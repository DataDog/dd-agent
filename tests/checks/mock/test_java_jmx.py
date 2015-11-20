# stdlib
import os
import tempfile
import threading
import time
from types import ListType
import unittest

# 3p
from mock import patch
from nose.plugins.attrib import attr
import yaml

# project
from aggregator import MetricsAggregator
from dogstatsd import Server
from jmxfetch import JMXFetch
from tests.checks.common import AgentCheckTest

STATSD_PORT = 8129


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


@attr('local')
class JMXInitTest(AgentCheckTest):
    CHECK_NAME = "java_jmx"

    @patch("subprocess.Popen")
    def _get_jmxfetch_subprocess_args(self, yaml_jmx_conf, mock_subprocess_call):
        # Helper function
        # Returns the Java JMX subprocess_args called from a YAML configuration
        tmp_dir = tempfile.mkdtemp()
        filename = "jmx.yaml"
        with open(os.path.join(tmp_dir, filename), 'wb') as temp_file:
            temp_file.write(yaml.dump(yaml_jmx_conf))

        jmx = JMXFetch(tmp_dir, {})
        jmx.run(reporter="console")
        return mock_subprocess_call.call_args[0][0]

    def _get_jmx_conf(self, java_options):
        return {
            'instances': [{
                'host': "localhost",
                'port': 7199,
                'java_options': java_options
            }]
        }

    def assertJavaRunsWith(self, yaml_conf, include=[], exclude=[]):
        # pylint doesn't get that the arg is the mock
        subprocess_args = self._get_jmxfetch_subprocess_args(yaml_conf)  # pylint: disable=E1120
        for i in include:
            self.assertIn(i, subprocess_args)
        for e in exclude:
            self.assertNotIn(e, subprocess_args)

    def test_jmx_start(self):
        # Empty java_options
        jmx_conf = self._get_jmx_conf("")
        self.assertJavaRunsWith(jmx_conf, ['-Xms50m', '-Xmx200m'])

        # Specified initial memory allocation pool for the JVM
        jmx_conf = self._get_jmx_conf("-Xms10m")
        self.assertJavaRunsWith(jmx_conf, ['-Xms10m', '-Xmx200m'], ['-Xms50m'])

        jmx_conf = self._get_jmx_conf("-XX:InitialHeapSize=128m")
        self.assertJavaRunsWith(jmx_conf, ['-XX:InitialHeapSize=128m', '-Xmx200m'], ['-Xms50m'])

        # Specified maximum memory allocation pool for the JVM
        jmx_conf = self._get_jmx_conf("-Xmx500m")
        self.assertJavaRunsWith(jmx_conf, ['-Xms50m', '-Xmx500m'], ['-Xmx200m'])

        jmx_conf = self._get_jmx_conf("-XX:MaxHeapSize=500m")
        self.assertJavaRunsWith(jmx_conf, ['-Xms50m', '-XX:MaxHeapSize=500m'], ['-Xmx200m'])


@attr(requires='tomcat')
class JMXTestCase(unittest.TestCase):
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

    def testCustomJMXMetric(self):
        count = 0
        while self.reporter.metrics is None:
            time.sleep(1)
            count += 1
            if count > 20:
                raise Exception("No metrics were received in 20 seconds")

        metrics = self.reporter.metrics

        self.assertTrue(isinstance(metrics, ListType))
        self.assertTrue(len(metrics) > 0)
        self.assertEquals(len([t for t in metrics if t['metric'] == "my.metric.buf" and "instance:jmx_instance1" in t['tags']]), 2, metrics)
        self.assertTrue(len([t for t in metrics if 'type:ThreadPool' in t['tags'] and "instance:jmx_instance1" in t['tags'] and "jmx.catalina" in t['metric']]) > 8, metrics)
        self.assertTrue(len([t for t in metrics if "jvm." in t['metric'] and "instance:jmx_instance1" in t['tags']]) == 13, metrics)
