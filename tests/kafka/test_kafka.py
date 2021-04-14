# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import threading
import time
from types import ListType
import unittest
import os
import mock

# 3p
from nose.plugins.attrib import attr

# project
from aggregator import MetricsAggregator
import logging


log = logging.getLogger('kafka_test')

STATSD_PORT = 8121

LOG_INFO = {
    'log_to_event_viewer': False,
    'log_to_syslog': False,
    'syslog_host': None,
    'syslog_port': None,
    'log_level': logging.INFO,
    'disable_file_logging': True,
    'collector_log_file': '/tmp/collector.log',
    'forwarder_log_file': '/tmp/forwarder.log',
    'dogstatsd_log_file': '/tmp/dogstatsd.log',
    'jmxfetch_log_file': '/tmp/datadog/jmxfetch.log',
    'go-metro_log_file': '/tmp/datadog/go-metro.log',
}

with mock.patch('config.get_logging_config', return_value=LOG_INFO):
    from jmxfetch import JMXFetch
    from dogstatsd import Server

class DummyReporter(threading.Thread):
    def __init__(self, metrics_aggregator):
        threading.Thread.__init__(self)
        self.finished = threading.Event()
        self.metrics_aggregator = metrics_aggregator
        self.interval = 10
        self.metrics = None
        self.finished = False
        self.start()

    def run(self):
        while not self.finished:
            time.sleep(self.interval)
            self.flush()

    def flush(self):
        metrics = self.metrics_aggregator.flush()
        if metrics:
            self.metrics = metrics


@attr(requires='kafka')
class TestKafka(unittest.TestCase):
    """Basic Test for kafka integration."""
    def setUp(self):
        aggregator = MetricsAggregator("test_host")
        self.server = Server(aggregator, "localhost", STATSD_PORT)
        self.reporter = DummyReporter(aggregator)

        self.t1 = threading.Thread(target=self.server.start)
        self.t1.start()

        confd_path = os.path.join(os.path.dirname(__file__), 'resources/')

        self.jmx_daemon = JMXFetch(confd_path, {'dogstatsd_port': STATSD_PORT})
        self.t2 = threading.Thread(target=self.jmx_daemon.run)
        self.t2.start()

    def tearDown(self):
        self.server.stop()
        self.reporter.finished = True
        self.jmx_daemon.terminate()

    def testCustomJMXMetric(self):
        count = 0
        while self.reporter.metrics is None:
            time.sleep(1)
            count += 1
            if count > 25:
                raise Exception("No metrics were received in 25 seconds")

        metrics = self.reporter.metrics
        # expected_tags = ['env:test', 'instance:kafka-172.17.0.1-9999', 'kafka:broker']

        self.assertTrue(isinstance(metrics, ListType))
        self.assertTrue(len(metrics) > 0)
        log.info(metrics)
        log.info(len(metrics))
        self.assertTrue(
            len([t for t in metrics if "jvm." in t['metric'] and "instance:kafka-172.17.0.1-9999" in t['tags']]) >= 13, metrics)
        self.assertTrue(
            len([t for t in metrics if "kafka.request." in t['metric'] and "instance:kafka-172.17.0.1-9999" in t['tags']]) == 12, metrics)
        self.assertTrue(
            len([t for t in metrics if "kafka.replication." in t['metric'] and "instance:kafka-172.17.0.1-9999" in t['tags']]) == 6, metrics)

        # CLIENT metrics.
        # kafka.producer.request_latency_avg
        self.assertTrue(
            len([t for t in metrics if "kafka.producer." in t['metric'] and "instance:kafka-172.17.0.1-7777" in t['tags']]) == 1, metrics)
        # kafka.consumer.fetch_rate, kafka.consumer.max_lag
        self.assertTrue(
            len([t for t in metrics if "kafka.consumer." in t['metric'] and "instance:kafka-172.17.0.1-7777" in t['tags']]) == 2, metrics)


        # self.assertTrue(
        #     len([t for t in metrics if "kafka.follower." in t['metric'] and "instance:kafka-172.17.0.1-9999" in t['tags']]) > 40, metrics)
        # self.assertTrue(
        #     len([t for t in metrics if "kafka.net." in t['metric'] and "instance:kafka-172.17.0.1-9999" in t['tags']]) > 40, metrics)
        # self.assertTrue(
        #     len([t for t in metrics if "kafka.messages_in" in t['metric'] and "instance:kafka-172.17.0.1-9999" in t['tags']]) > 40, metrics)
