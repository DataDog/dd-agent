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
import tornado.httpclient
import tornado.ioloop
import tornado.web
from tornado.escape import json_decode
from tornado.options import define, parse_command_line, options

# agent import
from config import get_config, get_system_stats, get_parsed_args
from emitter import http_emitter, format_body
from checks.common import checks
from daemon import Daemon
from agent import setupLogging, getPidFile

from transaction import Transaction, TransactionManager

CHECK_INTERVAL =  60 * 1000       # Every 60s
PROCESS_CHECK_INTERVAL = 1000     # Every second
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

        url = self._application.agentConfig['ddUrl'] + '/intake/'
        # Send Transaction to the intake
        req = tornado.httpclient.HTTPRequest(url, 
                             method = "POST", body = self.get_data() )
        http = tornado.httpclient.AsyncHTTPClient()
        logging.info("Sending transaction %d to datadog" % self.get_id())
        http.fetch(req, callback=lambda(x): self.on_response(x))

    def on_response(self, response):
        if response.error: 
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

class Application(tornado.web.Application, Daemon):

    def __init__(self, pidFile, port, agentConfig):

        self._check_pid = -1
        self._port = port
        self.agentConfig = agentConfig

        MetricTransaction.set_application(self)
        self._tr_manager = TransactionManager(MAX_WAIT_FOR_REPLAY,
            MAX_QUEUE_SIZE, THROTTLING_DELAY)
        MetricTransaction.set_tr_manager(self._tr_manager)
    
        Daemon.__init__(self,pidFile)

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

        def run_checks():
            logging.info("Running checks...")
            self.run_checks()
    
        def process_check():
            self.process_check()

        def flush_trs():
            self._tr_manager.flush()

        check_scheduler = tornado.ioloop.PeriodicCallback(run_checks,CHECK_INTERVAL, io_loop = mloop) 

        p_checks_scheduler = tornado.ioloop.PeriodicCallback(process_check,PROCESS_CHECK_INTERVAL, io_loop = mloop) 
        tr_sched = tornado.ioloop.PeriodicCallback(flush_trs,TRANSACTION_FLUSH_INTERVAL, io_loop = mloop)

        # Start everything
        tr_sched.start()
        p_checks_scheduler.start()
        check_scheduler.start()
        self.run_checks(True)
        mloop.start()
    
    def run_checks(self, firstRun = False):

        if self._check_pid > 0 :
            logging.warning("Not running checks because a previous instance is still running")
            return False

        args = [sys.executable]
        args.append(__file__)
        args.append("--action=runchecks")

        if firstRun:
            args.append("--firstRun=yes")

        logging.info("Running local checks")

        try:
            p = Popen(args)
            self._check_pid = p.pid
        except Exception, e:
            logging.exception(e)
            return False
  
        return True

    def process_check(self):

        if self._check_pid > 0:
            logging.debug("Checking on child process")
            # Try to join the process running checks
            (pid, status) = os.waitpid(self._check_pid,os.WNOHANG)
            if (pid, status) != (0, 0):
                logging.debug("child (pid: %s) exited with status: %s" % (pid, status))
                if status != 0:
                    logging.error("Error while running checks")
                self._check_pid = -1
            else:
                logging.debug("child (pid: %s) still running" % self._check_pid)

def main():

    define("action", type=str, default= "", help="Action to run")
    define("firstRun", type=bool, default=False, help="First check run ?")
    define("port", type=int, default=17123, help="Port to listen on")
    define("log", type=str, default="ddagent.log", help="Log file to use")

    args = parse_command_line()

    # Remove known options so it won't get parsed (and fails because
    # get_config don't know about our option and python OptParser breaks on
    # unkown options)
    newargs = []
    knownoptions = [ "--" + o for o in options.keys()]
    for arg in sys.argv:
        known = False
        for opt in knownoptions:
            if arg.startswith(opt):
                known = True
                break

        if not known:
            newargs.append(arg)

    sys.argv = newargs

    agentConfig, rawConfig = get_config()

    setupLogging(agentConfig)
 
    if options.action == "runchecks":

        #Create checks instance
        agentLogger = logging.getLogger('agent')

        systemStats = False
        if options.firstRun:
            agentLogger.debug('Collecting basic system stats')
            systemStats = get_system_stats()
            agentLogger.debug('System: ' + str(systemStats))
            
        agentLogger.debug('Creating checks instance')

        emitter = http_emitter
       
        mConfig = dict(agentConfig)
        mConfig['ddUrl'] = "http://localhost:" + str(options.port)
        _checks = checks(mConfig, rawConfig, emitter)
        _checks._doChecks(options.firstRun,systemStats)

    else:
        if options.action == "" and len(sys.argv) > 0:
            command = args[0]
        else:
            command = options.action

        pidFile = getPidFile(options.action, agentConfig, False)

        port = agentConfig['listen_port']
        if port is None:
            port = options.port

        app = Application(pidFile, port, agentConfig)

        if command == "start":
            logging.debug("Starting ddagent tornado daemon")
            app.start()

        elif command == "stop":
            logging.debug("Stop daemon")
            app.stop()

        elif command == 'restart':
            logging.debug('Restart daemon')
            app.restart()

        elif command == 'foreground':
            logging.debug('Running in foreground')
            app.run()

        elif command == 'status':
            logging.debug('Checking agent status')

            try:
                pf = file(pidFile,'r')
                pid = int(pf.read().strip())
                pf.close()
            except IOError:
                pid = None
            except SystemExit:
                pid = None

            if pid:
                sys.stdout.write('dd-agent is running as pid %s.\n' % pid)
            else:
                sys.stdout.write('dd-agent is not running.\n')

        else:
            sys.stderr.write('Unknown command: %s.\n' % options.action)
            sys.exit(2)

        sys.exit(0)

if __name__ == "__main__":
    main()

