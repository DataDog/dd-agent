#!/opt/datadog-agent/embedded/bin/python

# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""
A Python Statsd implementation with some datadog special sauce.
"""
# set up logging before importing any other components
from config import initialize_logging  # noqa
initialize_logging('dogstatsd')


from utils.proxy import set_no_proxy_settings  # noqa
set_no_proxy_settings()

# stdlib
import os
import logging
import optparse
import select
import signal
import socket
import sys
import threading
from time import sleep, time
from urllib import urlencode
import zlib

# For pickle & PID files, see issue 293
os.umask(022)

# 3rd party
import requests
import simplejson as json

# project
from aggregator import get_formatter, MetricsBucketAggregator
from checks.check_status import DogstatsdStatus
from checks.metric_types import MetricTypes
from config import get_config, get_version
from daemon import AgentSupervisor, Daemon
from util import chunks, get_uuid, plural
from utils.hostname import get_hostname
from utils.net import inet_pton
from utils.net import IPV6_V6ONLY, IPPROTO_IPV6
from utils.pidfile import PidFile
from utils.watchdog import Watchdog
from utils.tmp_files import setup_temp_dir

# urllib3 logs a bunch of stuff at the info level
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.WARN)
requests_log.propagate = True

log = logging.getLogger('dogstatsd')

PID_NAME = "dogstatsd"
PID_DIR = None

# Dogstatsd constants in seconds
DOGSTATSD_FLUSH_INTERVAL = 10
DOGSTATSD_AGGREGATOR_BUCKET_SIZE = 10


WATCHDOG_TIMEOUT = 120
UDP_SOCKET_TIMEOUT = 5
# Since we call flush more often than the metrics aggregation interval, we should
#  log a bunch of flushes in a row every so often.
FLUSH_LOGGING_PERIOD = 70
FLUSH_LOGGING_INITIAL = 10
FLUSH_LOGGING_COUNT = 5
EVENT_CHUNK_SIZE = 50
COMPRESS_THRESHOLD = 1024


def add_serialization_status_metric(status, hostname):
    """
    Add a metric to track the number of metric serializations,
    tagged by their status.
    """
    interval = 10.0
    value = 1
    return {
        'tags': ["status:{0}".format(status)],
        'metric': 'datadog.dogstatsd.serialization_status',
        'interval': interval,
        'device_name': None,
        'host': hostname,
        'points': [(time(), value / interval)],
        'type': MetricTypes.RATE,
    }


def unicode_metrics(metrics):
    for i, metric in enumerate(metrics):
        for key, value in metric.items():
            if isinstance(value, basestring):
                metric[key] = unicode(value, errors='replace')
            elif isinstance(value, tuple) or isinstance(value, list):
                value_list = list(value)
                for j, value_element in enumerate(value_list):
                    if isinstance(value_element, basestring):
                        value_list[j] = unicode(value_element, errors='replace')
                metric[key] = tuple(value_list)
        metrics[i] = metric
    return metrics


def serialize_metrics(metrics, hostname):
    try:
        metrics.append(add_serialization_status_metric("success", hostname))
        serialized = json.dumps({"series": metrics})
    except UnicodeDecodeError as e:
        log.exception("Unable to serialize payload. Trying to replace bad characters. %s", e)
        metrics.append(add_serialization_status_metric("failure", hostname))
        try:
            log.error(metrics)
            serialized = json.dumps({"series": unicode_metrics(metrics)})
        except Exception as e:
            log.exception("Unable to serialize payload. Giving up. %s", e)
            serialized = json.dumps({"series": [add_serialization_status_metric("permanent_failure", hostname)]})

    if len(serialized) > COMPRESS_THRESHOLD:
        headers = {'Content-Type': 'application/json',
                   'Content-Encoding': 'deflate'}
        serialized = zlib.compress(serialized)
    else:
        headers = {'Content-Type': 'application/json'}
    return serialized, headers


def serialize_event(event):
    return json.dumps(event)


def mapto_v6(addr):
    """
    Map an IPv4 address to an IPv6 one.
    If the address is already an IPv6 one, just return it.
    Return None if the IP address is not valid.
    """
    try:
        inet_pton(socket.AF_INET, addr)
        return '::ffff:{}'.format(addr)
    except socket.error:
        try:
            inet_pton(socket.AF_INET6, addr)
            return addr
        except socket.error:
            log.debug('%s is not a valid IP address.', addr)

    return None


def get_socket_address(host, port, ipv4_only=False):
    """
    Gather informations to open the server socket.
    Try to resolve the name giving precedence to IPv4 for retro compatibility
    but still mapping the host to an IPv6 address, fallback to IPv6.
    """
    try:
        info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)
    except socket.gaierror as e:
        try:
            if not ipv4_only:
                info = socket.getaddrinfo(host, port, socket.AF_INET6, socket.SOCK_DGRAM)
            elif host == 'localhost':
                log.warning("Warning localhost seems undefined in your host file, using 127.0.0.1 instead")
                info = socket.getaddrinfo('127.0.0.1', port, socket.AF_INET, socket.SOCK_DGRAM)
            else:
                log.error('Error processing host %s and port %s: %s', host, port, e)
                return None
        except socket.gaierror as e:
            log.error('Error processing host %s and port %s: %s', host, port, e)
            return None

    # we get the first item of the list and map the address for IPv4 hosts
    sockaddr = info[0][-1]
    if info[0][0] == socket.AF_INET and not ipv4_only:
        mapped_host = mapto_v6(sockaddr[0])
        sockaddr = (mapped_host, sockaddr[1], 0, 0)
    return sockaddr


class Reporter(threading.Thread):
    """
    The reporter periodically sends the aggregated metrics to the
    server.
    """

    def __init__(self, interval, metrics_aggregator, api_host, api_key=None,
                 use_watchdog=False, event_chunk_size=None):
        threading.Thread.__init__(self)
        self.interval = int(interval)
        self.finished = threading.Event()
        self.metrics_aggregator = metrics_aggregator
        self.flush_count = 0
        self.log_count = 0
        self.hostname = get_hostname()

        self.watchdog = None
        if use_watchdog:
            self.watchdog = Watchdog.create(WATCHDOG_TIMEOUT)

        self.api_key = api_key
        self.api_host = api_host
        self.event_chunk_size = event_chunk_size or EVENT_CHUNK_SIZE

    def stop(self):
        log.info("Stopping reporter")
        self.finished.set()

    def run(self):

        log.info("Reporting to %s every %ss" % (self.api_host, self.interval))
        log.debug("Watchdog enabled: %s" % bool(self.watchdog))

        # Persist a start-up message.
        DogstatsdStatus().persist()

        while not self.finished.isSet():  # Use camel case isSet for 2.4 support.
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
            self.log_count += 1
            packets_per_second = self.metrics_aggregator.packets_per_second(self.interval)
            packet_count = self.metrics_aggregator.total_count

            metrics = self.metrics_aggregator.flush()
            count = len(metrics)
            if self.flush_count % FLUSH_LOGGING_PERIOD == 0:
                self.log_count = 0
            if count:
                self.submit(metrics)

            events = self.metrics_aggregator.flush_events()
            event_count = len(events)
            if event_count:
                self.submit_events(events)

            service_checks = self.metrics_aggregator.flush_service_checks()
            service_check_count = len(service_checks)
            if service_check_count:
                self.submit_service_checks(service_checks)

            should_log = self.flush_count <= FLUSH_LOGGING_INITIAL or self.log_count <= FLUSH_LOGGING_COUNT
            log_func = log.info
            if not should_log:
                log_func = log.debug
            log_func("Flush #%s: flushed %s metric%s, %s event%s, and %s service check run%s" % (self.flush_count, count, plural(count), event_count, plural(event_count), service_check_count, plural(service_check_count)))
            if self.flush_count == FLUSH_LOGGING_INITIAL:
                log.info("First flushes done, %s flushes will be logged every %s flushes." % (FLUSH_LOGGING_COUNT, FLUSH_LOGGING_PERIOD))

            # Persist a status message.
            packet_count = self.metrics_aggregator.total_count
            DogstatsdStatus(
                flush_count=self.flush_count,
                packet_count=packet_count,
                packets_per_second=packets_per_second,
                metric_count=count,
                event_count=event_count,
                service_check_count=service_check_count,
            ).persist()

        except Exception:
            if self.finished.isSet():
                log.debug("Couldn't flush metrics, but that's expected as we're stopping")
            else:
                log.exception("Error flushing metrics")

    def submit(self, metrics):
        body, headers = serialize_metrics(metrics, self.hostname)
        params = {}
        if self.api_key:
            params['api_key'] = self.api_key
        url = '%s/api/v1/series?%s' % (self.api_host, urlencode(params))
        self.submit_http(url, body, headers)

    def submit_events(self, events):
        headers = {'Content-Type':'application/json'}
        event_chunk_size = self.event_chunk_size

        for chunk in chunks(events, event_chunk_size):
            payload = {
                'apiKey': self.api_key,
                'events': {
                    'api': chunk
                },
                'uuid': get_uuid(),
                'internalHostname': get_hostname()
            }
            params = {}
            if self.api_key:
                params['api_key'] = self.api_key
            url = '%s/intake?%s' % (self.api_host, urlencode(params))

            self.submit_http(url, json.dumps(payload), headers)

    def submit_http(self, url, data, headers):
        headers["DD-Dogstatsd-Version"] = get_version()
        log.debug("Posting payload to %s" % url)
        try:
            start_time = time()
            r = requests.post(url, data=data, timeout=5, headers=headers)
            r.raise_for_status()

            if r.status_code >= 200 and r.status_code < 205:
                log.debug("Payload accepted")

            status = r.status_code
            duration = round((time() - start_time) * 1000.0, 4)
            log.debug("%s POST %s (%sms)" % (status, url, duration))
        except Exception:
            log.exception("Unable to post payload.")
            try:
                log.error("Received status code: {0}".format(r.status_code))
            except Exception:
                pass

    def submit_service_checks(self, service_checks):
        headers = {'Content-Type':'application/json'}

        params = {}
        if self.api_key:
            params['api_key'] = self.api_key

        url = '{0}/api/v1/check_run?{1}'.format(self.api_host, urlencode(params))
        self.submit_http(url, json.dumps(service_checks), headers)


class Server(object):
    """
    A statsd udp server.
    """
    def __init__(self, metrics_aggregator, host, port, forward_to_host=None, forward_to_port=None):
        self.sockaddr = None
        self.socket = None
        self.metrics_aggregator = metrics_aggregator
        self.host = host
        self.port = port
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
            except Exception:
                log.exception("Error while setting up connection to external statsd server")

    def start(self):
        """
        Run the server.
        """
        ipv4_only = False
        try:
            # Bind to the UDP socket in IPv4 and IPv6 compatibility mode
            self.socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            # Configure the socket so that it accepts connections from both
            # IPv4 and IPv6 networks in a portable manner.
            self.socket.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)
        except Exception:
            log.info('unable to create IPv6 socket, falling back to IPv4.')
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ipv4_only = True

        self.socket.setblocking(0)

        #let's get the sockaddr
        self.sockaddr = get_socket_address(self.host, int(self.port), ipv4_only=ipv4_only)

        try:
            self.socket.bind(self.sockaddr)
        except TypeError:
            log.error('Unable to start Dogstatsd server loop, exiting...')
            return

        log.info('Listening on socket address: %s', str(self.sockaddr))

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
        message = None
        while self.running:
            try:
                ready = select_select(sock, [], [], timeout)
                if ready[0]:
                    message = socket_recv(buffer_size)
                    aggregator_submit(message)

                    if should_forward:
                        forward_udp_sock.send(message)
            except select_error as se:
                # Ignore interrupted system calls from sigterm.
                errno = se[0]
                if errno != 4:
                    raise
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception:
                log.exception('Error receiving datagram `%s`', message)

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
            except Exception as e:
                log.exception(
                    'Error starting dogstatsd server on %s', self.server.sockaddr)
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

    @classmethod
    def info(self):
        logging.getLogger().setLevel(logging.ERROR)
        return DogstatsdStatus.print_latest_status()


def init(config_path=None, use_watchdog=False, use_forwarder=False, args=None):
    """Configure the server and the reporting thread.
    """
    c = get_config(parse_args=False, cfg_path=config_path)
    setup_temp_dir(c, proc_name='dogstatsd')

    if (not c['use_dogstatsd'] and
            (args and args[0] in ['start', 'restart'] or not args)):
        log.info("Dogstatsd is disabled. Exiting")
        # We're exiting purposefully, so exit with zero (supervisor's expected
        # code). HACK: Sleep a little bit so supervisor thinks we've started cleanly
        # and thus can exit cleanly.
        sleep(4)
        sys.exit(0)

    port = c['dogstatsd_port']
    interval = DOGSTATSD_FLUSH_INTERVAL
    api_key = c['api_key']
    aggregator_interval = DOGSTATSD_AGGREGATOR_BUCKET_SIZE
    non_local_traffic = c['non_local_traffic']
    forward_to_host = c.get('statsd_forward_host')
    forward_to_port = c.get('statsd_forward_port')
    event_chunk_size = c.get('event_chunk_size')
    recent_point_threshold = c.get('recent_point_threshold', None)
    server_host = c['bind_host']

    target = c['dd_url']
    if use_forwarder:
        target = c['dogstatsd_target']

    hostname = get_hostname(c)

    # Create the aggregator (which is the point of communication between the
    # server and reporting threads.
    assert 0 < interval

    aggregator = MetricsBucketAggregator(
        hostname,
        aggregator_interval,
        recent_point_threshold=recent_point_threshold,
        formatter=get_formatter(c),
        histogram_aggregates=c.get('histogram_aggregates'),
        histogram_percentiles=c.get('histogram_percentiles'),
        utf8_decoding=c['utf8_decoding']
    )

    # Start the reporting thread.
    reporter = Reporter(interval, aggregator, target, api_key, use_watchdog, event_chunk_size)

    # NOTICE: when `non_local_traffic` is passed we need to bind to any interface on the box. The forwarder uses
    # Tornado which takes care of sockets creation (more than one socket can be used at once depending on the
    # network settings), so it's enough to just pass an empty string '' to the library.
    # In Dogstatsd we use a single, fullstack socket, so passing '' as the address doesn't work and we default to
    # '0.0.0.0'. If someone needs to bind Dogstatsd to the IPv6 '::', they need to turn off `non_local_traffic` and
    # use the '::' meta address as `bind_host`.
    if non_local_traffic:
        server_host = '0.0.0.0'

    server = Server(aggregator, server_host, port, forward_to_host=forward_to_host, forward_to_port=forward_to_port)

    return reporter, server, c


def main(config_path=None):
    """ The main entry point for the unix version of dogstatsd. """
    COMMANDS_START_DOGSTATSD = [
        'start',
        'stop',
        'restart',
        'status'
    ]

    parser = optparse.OptionParser("%prog [start|stop|restart|status]")
    parser.add_option('-u', '--use-local-forwarder', action='store_true',
                      dest="use_forwarder", default=False)
    opts, args = parser.parse_args()

    in_developer_mode = False
    if not args or args[0] in COMMANDS_START_DOGSTATSD:
        reporter, server, cnf = init(config_path, use_watchdog=True, use_forwarder=opts.use_forwarder, args=args)
        daemon = Dogstatsd(PidFile(PID_NAME, PID_DIR).get_path(), server, reporter,
                           cnf.get('autorestart', False))
        in_developer_mode = cnf.get('developer_mode')

    # If no args were passed in, run the server in the foreground.
    if not args:
        daemon.start(foreground=True)
        return 0

    # Otherwise, we're process the deamon command.
    else:
        command = args[0]

        # TODO: actually kill the start/stop/restart/status command for 5.11
        if command in ['start', 'stop', 'restart', 'status'] and not in_developer_mode:
            logging.error('Please use supervisor to manage the agent')
            return 1

        if command == 'start':
            daemon.start()
        elif command == 'stop':
            daemon.stop()
        elif command == 'restart':
            daemon.restart()
        elif command == 'status':
            daemon.status()
        elif command == 'info':
            return Dogstatsd.info()
        else:
            sys.stderr.write("Unknown command: %s\n\n" % command)
            parser.print_help()
            return 1
        return 0

if __name__ == '__main__':
    sys.exit(main())
