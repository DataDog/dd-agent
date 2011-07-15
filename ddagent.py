# Standard imports
import logging
import os
import sys
import time
from subprocess import Popen
from hashlib import md5
from datetime import datetime, timedelta
from operator import attrgetter

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

CHECK_INTERVAL =  60 * 1000       # Every 60s
PROCESS_CHECK_INTERVAL = 1000     # Every second
TRANSACTION_FLUSH_INTERVAL = 5000 # Every 5 seconds

# Maximum delay before replaying a transaction
MAX_WAIT_FOR_REPLAY = timedelta(seconds=90) 

# Maximum queue size in bytes (when this is reached, old messages are dropped)
MAX_QUEUE_SIZE = 30 * 1024 * 1024 # 30MB

THROTTLING_DELAY = timedelta(microseconds=1000000/2) # 2 msg/second

def plural(count):
    if count > 1:
        return "s"
    return ""

class Transaction(object):

    application = None

    _transactions = [] #List of all non commited transactions
    _counter = 0 # Global counter to assign a number to each transaction


    _trs_to_flush = None # Current transactions being flushed
    _last_flush = datetime.now() # Last flush (for throttling)

    @staticmethod
    def set_application(app):
        Transaction.application = app

    @staticmethod
    def append(tr):

        total_size = tr._size
        if Transaction._transactions is not None:
            for tr2 in Transaction._transactions:
                total_size = total_size + tr2._size

        logging.info("Adding transaction, total size of queue is: %s KB" % (total_size/1024))
 
        if total_size > MAX_QUEUE_SIZE:
            logging.warn("Queue is too big, removing old messages...")
            new_trs = sorted(Transaction._transactions,key=attrgetter('_next_flush'), reverse = True)
            for tr2 in new_trs:
                if total_size > MAX_QUEUE_SIZE:
                    logging.warn("Removing transaction %s from queue" % tr2._id)
                    Transaction._transactions.remove(tr2)
                    total_size = total_size - tr2._size
            
        Transaction._transactions.append(tr)

    def __init__(self, data):

        Transaction._counter = Transaction._counter + 1
        self._id = Transaction._counter
        
        self._data = data
        self._size = sys.getsizeof(data)

        self._error_count = 0
        self._next_flush = datetime.now()

        #Append the transaction to the end of the list, we pop it later:
        # The most recent message is thus sent first.
        Transaction.append(self)
        logging.info("Created transaction %d" % self._id)

    @staticmethod
    def flush():

        if Transaction._trs_to_flush is not None:
            logging.info("A flush is already in progress, not doing anything")
            return

        to_flush = []
        # Do we have something to do ?
        now = datetime.now()
        for tr in Transaction._transactions:
            if tr.time_to_flush(now):
                to_flush.append(tr)
           
        count = len(to_flush)
        if count > 0:
            logging.info("Flushing %s transaction%s" % (count,plural(count)))
            url = Transaction.application.agentConfig['ddUrl'] + '/intake/'
            Transaction._trs_to_flush = to_flush
            Transaction._flush_next(url)

    @staticmethod
    def _flush_next(url):


        if len(Transaction._trs_to_flush) > 0:

            td = Transaction._last_flush + THROTTLING_DELAY - datetime.now()
            delay = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10.0**6
            if delay <= 0:
                tr = Transaction._trs_to_flush.pop()
                # Send Transaction to the intake
                req = tornado.httpclient.HTTPRequest(url, 
                             method = "POST", body = tr.get_data() )
                http = tornado.httpclient.AsyncHTTPClient()
                logging.info("Sending transaction %d to datadog" % tr._id)
                Transaction._last_flush = datetime.now()
                http.fetch(req, callback=lambda(x): Transaction.on_response(tr, url, x))
            else:
                # Wait a little bit more
                tornado.ioloop.IOLoop.instance().add_timeout(time.time() + delay,
                    lambda: Transaction._flush_next(url))
        else:
            Transaction._trs_to_flush = None

    @staticmethod
    def on_response(tr, url, response):
        if response.error: 
            tr.error()
        else:
            tr.finish()

        Transaction._flush_next(url)

    def time_to_flush(self,now = datetime.now()):
        return self._next_flush < now

    def get_data(self):
        try:
            return format_body(self._data, logging)
        except Exception, e:
            import traceback
            logger.error('http_emitter: Exception = ' + traceback.format_exc())

    def compute_next_flush(self):

        # Transactions are replayed, try to send them faster for newer transactions
        # Send them every MAX_WAIT_FOR_REPLAY at most
        td = timedelta(seconds=self._error_count * 20)
        if td > MAX_WAIT_FOR_REPLAY:
            td = MAX_WAIT_FOR_REPLAY

        newdate = datetime.now() + td
        self._next_flush = newdate.replace(microsecond=0)

    def error(self):
        self._error_count = self._error_count + 1
        self.compute_next_flush()
        logging.info("Transaction %d in error (%s error%s), it will be replayed after %s" % 
          (self._id, self._error_count, plural(self._error_count), self._next_flush))

    def finish(self):
        logging.info("Transaction %d completed" % self._id)
        Transaction._transactions.remove(self)

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
            Transaction(msg)
            Transaction.flush()
        else:
            raise tornado.web.HTTPError(500)
   
class Application(tornado.web.Application, Daemon):

    def __init__(self, pidFile, options, agentConfig):

        handlers = [
            (r"/intake/?", AgentInputHandler),
        ]

        settings = dict(
            cookie_secret="12oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            xsrf_cookies=False,
            debug=True,
        )

        self._check_pid = -1
        self._port = options.port
        self.agentConfig = agentConfig

        tornado.web.Application.__init__(self, handlers, **settings)

        Transaction.set_application(self)
    
        Daemon.__init__(self,pidFile)

    def run(self):

        http_server = tornado.httpserver.HTTPServer(self)
        http_server.listen(self._port)

        # Register callbacks
        mloop = tornado.ioloop.IOLoop.instance() 

        def run_checks():
            logging.info("Running checks...")
            self.run_checks()
    
        def process_check():
            self.process_check()

        def flush_trs():
            Transaction.flush()

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

    # set up logging
    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s")
    handler = logging.FileHandler(filename=options.log)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    #logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().setLevel(logging.INFO)
    
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

        app = Application(pidFile, options, agentConfig)
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

if __name__ == "__main__":
    main()

