import logging
import sys
import unittest
from tempfile import NamedTemporaryFile

from checks.datadog import Dogstreams

log = logging.getLogger('datadog.test')

class TailTestCase(unittest.TestCase):
    def setUp(self):
        self.log_file = NamedTemporaryFile()

    def _write_log(self, log_data):
        for data in log_data:
            print >> self.log_file, data
        self.log_file.flush()

    def tearDown(self):
        self.log_file.close()

class TestDogstream(TailTestCase):
    gauge = {'metric_type': 'gauge'}
    counter = {'metric_type': 'counter'}

    def setUp(self):
        TailTestCase.setUp(self)

        self.config = {
            'dogstreams': self.log_file.name,
            'checkFreq': 5,
        }
        log.info("Test config: %s" % self.config)
        self.dogstream = Dogstreams.init(logging.getLogger('test.dogstream'), 
            self.config)
    
    def test_dogstream_gauge(self):
        log_data = [
            # bucket 0
            ('test.metric.a', '1000000000', '10', 'metric_type=gauge'),
            ('test.metric.a', '1000000001', '20', 'metric_type=gauge'),
            ('test.metric.a', '1000000002', '3', 'metric_type=gauge'),
            ('test.metric.a', '1000000003', '4', 'metric_type=gauge'),
            ('test.metric.a', '1000000004', '5', 'metric_type=gauge'),

            # bucket 1
            ('test.metric.a', '1000000005', '12', 'metric_type=gauge'),
            ('test.metric.a', '1000000006', '7', 'metric_type=gauge'),
            ('test.metric.a', '1000000007', '8', 'metric_type=gauge'),
        ]
        
        expected_output = {
            "dogstream": [
                ('test.metric.a', 1000000000, 5.0, self.gauge),
                ('test.metric.a', 1000000005, 8.0, self.gauge),
            ]
        }
        
        self._write_log((' '.join(data) for data in log_data))

        actual_output = self.dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)
        for metric, timestamp, val, attr in expected_output['dogstream']:
            assert isinstance(val, float)
    
    def test_dogstream_counter(self):
        log_data = [
            # bucket 0
            ('test.metric.a', '1000000000', '10', 'metric_type=counter'),
            ('test.metric.a', '1000000001', '20', 'metric_type=counter'),
            ('test.metric.a', '1000000002', '3', 'metric_type=counter'),
            ('test.metric.a', '1000000003', '4', 'metric_type=counter'),
            ('test.metric.a', '1000000004', '5', 'metric_type=counter'),

            # bucket 1
            ('test.metric.a', '1000000005', '12', 'metric_type=counter'),
            ('test.metric.a', '1000000006', '7', 'metric_type=counter'),
            ('test.metric.a', '1000000007', '8', 'metric_type=counter'),
        ]
        
        expected_output = {
            "dogstream": [
                ('test.metric.a', 1000000000, 5, self.counter),
                ('test.metric.a', 1000000005, 8, self.counter),
            ]
        }
        
        self._write_log((' '.join(data) for data in log_data))

        actual_output = self.dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)
        for metric, timestamp, val, attr in expected_output['dogstream']:
            assert isinstance(val, (int, long))

    def test_dogstream_bad_input(self):
        log_data = [
            ('test.metric.e1000000000 1metric_type=gauge'),
            ('1000000001 1 metric_type=gauge tag=staging'),
            ('test_metric.e 1 1000000002 metric_type=gauge'),
            ('test_metric.e 1000000002 10 metric_type=gauge'),
        ]
        expected_output = {"dogstream":
            [('test_metric.e', 1000000000, 10, self.gauge)]
        }
        
        self._write_log(log_data)
        
        actual_output = self.dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)


if __name__ == '__main__':
    logging.basicConfig("%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s")
    unittest.main()


