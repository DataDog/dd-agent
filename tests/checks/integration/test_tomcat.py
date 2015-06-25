# stdlib
import os
import threading
import time
from types import ListType
import unittest

# 3p
from nose.plugins.attrib import attr

# project
from aggregator import MetricsAggregator
from dogstatsd import Server
from jmxfetch import JMXFetch

STATSD_PORT = 8126


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


@attr(requires='tomcat')
class TestTomcat(unittest.TestCase):
    def setUp(self):
        aggregator = MetricsAggregator("test_host")
        self.server = Server(aggregator, "localhost", STATSD_PORT)
        self.reporter = DummyReporter(aggregator)

        self.t1 = threading.Thread(target=self.server.start)
        self.t1.start()

        confd_path = os.path.join(os.environ['VOLATILE_DIR'], 'jmx_yaml')
        self.jmx_daemon = JMXFetch(confd_path, {'dogstatsd_port': STATSD_PORT})
        self.t2 = threading.Thread(target=self.jmx_daemon.run)
        self.t2.start()

    def tearDown(self):
        self.server.stop()
        self.reporter.finished = True
        self.jmx_daemon.terminate()

    def test_tomcat_metrics(self):
        count = 0
        while self.reporter.metrics is None:
            time.sleep(1)
            count += 1
            if count > 25:
                raise Exception("No metrics were received in 25 seconds")

        metrics = self.reporter.metrics

        self.assertTrue(isinstance(metrics, ListType))
        self.assertTrue(len(metrics) > 0)
        self.assertEquals(len([t for t in metrics if t['metric'] == "tomcat.threads.busy" and "instance:tomcat_instance" in t['tags']]), 2, metrics)
        self.assertEquals(len([t for t in metrics if t['metric'] == "tomcat.bytes_sent" and "instance:tomcat_instance" in t['tags']]), 0, metrics)
        self.assertTrue(len([t for t in metrics if "jvm." in t['metric'] and "instance:tomcat_instance" in t['tags']]) > 4, metrics)
