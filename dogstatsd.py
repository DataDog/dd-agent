#!/usr/bin/env python
"""
A Python Statsd implementation with some datadog special sauce.
"""

# set up logging before importing any other components
from config import initialize_logging
initialize_logging('dogstatsd')

import os
os.umask(022)

# stdlib
import httplib as http_client
import logging
import optparse
import re
import select
import signal
import socket
import sys
from time import time
import threading
from urllib import urlencode

# project
from aggregator import MetricsAggregator
from checks.check_status import DogstatsdStatus
from config import get_config
from daemon import Daemon, AgentSupervisor
from util import json, PidFile, get_hostname, plural

log = logging.getLogger('dogstatsd')


WATCHDOG_TIMEOUT = 120
UDP_SOCKET_TIMEOUT = 5
FLUSH_LOGGING_PERIOD = 10
FLUSH_LOGGING_INITIAL = 5

def serialize_metrics(metrics):
    return json.dumps({"series" : metrics})

def serialize_event(event):
    return json.dumps(event)

class Reporter(threading.Thread):
    """
    The reporter periodically sends the aggregated metrics to the
    server.
    """

    def __init__(self, interval, metrics_aggregator, api_host, api_key=None, use_watchdog=False):
        threading.Thread.__init__(self)
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
        log.info("Stopping reporter")
        self.finished.set()

    def run(self):

        log.info("Reporting to %s every %ss" % (self.api_host, self.interval))
        log.debug("Watchdog enabled: %s" % bool(self.watchdog))

        # Persist a start-up message.
        DogstatsdStatus().persist()

        while not self.finished.isSet(): # Use camel case isSet for 2.4 support.
            self.finished.wait(self.interval)
            self.metrics_aggregator.send_packet_count('datadog.dogstatsd.packet.count')
            self.flush()
            if self.watchdog:
                self.watchdog.reset()

        # Clean up the status messages.
        log.debug("Stopped reporter")
        DogstatsdStatus.remove_latest_status()

    def flush(self):
        try:
            self.flush_count += 1
            packets_per_second = self.metrics_aggregator.packets_per_second(self.interval)
            packet_count = self.metrics_aggregator.total_count

            metrics = self.metrics_aggregator.flush()
            count = len(metrics)
            should_log = self.flush_count <= FLUSH_LOGGING_INITIAL or self.flush_count % FLUSH_LOGGING_PERIOD == 0
            if not count:
                if should_log:
                    log.info("Flush #%s: No metrics to flush." % self.flush_count)
                else:
                    log.debug("Flush #%s: No metrics to flush." % self.flush_count)
            else:
                if should_log:
                    log.info("Flush #%s: flushing %s metric%s" % (self.flush_count, count, plural(count)))
                else:
                    log.debug("Flush #%s: flushing %s metric%s" % (self.flush_count, count, plural(count)))

                self.submit(metrics)

            events = self.metrics_aggregator.flush_events()
            event_count = len(events)
            if not event_count:
                if should_log:
                    log.info("Flush #%s: No events to flush." % self.flush_count)
                else:
                    log.debug("Flush #%s: No events to flush." % self.flush_count)
            else:
                if should_log:
                    log.info("Flush #%s: flushing %s event%s" % (self.flush_count, len(events), plural(len(events))))
                else:
                    log.debug("Flush #%s: flushing %s event%s" % (self.flush_count, len(events), plural(len(events))))
                self.submit_events(events)

            if self.flush_count == FLUSH_LOGGING_INITIAL:
                log.info("First flushes done, next flushes will be logged every %s flushes." % FLUSH_LOGGING_PERIOD)

            # Persist a status message.
            packet_count = self.metrics_aggregator.total_count
            DogstatsdStatus(
                flush_count=self.flush_count,
                packet_count=packet_count,
                packets_per_second=packets_per_second,
                metric_count=count,
                event_count=event_count,
            ).persist()

        except Exception, e:
            log.exception("Error flushing metrics")

    def submit(self, metrics):
        # Copy and pasted from dogapi, because it's a bit of a pain to distribute python
        # dependencies with the agent.
        body = serialize_metrics(metrics)
        headers = {'Content-Type':'application/json'}
        method = 'POST'

        params = {}
        if self.api_key:
            params['api_key'] = self.api_key
        url = '/api/v1/series?%s' % urlencode(params)

        start_time = time()
        status = None
        conn = self.http_conn_cls(self.api_host)
        try:
            conn.request(method, url, body, headers)

            #FIXME: add timeout handling code here

            response = conn.getresponse()
            status = response.status
            response.close()
        finally:
            conn.close()
        duration = round((time() - start_time) * 1000.0, 4)
        log.debug("%s %s %s%s (%sms)" % (
                        status, method, self.api_host, url, duration))
        return duration

    def submit_events(self, events):
        headers = {'Content-Type':'application/json'}
        method = 'POST'

        params = {}
        if self.api_key:
            params['api_key'] = self.api_key
        url = '/api/v1/events?%s' % urlencode(params)

        status = None
        conn = self.http_conn_cls(self.api_host)
        try:
            for event in events:
                start_time = time()
                body = serialize_event(event)
                log.debug('Sending event: %s' % body)
                conn.request(method, url, body, headers)

                response = conn.getresponse()
                status = response.status
                response.close()
                duration = round((time() - start_time) * 1000.0, 4)
                log.debug("%s %s %s%s (%sms)" % (
                                status, method, self.api_host, url, duration))
        finally:
            conn.close()

