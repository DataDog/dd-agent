import logging
import sys
import unittest
from tempfile import NamedTemporaryFile

from checks.datadog import Dogstream

class TestDogstream(unittest.TestCase):
    def setUp(self):
        self.log_file = NamedTemporaryFile()
        
        self.config = {
            'dogstream_log': self.log_file.name
        }
        
        self.dogstream = Dogstream(logging.getLogger('test.dogstream'))
        
    def _write_log(self, log_data):
        for data in log_data:
            print >> self.log_file, data
        self.log_file.flush()
    
    def tearDown(self):
        self.log_file.close()
    
    def test_dogstream(self):
        log_data = [
            ('test.metric.a', '1000000000', '1', 'metric_type=counter'),
            ('test.metric.b', '1000000000', '1', 'metric_type=gauge'),
            ('test.metric.c', '1000000000', '1', 'metric_type=counter'),

            ('test.metric.a', '1000000001', '1', 'metric_type=counter'),
            ('test.metric.b', '1000000001', '2', 'metric_type=gauge'),
            ('test.metric.c', '1000000001', '2', 'metric_type=counter'),

            ('test.metric.a', '1000000002', '1', 'metric_type=counter'),
            ('test.metric.b', '1000000002', '3', 'metric_type=gauge'),
            ('test.metric.c', '1000000002', '4', 'metric_type=counter'),

            ('test.metric.a', '1000000003', '1', 'metric_type=counter'),
            ('test.metric.b', '1000000003', '4', 'metric_type=gauge'),
            ('test.metric.c', '1000000003', '8', 'metric_type=counter'),

            ('test.metric.a', '1000000004', '1', 'metric_type=counter'),

            ('test.metric.a', '1000000005', '0', 'metric_type=counter'),
            ('test.metric.b', '1000000005', '0', 'metric_type=gauge'),
            ('test.metric.c', '1000000005', '32', 'metric_type=counter'),
        ]
        
        expected_output = {
            'test.metric.a': (1000000002.5, 5),
            'test.metric.b': (1000000002.2, 2),
            'test.metric.c': (1000000002.2, 47),
        }
        
        self._write_log((' '.join(data) for data in log_data))

        actual_output = self.dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)
    
    def test_dogstream_bad_input(self):
        log_data = [
            ('test.metric.e1000000000 1metric_type=gauge'),
            ('1000000001 1 metric_type=gauge tag=staging'),
            ('test_metric.e 1 1000000002 metric_type=gauge'),
            ('test_metric.e 1000000002 10 metric_type=gauge'),
        ]
        expected_output = {
            'test_metric.e': (1000000002, 10)
        }
        
        self._write_log(log_data)
        
        actual_output = self.dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)
        


