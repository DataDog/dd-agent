import unittest
import time
import threading
from aggregator import MetricsAggregator
from dogstatsd import Dogstatsd, init, Server
from util import PidFile
import os
from config import get_logging_config
from jmxfetch import JMXFetch, JMX_COLLECT_COMMAND

STATSD_PORT = 8127
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


class JMXTestCase(unittest.TestCase):
    def setUp(self):
        aggregator = MetricsAggregator("test_host")
        self.server = Server(aggregator, "localhost", STATSD_PORT)
        pid_file = PidFile('dogstatsd')
        self.reporter = DummyReporter(aggregator)
        
        self.t1 = threading.Thread(target=self.server.start)
        self.t1.start()

        confd_path = os.path.realpath(os.path.join(os.path.abspath(__file__), "..", "jmx_yamls"))
        JMXFetch.init(confd_path, {'dogstatsd_port':STATSD_PORT}, get_logging_config(), 15, JMX_COLLECT_COMMAND)


    def tearDown(self):
        self.server.stop()
        self.reporter.finished = True
        JMXFetch.stop()


    def testTomcatMetrics(self):
        count = 0
        while self.reporter.metrics is None:
            time.sleep(1)
            count += 1
            if count > 20:
                raise Exception("No metrics were received in 20 seconds")

        metrics = self.reporter.metrics
        

        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 8, metrics)
        self.assertEquals(len([t for t in metrics if 'instance:solr_instance' in t['tags'] and t['metric'] == "jvm.thread_count"]), 1, metrics)
        self.assertTrue(len([t for t in metrics if "jvm." in t['metric'] and 'instance:solr_instance' in t['tags']]) > 4, metrics)
        self.assertTrue(len([t for t in metrics if "solr." in t['metric'] and 'instance:solr_instance' in t['tags']]) > 4, metrics)

if __name__ == "__main__":
    unittest.main()
