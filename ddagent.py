# Standard imports
import logging
import os
import sys
from subprocess import Popen
from hashlib import md5

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


CHECK_INTERVAL =  60 * 1000 # Every 60s
PROCESS_CHECK_INTERVAL = 1000 # Every second

class Transaction(object):

    _transactions = []
    _flush_tr = None
    _counter = 0

    def __init__(self, data):

        Transaction._counter = Transaction._counter + 1
        self._id = Transaction._counter
        
        self._data = data
        self._transactions.append(self)
        logging.info("Created transaction %d" % self._id)

    @staticmethod
    def flush(url, callback, topRun = True):


        if topRun:
            Transaction._flush_tr = list(Transaction._transactions)
        
        if Transaction._flush_tr is not None and len(Transaction._flush_tr) > 0:
            tr = Transaction._flush_tr.pop()
            if tr is not None:
                # Send all remaining transaction to the intake
                req = tornado.httpclient.HTTPRequest(url, 
                      method = "POST", body = tr.get_data() )
                http = tornado.httpclient.AsyncHTTPClient()
                logging.info("Sending transaction %d to datadog" % tr._id)
                http.fetch(req, callback=lambda(x): Transaction.on_response(tr,url,callback,x))
        else:
            callback()

    @staticmethod
    def on_response(tr, url, callback, response):
        if response.error: 
            tr.error()
        else:
            tr.finish()

        Transaction.flush(url, callback, topRun = False)

    def get_data(self):
        try:
            return format_body(self._data, logging)
        except Exception, e:
            import traceback
            logger.error('http_emitter: Exception = ' + traceback.format_exc())

    def error(self):
        logging.info("Transaction %d in error, will be replayed later" % self._id)
        if not self in self._transactions:
            self._transactions.append(self)

    def finish(self):
        self._transactions.remove(self)
        logging.info("Transaction %d completed" % self._id)

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


    @tornado.web.asynchronous
    def post(self):
        """Read the message and forward it to the intake"""

        # read message
        msg = AgentInputHandler.parse_message(self.get_argument(self.PAYLOAD),
            self.get_argument(self.HASH))

        if msg is not None:
            # Setup a transaction for this message
            Transaction(msg)
            Transaction.flush(self.application.agentConfig['ddUrl'] + '/intake/',self.on_finish)
        else:
            raise tornado.web.HTTPError(500)
   
    def on_finish(self):
        self.finish()

class Application(tornado.web.Application):

    def __init__(self, options, agentConfig):

        handlers = [
            (r"/intake/?", AgentInputHandler),
        ]

        settings = dict(
            cookie_secret="12oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            xsrf_cookies=False,
            debug=True,
        )

        self._check_pid = -1
        self.agentConfig = agentConfig

        tornado.web.Application.__init__(self, handlers, **settings)

        http_server = tornado.httpserver.HTTPServer(self)
        http_server.listen(options.port)

        self.run_checks(sys.argv, True)

    def run_checks(self, cmd, firstRun = False):

        if self._check_pid > 0 :
            logging.warning("Not running checks because a previous instance is still running")
            return False

        args = [sys.executable]
        args.extend(cmd)
        args.append("--action=runchecks")

        if firstRun:
            args.append("--firstRun=yes")

        print args
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
    define("port", type=int, default=17123, help="Port to listen on")
    define("log", type=str, default="ddagent.log", help="Log file to use")
    define("action",type=str, default="start", help="Action to run")
    define("firstRun",type=bool, default=False, help="First check run ?")

    parse_command_line()

    # set up logging
    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s")
    handler = logging.FileHandler(filename=options.log)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    #logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().setLevel(logging.INFO)

    agentConfig, rawConfig = get_config()

    if options.action == "start":
        logging.info("Starting ddagent tornado")
        # Set up tornado
        app = Application(options,agentConfig)

        # Register check callback
        mloop = tornado.ioloop.IOLoop.instance() 

        def run_checks():
            logging.info("Running checks...")
            app.run_checks(sys.argv)
    
        def process_check():
            app.process_check()

        check_scheduler = tornado.ioloop.PeriodicCallback(run_checks,CHECK_INTERVAL, io_loop = mloop) 
        check_scheduler.start()

        p_checks_scheduler = tornado.ioloop.PeriodicCallback(process_check,PROCESS_CHECK_INTERVAL, io_loop = mloop) 
        p_checks_scheduler.start()

        # Start me up!
        mloop.start()

    elif options.action == "runchecks":

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

if __name__ == "__main__":
    main()

