# Standard imports
import logging

#Tornado
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, parse_command_line, options

# agent import
from config import get_config, get_system_stats, get_parsed_args
from emitter import http_emitter
from checks.common import checks


CHECK_INTERVAL =  60 * 1000 # Every 60s

class Application(tornado.web.Application):

    def __init__(self):

        handlers = []

        settings = dict(
            cookie_secret="12oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            xsrf_cookies=False,
            debug=True,
        )

        #Create checks instance
        agentLogger = logging.getLogger('agent')

        agentLogger.debug('Collecting basic system stats')

        systemStats = get_system_stats()
        agentLogger.debug('System: ' + str(systemStats))

        agentLogger.debug('Creating checks instance')

        agentConfig, rawConfig = get_config()
        emitter = http_emitter

        self._checks = checks(agentConfig, rawConfig, emitter)
        self.run_checks(True,systemStats) # start immediately 

        tornado.web.Application.__init__(self, handlers, **settings)

    def run_checks(self, firstRun = False, systemStats = False):
        self._checks._doChecks(firstRun, systemStats)

def main():
    define("port", type=int, default=17123, help="Port to listen on")
    define("log", type=str, default="ddagent.log", help="Log file to use")

    parse_command_line()

    # set up logging
    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s")
    handler = logging.FileHandler(filename=options.log)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Starting ddagent tornado")


    # Set up tornado
    app = Application()

    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)

    # Register check callback
    interval_ms = 10 * 60 * 1000 
    mloop = tornado.ioloop.IOLoop.instance() 

    def run_checks():
        logging.info("Running checks...")
        app.run_checks()

    check_scheduler = tornado.ioloop.PeriodicCallback(run_checks,CHECK_INTERVAL, io_loop = mloop) 
    check_scheduler.start()

    # Start me up!
    mloop.start()


if __name__ == "__main__":
    main()