class Server(object):
    """
    A statsd udp server.
    """

    def __init__(self, metrics_aggregator, host, port, forward_to_host=None, forward_to_port=None):
        self.host = host
        self.port = int(port)
        self.address = (self.host, self.port)
        self.metrics_aggregator = metrics_aggregator
        self.buffer_size = 1024 * 8

        self.running = False

        self.should_forward = forward_to_host is not None
        
        self.forward_udp_sock = None
        # In case we want to forward every packet received to another statsd server
        if self.should_forward:
            if forward_to_port is None:
                forward_to_port = 8125

            log.info("External statsd forwarding enabled. All packets received will be forwarded to %s:%s" % (forward_to_host, forward_to_port))
            try:
                self.forward_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.forward_udp_sock.connect((forward_to_host, forward_to_port))
            except Exception, e:
                log.exception("Error while setting up connection to external statsd server")

    def start(self):
        """ Run the server. """
        # Bind to the UDP socket.
        # IPv4 only
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(0)
        self.socket.bind(self.address)

        log.info('Listening on host & port: %s' % str(self.address))

        # Inline variables for quick look-up.
        buffer_size = self.buffer_size
        aggregator_submit = self.metrics_aggregator.submit_packets
        sock = [self.socket]
        socket_recv = self.socket.recv
        select_select = select.select
        select_error = select.error
        timeout = UDP_SOCKET_TIMEOUT
        should_forward = self.should_forward
        forward_udp_sock = self.forward_udp_sock

        # Run our select loop.
        self.running = True
        while self.running:
            try:
                ready = select_select(sock, [], [], timeout)
                if ready[0]:
                    message = socket_recv(buffer_size)
                    aggregator_submit(message)

                    if should_forward:
                        forward_udp_sock.send(message)
            except select_error, se:
                # Ignore interrupted system calls from sigterm.
                errno = se[0]
                if errno != 4:
                    raise
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception, e:
                log.exception('Error receiving datagram')

    def stop(self):
        self.running = False


class Dogstatsd(Daemon):
    """ This class is the dogstatsd daemon. """

    def __init__(self, pid_file, server, reporter, autorestart):
        Daemon.__init__(self, pid_file, autorestart=autorestart)
        self.server = server
        self.reporter = reporter


    def _handle_sigterm(self, signum, frame):
        log.debug("Caught sigterm. Stopping run loop.")
        self.server.stop()

    def stop(self):
        if self.autorestart:
            parent_pid = os.getpgid(self.pid())
            os.kill(parent_pid, signal.SIGTERM)
        super(Dogstatsd, self).stop()

    def run(self):
        # Gracefully exit on sigterm.
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # Handle Keyboard Interrupt
        signal.signal(signal.SIGINT, self._handle_sigterm)

        # Start the reporting thread before accepting data
        self.reporter.start()

        try:
            try:
                self.server.start()
            except Exception, e:
                log.exception('Error starting server')
                raise e
        finally:
            # The server will block until it's done. Once we're here, shutdown
            # the reporting thread.
            self.reporter.stop()
            self.reporter.join()
            log.info("Dogstatsd is stopped")
            # Restart if asked to restart
            if self.autorestart:
                sys.exit(AgentSupervisor.RESTART_EXIT_STATUS)

    def info(self):
        logging.getLogger().setLevel(logging.ERROR)
        return DogstatsdStatus.print_latest_status()


def init(config_path=None, use_watchdog=False, use_forwarder=False):
    """Configure the server and the reporting thread.
    """
    c = get_config(parse_args=False, cfg_path=config_path)
    log.debug("Configuration dogstatsd")

    port      = c['dogstatsd_port']
    interval  = int(c['dogstatsd_interval'])
    api_key   = c['api_key']
    non_local_traffic = c['non_local_traffic']
    forward_to_host = c.get('statsd_forward_host')
    forward_to_port = c.get('statsd_forward_port')

    target = c['dd_url']
    if use_forwarder:
        target = c['dogstatsd_target']

    hostname = get_hostname(c)

    # Create the aggregator (which is the point of communication between the
    # server and reporting threads.
    assert 0 < interval

    aggregator = MetricsAggregator(hostname, interval, recent_point_threshold=c.get('recent_point_threshold', None))

    # Start the reporting thread.
    reporter = Reporter(interval, aggregator, target, api_key, use_watchdog)

    # Start the server on an IPv4 stack
    # Default to loopback
    server_host = '127.0.0.1'
    # If specified, bind to all addressses
    if non_local_traffic:
        server_host = ''

    server = Server(aggregator, server_host, port, forward_to_host=forward_to_host, forward_to_port=forward_to_port)

    return reporter, server, c

def main(config_path=None):
    """ The main entry point for the unix version of dogstatsd. """
    parser = optparse.OptionParser("%prog [start|stop|restart|status]")
    parser.add_option('-u', '--use-local-forwarder', action='store_true',
                        dest="use_forwarder", default=False)
    opts, args = parser.parse_args()

    reporter, server, cnf = init(config_path, use_watchdog=True, use_forwarder=opts.use_forwarder)
    pid_file = PidFile('dogstatsd')
    daemon = Dogstatsd(pid_file.get_path(), server, reporter,
            cnf.get('autorestart', False))

    # If no args were passed in, run the server in the foreground.
    if not args:
        daemon.run()
        return 0

    # Otherwise, we're process the deamon command.
    else:
        command = args[0]

        if command == 'start':
            daemon.start()
        elif command == 'stop':
            daemon.stop()
        elif command == 'restart':
            daemon.restart()
        elif command == 'status':
            daemon.status()
        elif command == 'info':
            return daemon.info()
        else:
            sys.stderr.write("Unknown command: %s\n\n" % command)
            parser.print_help()
            return 1
        return 0


if __name__ == '__main__':
    sys.exit(main())
