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
import sys
from time import time
import threading
from urllib import urlencode

# project
from config import get_config
from checks import gethostname
from util import json

logger = logging.getLogger('dogstatsd')

class Metric(object):
    """
    A base metric class that accepts points, slices them into time intervals
    and performs roll-ups within those intervals.
    """

    def sample(self, value, sample_rate):
        """ Add a point to the given metric. """
        raise NotImplementedError()

    def flush(self, timestamp):
        """ Flush all metrics up to the given timestamp. """
        raise NotImplementedError()


class Gauge(Metric):
    """ A metric that tracks a value at particular points in time. """

    def __init__(self, name, tags, hostname):
        self.name = name
        self.value = None
        self.tags = tags
        self.hostname = hostname
        self.last_sample_time = None

    def sample(self, value, sample_rate):
        self.value = value
        self.last_sample_time = time()

    def flush(self, timestamp):
        # Gauges don't reset. Continue to send the same value.
        return [{
            'metric' : self.name,
            'points' : [(timestamp, self.value)],
            'tags' : self.tags,
            'host' : self.hostname
        }]


class Counter(Metric):
    """ A metric that tracks a counter value. """

    def __init__(self, name, tags, hostname):
        self.name = name
        self.value = 0
        self.tags = tags
        self.hostname = hostname

    def sample(self, value, sample_rate):
        self.value += value * int(1 / sample_rate)
        self.last_sample_time = time()

    def flush(self, timestamp):
        try:
            return [{
                'metric' : self.name,
                'points' : [(timestamp, self.value)],
                'tags' : self.tags,
                'host' : self.hostname
            }]
        finally:
            self.value = 0


class Histogram(Metric):
    """ A metric to track the distribution of a set of values. """

    def __init__(self, name, tags, hostname):
        self.name = name
        self.max = float("-inf")
        self.min = float("inf")
        self.sum = 0
        self.count = 0
        self.sample_size = 1000
        self.samples = []
        self.percentiles = [0.95]
        self.tags = tags
        self.hostname = hostname

    def sample(self, value, sample_rate):
        self.count += int(1 / sample_rate)
        self.samples.append(value)
        self.last_sample_time = time()

    def flush(self, ts):
        if not self.count:
            return []

        self.samples.sort()
        length = len(self.samples)

        max_ = self.samples[-1]
        med = self.samples[int(round(length/2 - 1))]
        avg = sum(self.samples)/length

        metrics = [
            {'host':self.hostname, 'tags': self.tags, 'metric' : '%s.max' % self.name, 'points' : [(ts, max_)]},
            {'host':self.hostname, 'tags': self.tags, 'metric' : '%s.median' % self.name, 'points' : [(ts, med)]},
            {'host':self.hostname, 'tags': self.tags, 'metric' : '%s.avg' % self.name, 'points' : [(ts, avg)]},
            {'host':self.hostname, 'tags': self.tags, 'metric' : '%s.count' % self.name, 'points' : [(ts, self.count)]},
        ]

        for p in self.percentiles:
            val = self.samples[int(round(p * length - 1))]
            name = '%s.%spercentile' % (self.name, int(p * 100))
            metrics.append({'host': self.hostname, 'tags':self.tags, 'metric': name, 'points': [(ts, val)]})

        # Reset our state.
        self.samples = []
        self.count = 0

        return metrics


