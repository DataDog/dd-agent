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

# Tornado
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.escape import json_decode
from tornado.options import define, parse_command_line, options

# agent import
from util import Watchdog, getOS
from emitter import http_emitter, format_body
from config import get_config
from checks.common import getUuid
from checks import gethostname
from transaction import Transaction, TransactionManager

TRANSACTION_FLUSH_INTERVAL = 5000 # Every 5 seconds
WATCHDOG_INTERVAL_MULTIPLIER = 10 # 10x flush interval

# Maximum delay before replaying a transaction
MAX_WAIT_FOR_REPLAY = timedelta(seconds=90)

# Maximum queue size in bytes (when this is reached, old messages are dropped)
MAX_QUEUE_SIZE = 30 * 1024 * 1024 # 30MB

THROTTLING_DELAY = timedelta(microseconds=1000000/2) # 2 msg/second

class MetricTransaction(Transaction):

    _application = None
    _trManager = None
    _endpoints = []

    @classmethod
    def set_application(cls, app):
        cls._application = app

    @classmethod
    def set_tr_manager(cls, manager):
        cls._trManager = manager

    @classmethod
    def get_tr_manager(cls):
        return cls._trManager

    @classmethod
    def set_endpoints(cls):
        if 'use_pup' in cls._application._agentConfig:
            if cls._application._agentConfig['use_pup']:
                cls._endpoints.append('pup_url')
        # Only send data to Datadog if an API KEY exists
        # i.e. user is also Datadog user
        try:
            is_dd_user = 'api_key' in cls._application._agentConfig\
                and 'use_dd' in cls._application._agentConfig\
                and cls._application._agentConfig['use_dd']\
                and cls._application._agentConfig.get('api_key') is not None\
                and cls._application._agentConfig.get('api_key', "pup") not in ("", "pup")
            if is_dd_user:
                logging.warn("You are a Datadog user so we will send data to https://app.datadoghq.com")
                cls._endpoints.append('dd_url')
        except:
            logging.info("Not a Datadog user")

    def __init__(self, data, headers):
        self._data = data
        self._headers = headers

        # Call after data has been set (size is computed in Transaction's init)
        Transaction.__init__(self)

        # Insert the transaction in the Manager
        self._trManager.append(self)
        logging.debug("Created transaction %d" % self.get_id())
        self._trManager.flush()

    def __sizeof__(self):
        return sys.getsizeof(self._data)

    def get_url(self, endpoint):
        api_key = self._application._agentConfig.get('api_key')
        if api_key:
            return self._application._agentConfig[endpoint] + '/intake?api_key=%s' % api_key
        return self._application._agentConfig[endpoint] + '/intake'

    def flush(self):
        for endpoint in self._endpoints:
            url = self.get_url(endpoint)
            logging.info("Sending metrics to endpoint %s at %s" % (endpoint, url))
            req = tornado.httpclient.HTTPRequest(url, method="POST",
                body=self._data, headers=self._headers)

            # Send Transaction to the endpoint
            http = tornado.httpclient.AsyncHTTPClient()

            # The success of this metric transaction should only depend on
            # whether or not it's successfully sent to datadoghq. If it fails
            # getting sent to pup, it's not a big deal.
            callback = lambda(x): None
            if len(self._endpoints) <= 1 or endpoint == 'dd_url':
                callback = self.on_response

            http.fetch(req, callback=callback)

    def on_response(self, response):
        if response.error:
            logging.error("Response: %s" % response.error)
            self._trManager.tr_error(self)
        else:
            self._trManager.tr_success(self)

        self._trManager.flush_next()


class APIMetricTransaction(MetricTransaction):

    def get_url(self, endpoint):
        config = self._application._agentConfig
        api_key = config['api_key']
        url = config[endpoint] + '/api/v1/series/?api_key=' + api_key
        if endpoint == 'pup_url':
            url = config[endpoint] + '/api/v1/series'
        return url

    def get_data(self):
        return self._data


