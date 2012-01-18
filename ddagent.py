#!/usr/bin/python
'''
    Datadog
    www.datadoghq.com
    ----
    Make sense of your IT Data

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
    (C) Datadog, Inc. 2010 all rights reserved
'''

# Standard imports
import logging
import os
import sys
from subprocess import Popen
from hashlib import md5
from datetime import datetime, timedelta

#Tornado
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.escape import json_decode
from tornado.options import define, parse_command_line, options

# agent import
from emitter import http_emitter, format_body
from config import get_config

from transaction import Transaction, TransactionManager

TRANSACTION_FLUSH_INTERVAL = 5000 # Every 5 seconds

# Maximum delay before replaying a transaction
MAX_WAIT_FOR_REPLAY = timedelta(seconds=90) 

# Maximum queue size in bytes (when this is reached, old messages are dropped)
MAX_QUEUE_SIZE = 30 * 1024 * 1024 # 30MB

THROTTLING_DELAY = timedelta(microseconds=1000000/2) # 2 msg/second

class MetricTransaction(Transaction):

    _application = None
    _trManager = None

    @classmethod
    def set_application(cls, app):
        cls._application = app

    @classmethod
    def set_tr_manager(cls, manager):
        cls._trManager = manager

    @classmethod
    def get_tr_manager(cls):
        return cls._trManager

    def __init__(self, data):

        self._data = data

        # Call after data has been set (size is computed in Transaction's init)
        Transaction.__init__(self)

        # Insert the transaction in the Manager
        self._trManager.append(self)
        logging.info("Created transaction %d" % self.get_id())
        self._trManager.flush()

    def __sizeof__(self):
        return sys.getsizeof(self._data)

    def get_data(self):
        try:
            return format_body(self._data, logging)
        except Exception, e:
            import traceback
            logger.error('http_emitter: Exception = ' + traceback.format_exc())

    def flush(self):

        url = self._application._agentConfig['ddUrl'] + '/intake/'
        # Send Transaction to the intake
        req = tornado.httpclient.HTTPRequest(url, 
                             method = "POST", body = self.get_data() )
        http = tornado.httpclient.AsyncHTTPClient()
        logging.info("Sending transaction %d to datadog" % self.get_id())
        http.fetch(req, callback=lambda(x): self.on_response(x))

    def on_response(self, response):
        if response.error: 
            logging.error("Got error %s" % response.error)
            self._trManager.tr_error(self)
        else:
            self._trManager.tr_success(self)

        self._trManager.flush_next()

class StatusHandler(tornado.web.RequestHandler):

    def get(self):

        m = MetricTransaction.get_tr_manager()
       
        self.write("<table><tr><td>Id</td><td>Size</td><td>Error count</td><td>Next flush</td></tr>")
        for tr in m.get_transactions():
            self.write("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % 
                (tr.get_id(), tr.get_size(), tr.get_error_count(), tr.get_next_flush()))
        self.write("</table>")
  
class AgentInputHandler(tornado.web.RequestHandler):

    HASH = "hash"
    PAYLOAD = "payload"

    @staticmethod
    def parse_message(message, msg_hash):

        c_hash = md5(message).hexdigest()
        if c_hash != msg_hash:
            logging.error("Malformed message: %s != %s" % (c_hash, msg_hash))
            return None

        return json_decode(message)


    def post(self):
        """Read the message and forward it to the intake"""

        # read message
        msg = AgentInputHandler.parse_message(self.get_argument(self.PAYLOAD),
            self.get_argument(self.HASH))

        if msg is not None:
            # Setup a transaction for this message
            tr = MetricTransaction(msg)
        else:
            raise tornado.web.HTTPError(500)

        self.write("Transaction: %s" % tr.get_id())

class Application(tornado.web.Application):

    def __init__(self, port, agentConfig):

        self._port = port
        self._agentConfig = agentConfig

        MetricTransaction.set_application(self)
        self._tr_manager = TransactionManager(MAX_WAIT_FOR_REPLAY,
            MAX_QUEUE_SIZE, THROTTLING_DELAY)
        MetricTransaction.set_tr_manager(self._tr_manager)
    
    def run(self):

        handlers = [
            (r"/intake/?", AgentInputHandler),
            (r"/status/?", StatusHandler),
        ]

        settings = dict(
            cookie_secret="12oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            xsrf_cookies=False,
            debug=True,
        )

        tornado.web.Application.__init__(self, handlers, **settings)
        http_server = tornado.httpserver.HTTPServer(self)
        http_server.listen(self._port)
        logging.info("Listening on port %s" % self._port)

        # Register callbacks
        mloop = tornado.ioloop.IOLoop.instance() 

        def flush_trs():
            self._tr_manager.flush()

        tr_sched = tornado.ioloop.PeriodicCallback(flush_trs,TRANSACTION_FLUSH_INTERVAL, io_loop = mloop)

        # Register optional Graphite listener
        gport = self._agentConfig["graphite_listen_port"]
        if gport is not None:
            logging.info("Starting graphite listener on port %s" % gport)
            from graphite import GraphiteServer
            gs = GraphiteServer()
            gs.listen(gport)

        # Start everything
        tr_sched.start()
        mloop.start()
    
def main():

    # Prevent tornado from setting up logging, it's done by our agent later on
    #tornado.options.options.logging = "none"
    # Settup logging
    define("pycurl", default=1, help="Use pycurl")
    parse_command_line()

    if options.pycurl == 0 or options.pycurl == "0":
        os.environ['USE_SIMPLE_HTTPCLIENT'] = '1'

    import tornado.httpclient

    agentConfig, rawConfig = get_config(parse_args = False)

    port = agentConfig['listen_port']
    if port is None:
        port = 17123

    app = Application(port,agentConfig)
    app.run()

if __name__ == "__main__":
    main()