class MetricsAggregator(object):
    """
    A metric aggregator class.
    """

    def __init__(self, hostname, expiry_seconds=300):
        self.metrics = {}
        self.total_count = 0
        self.count = 0
        self.metric_type_to_class = {
            'g': Gauge,
            'c': Counter,
            'h': Histogram,
            'ms' : Histogram
        }
        self.hostname = hostname
        self.expiry_seconds = expiry_seconds

    def submit(self, packet):
        self.count += 1
        # We can have colons in tags, so split once.
        name_and_metadata = packet.split(':', 1)

        if len(name_and_metadata) != 2:
            raise Exception('Unparseable packet: %s' % packet)

        name = name_and_metadata[0]
        metadata = name_and_metadata[1].split('|')

        if len(metadata) < 2:
            raise Exception('Unparseable packet: %s' % packet)

        # Parse the optional values - sample rate & tags.
        sample_rate = 1
        tags = None
        for m in metadata[2:]:
            # Parse the sample rate
            if m[0] == '@':
                sample_rate = float(m[1:])
                assert 0 <= sample_rate <= 1
            elif m[0] == '#':
                tags = tuple(sorted(m[1:].split(',')))

        context = (name, tags)
        if context not in self.metrics:
            metric_class = self.metric_type_to_class[metadata[1]]
            self.metrics[context] = metric_class(name, tags, self.hostname)
        self.metrics[context].sample(float(metadata[0]), sample_rate)


    def flush(self, include_diagnostic_stats=True):

        timestamp = time()
        expiry_timestamp = timestamp - self.expiry_seconds

        # Flush points and remove expired metrics. We mutate this dictionary
        # while iterating so don't use an iterator.
        metrics = []
        for context, metric in self.metrics.items():
            if metric.last_sample_time < expiry_timestamp:
                logger.info("%s hasnt been submitted in %ss. Expiring." % (context, self.expiry_seconds))
                del self.metrics[context]
            else:
                metrics += metric.flush(timestamp)

        # Track how many points we see.
        if include_diagnostic_stats:
            metrics.append({
                'host':self.hostname,
                'tags':None,
                'metric': 'datadog.dogstatsd.packet.count',
                'points': [(timestamp, self.count)]
            })

        # Save some stats.
        logger.info("received %s payloads since last flush" % self.count)
        self.total_count += self.count
        self.count = 0
        return metrics



class Reporter(threading.Thread):
    """
    The reporter periodically sends the aggregated metrics to the
    server.
    """

    def __init__(self, interval, metrics_aggregator, api_host, api_key=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.interval = int(interval)
        self.finished = threading.Event()
        self.metrics_aggregator = metrics_aggregator
        self.flush_count = 0

        self.api_key = api_key
        self.api_host = api_host

        self.http_conn_cls = http_client.HTTPSConnection

        match = re.match('^(https?)://(.*)', api_host)

        if match:
            self.api_host = match.group(2)
            if match.group(1) == 'http':
                self.http_conn_cls = http_client.HTTPConnection

    def end(self):
        self.finished.set()

    def run(self):
        logger.info("Reporting to %s every %ss" % (self.api_host, self.interval))
        while True:
            if self.finished.is_set():
                print 'reporter is finished!'
                break
            self.finished.wait(self.interval)
            self.flush()

    def flush(self):
        try:
            self.flush_count += 1
            metrics = self.metrics_aggregator.flush()
            count = len(metrics)
            if not count:
                logger.info("Flush #{0}: No metrics to flush.".format(self.flush_count))
                return
            logger.info("Flush #{0}: flushing {1} metrics".format(self.flush_count, count))
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
        self.socket.bind(self.address)

    def start(self):
        """ Run the server. """
        logger.info('Listening on host & port: %s' % str(self.address))

        while True:
            try:
                self.submit()
            except (KeyboardInterrupt, SystemExit):
                break
            except:
                logger.exception('Error receiving datagram')

    def submit(self):
        """ Submit metrics to the aggregator """
        buffer_size = self.buffer_size
        aggregator_submit = self.metrics_aggregator.submit
        socket_recv = self.socket.recv
        aggregator_submit(socket_recv(buffer_size))

def init(config_path=None):
    c = get_config(parse_args=False, cfg_path=config_path, init_logging=True)

    logger.info("Starting dogstatsd")

    port     = c['dogstatsd_port']
    target   = c['dogstatsd_target']
    interval = c['dogstatsd_interval']
    api_key  = c['api_key']

    hostname = gethostname(c)

    # Create the aggregator (which is the point of communication between the
    # server and reporting threads.
    aggregator = MetricsAggregator(hostname)  

    # Start the reporting thread.
    reporter = Reporter(interval, aggregator, target, api_key)
    reporter.start()

    # Start the server.
    server_host = ''
    server = Server(aggregator, server_host, port)

    return reporter, server

def main(config_path=None):
    reporter, server = init(config_path)
    server.start()

    # If we're here, we're done.
    logger.info("Shutting down ...")

if __name__ == '__main__':
    main()