class StatusHandler(tornado.web.RequestHandler):

    def get(self):
        threshold = int(self.get_argument('threshold', -1))

        m = MetricTransaction.get_tr_manager()

        self.write("<table><tr><td>Id</td><td>Size</td><td>Error count</td><td>Next flush</td></tr>")
        transactions = m.get_transactions()
        for tr in transactions:
            self.write("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" %
                (tr.get_id(), tr.get_size(), tr.get_error_count(), tr.get_next_flush()))
        self.write("</table>")

        if threshold >= 0:
            if len(transactions) > threshold:
                self.set_status(503)

class AgentInputHandler(tornado.web.RequestHandler):

    def post(self):
        """Read the message and forward it to the intake"""

        # read message
        msg = self.request.body
        headers = self.request.headers

        if msg is not None:
            # Setup a transaction for this message
            tr = MetricTransaction(msg, headers)
        else:
            raise tornado.web.HTTPError(500)

        self.write("Transaction: %s" % tr.get_id())

class ApiInputHandler(tornado.web.RequestHandler):

    def post(self):
        """Read the message and forward it to the intake"""

        # read message
        msg = self.request.body
        headers = self.request.headers

        if msg is not None:
            # Setup a transaction for this message
            tr = APIMetricTransaction(msg, headers)
        else:
            raise tornado.web.HTTPError(500)


class Application(tornado.web.Application):

    def __init__(self, port, agentConfig, watchdog=True):
        self._port = int(port)
        self._agentConfig = agentConfig
        self._metrics = {}
        MetricTransaction.set_application(self)
        MetricTransaction.set_endpoints()
        self._tr_manager = TransactionManager(MAX_WAIT_FOR_REPLAY,
            MAX_QUEUE_SIZE, THROTTLING_DELAY)
        MetricTransaction.set_tr_manager(self._tr_manager)

        self._watchdog = None
        if watchdog:
            watchdog_timeout = TRANSACTION_FLUSH_INTERVAL * WATCHDOG_INTERVAL_MULTIPLIER
            self._watchdog = Watchdog(watchdog_timeout)

    def appendMetric(self, prefix, name, host, device, ts, value):

        if self._metrics.has_key(prefix):
            metrics = self._metrics[prefix]
        else:
            metrics = {}
            self._metrics[prefix] = metrics

        if metrics.has_key(name):
            metrics[name].append([host, device, ts, value])
        else:
            metrics[name] = [[host, device, ts, value]]

    def _postMetrics(self):

        if len(self._metrics) > 0:
            self._metrics['uuid'] = getUuid()
            self._metrics['internalHostname'] = gethostname(self._agentConfig)
            self._metrics['apiKey'] = self._agentConfig['api_key']
            MetricTransaction(self._metrics, {})
            self._metrics = {}

    def run(self):

        handlers = [
            (r"/intake/?", AgentInputHandler),
            (r"/api/v1/series/?", ApiInputHandler),
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
        logging.info("Listening on port %d" % self._port)

        # Register callbacks
        self.mloop = tornado.ioloop.IOLoop.instance()

        def flush_trs():
            if self._watchdog:
                self._watchdog.reset()
            self._postMetrics()
            self._tr_manager.flush()

        tr_sched = tornado.ioloop.PeriodicCallback(flush_trs,TRANSACTION_FLUSH_INTERVAL,
            io_loop = self.mloop)

        # Register optional Graphite listener
        gport = self._agentConfig.get("graphite_listen_port", None)
        if gport is not None:
            logging.info("Starting graphite listener on port %s" % gport)
            from graphite import GraphiteServer
            gs = GraphiteServer(self, gethostname(self._agentConfig), io_loop=self.mloop)
            gs.listen(gport)

        # Start everything
        if self._watchdog:
            self._watchdog.reset()
        tr_sched.start()
        self.mloop.start()

    def stop(self):
        self.mloop.stop()

def init():
    agentConfig = get_config(parse_args = False)

    port = agentConfig.get('listen_port', 17123)
    if port is None:
        port = 17123
    else:
        port = int(port)

    app = Application(port, agentConfig)
    return app

def main():
    define("pycurl", default=1, help="Use pycurl")
    parse_command_line()

    if options.pycurl == 0 or options.pycurl == "0":
        os.environ['USE_SIMPLE_HTTPCLIENT'] = '1'

    import tornado.httpclient
    app = init()
    app.run()

if __name__ == "__main__":
    main()
