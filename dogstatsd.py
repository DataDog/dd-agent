#!/usr/bin/python
"""
A Python Statsd implementation with some datadog special sauce.
"""

# stdlib
import httplib as http_client
import logging
import optparse
from random import randrange
import re
import socket
import select
import sys
from time import time
import threading
from urllib import urlencode

# project
from aggregator import MetricsAggregator
from checks import gethostname
from config import get_config
from daemon import Daemon
from util import json, PidFile


WATCHDOG_TIMEOUT = 120 
UDP_SOCKET_TIMEOUT = 5


logger = logging.getLogger('dogstatsd')


class Reporter(threading.Thread):
    """
    The reporter periodically sends the aggregated metrics to the
    server.
    """

    def __init__(self, interval, metrics_aggregator, api_host, api_key=None, use_watchdog=False):
        threading.Thread.__init__(self)
        self.daemon = True
        self.interval = int(interval)
        self.finished = threading.Event()
        self.metrics_aggregator = metrics_aggregator
        self.flush_count = 0

        self.watchdog = None
        if use_watchdog:
            from util import Watchdog
            self.watchdog = Watchdog(WATCHDOG_TIMEOUT)

        self.api_key = api_key
        self.api_host = api_host

        self.http_conn_cls = http_client.HTTPSConnection

        match = re.match('^(https?)://(.*)', api_host)

        if match:
            self.api_host = match.group(2)
            if match.group(1) == 'http':
                self.http_conn_cls = http_client.HTTPConnection

    def stop(self):
        self.finished.set()

    def run(self):
        logger.info("Reporting to %s every %ss" % (self.api_host, self.interval))
        logger.debug("Watchdog enabled: %s" % bool(self.watchdog))
        while True:
            if self.finished.isSet(): # Use camel case version for 2.4 support.
                break
            self.finished.wait(self.interval)
            self.metrics_aggregator.send_packet_count('datadog.dogstatsd.packet.count')
            self.flush()
            if self.watchdog:
                self.watchdog.reset()

    def flush(self):
        try:
            self.flush_count += 1
            metrics = self.metrics_aggregator.flush()
            count = len(metrics)
            if not count:
                logger.info("Flush #%s: No metrics to flush." % self.flush_count)
                return
            logger.info("Flush #%s: flushing %s metrics" % (self.flush_count, count))
            self.submit(metrics)
        except:
            logger.exception("Error flushing metrics")

    def submit(self, metrics):

        # HACK - Copy and pasted from dogapi, because it's a bit of a pain to distribute python
        # dependencies with the agent.
        conn = self.http_conn_cls(self.api_host)
        body = json.dumps({"series" : metrics})
        headers = {'Content-Type':'application/json'}
        method = 'POST'

        params = {}
        if self.api_key:
            params['api_key'] = self.api_key
        url = '/api/v1/series?%s' % urlencode(params)

        start_time = time()
        conn.request(method, url, body, headers)

        #FIXME: add timeout handling code here

        response = conn.getresponse()
        duration = round((time() - start_time) * 1000.0, 4)
        logger.info("%s %s %s%s (%sms)" % (
                        response.status, method, self.api_host, url, duration))

class Server(object):
    """
    A statsd udp server.
    """

    def __init__(self, metrics_aggregator, host, port):
        self.host = host
        self.port = int(port)
        self.address = (self.host, self.port)
        self.metrics_aggregator = metrics_aggregator
        self.buffer_size = 1024

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(0)

        self.running = False

    def start(self):
        """ Run the server. """
        # Bind to the UDP socket.
        self.socket.bind(self.address)
        logger.info('Listening on host & port: %s' % str(self.address))

        # Inline variables for quick look-up.
        buffer_size = self.buffer_size
        aggregator_submit = self.metrics_aggregator.submit_packets
        socket = self.socket
        socket_recv = self.socket.recv
        timeout = UDP_SOCKET_TIMEOUT

        # Run our select loop.
        self.running = True
        while self.running:
            try:
                ready = select.select([socket], [], [], timeout)
                if ready[0]:
                    aggregator_submit(socket_recv(buffer_size))
            except (KeyboardInterrupt, SystemExit):
                break
            except:
                logger.exception('Error receiving datagram')

    def stop(self):
        self.running = False


class Dogstatsd(Daemon):
    """ This class is the dogstats daemon. """

    def __init__(self, pid_file, server, reporter):
        Daemon.__init__(self, pid_file)
        self.server = server
        self.reporter = reporter

    def run(self):
        self.reporter.start()
        self.server.start()


def init(config_path=None, use_watchdog=False, use_forwarder=False):
    c = get_config(parse_args=False, cfg_path=config_path, init_logging=True)

    logger.debug("Configuration dogstatsd")

    port     = c['dogstatsd_port']
    interval = c['dogstatsd_interval']
    api_key  = c['api_key']

    target = c['dd_url']
    if use_forwarder:
        target = c['dogstatsd_target'] 

    hostname = gethostname(c)

    # Create the aggregator (which is the point of communication between the
    # server and reporting threads.
    aggregator = MetricsAggregator(hostname)

    # Start the reporting thread.
    reporter = Reporter(interval, aggregator, target, api_key, use_watchdog)

    # Start the server.
    server_host = ''
    server = Server(aggregator, server_host, port)

    return reporter, server

def main(config_path=None):
    """ The main entry point for the unix version of dogstatsd. """
    parser = optparse.OptionParser("%prog [start|stop|restart|status]")
    parser.add_option('-u', '--use-local-forwarder', action='store_true',
                        dest="use_forwarder", default=False)
    opts, args = parser.parse_args()

    reporter, server = init(config_path, use_watchdog=True, use_forwarder=opts.use_forwarder)

    # If no args were passed in, run the server in the foreground.
    if not args:
        reporter.start()
        server.start()

        # If we're here, we're done.
        logger.info("Shutting down ...")
        return 0

    # Otherwise, we're process the deamon command.
    else:
        command = args[0]
        pid_file = PidFile('dogstatsd')
        daemon = Dogstatsd(pid_file.get_path(), server, reporter)

        if command == 'start':
            daemon.start()
        elif command == 'stop':
            daemon.stop()
        elif command == 'restart':
            daemon.restart()
        elif command == 'status':
            pid = pid_file.get_pid()
            if pid:
                message = 'dogstatsd is running with pid %s' % pid
            else:
                message = 'dogstatsd is not running'
            logger.info(message)
            sys.stdout.write(message + "\n")
        else:
            sys.stderr.write("Unknown command: %s\n\n" % command)
            parser.print_help()
            return 1
        return 0


if __name__ == '__main__':
    sys.exit(main())
