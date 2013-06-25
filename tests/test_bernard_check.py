import unittest
import logging
import os
logger = logging.getLogger()
from checks.bernard_check import BernardCheck, R, S
from dogstatsd_client import DogStatsd

class TestBernardCheck(unittest.TestCase):
    "Tests to validate the Bernard check logic"

    def get_test_checks(self):
        dogstatsd = FakeDogstatsd()
        path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(path, 'bernard_checks')

        config = {
            'frequency': 60,
            'attempts': 3,
            'timeout': 1,
            'notification': '',
        }

        return [
            BernardCheck(os.path.join(path, 'check_ok'), config, dogstatsd),
            BernardCheck(os.path.join(path, 'check_warning'), config, dogstatsd),
            BernardCheck(os.path.join(path, 'check_timeout'), config, dogstatsd),
            BernardCheck(os.path.join(path, 'check_wrong_exit'), config, dogstatsd),
            BernardCheck(os.path.join(path, 'check_disappeared'), config, dogstatsd),
        ]

    def test_result(self):
        check_ok, check_warning, check_timeout, check_wrong_exit, check_disappeared = self.get_test_checks()

        check_ok.run()
        result = check_ok.get_last_result()
        self.assertEqual(result.state, R.OK)
        self.assertEqual(result.status, S.OK)

        check_warning.run()
        result = check_warning.get_last_result()
        self.assertEqual(result.state, R.WARNING)
        self.assertEqual(result.status, S.OK)

        check_timeout.run()
        result = check_timeout.get_last_result()
        self.assertEqual(result.state, R.UNKNOWN)
        self.assertEqual(result.status, S.TIMEOUT)

        check_wrong_exit.run()
        result = check_wrong_exit.get_last_result()
        self.assertEqual(result.state, R.UNKNOWN)
        self.assertEqual(result.status, S.INVALID_OUTPUT)

        check_disappeared.run()
        result = check_disappeared.get_last_result()
        self.assertEqual(result.state, R.UNKNOWN)
        self.assertEqual(result.status, S.EXCEPTION)

    def test_perfdata_metrics(self):
        check_ok, check_warning, check_timeout, check_wrong_exit, check_disappeared = self.get_test_checks()
        metric = {}

        check_ok.run()
        for metric in check_ok.dogstatsd.metrics:
            if metric['metric'] == 'bernard.ok.metric1':
                metric = m
        self.assertEqual(metric.get('value'), 30)
        self.assertEqual(metric.get('metric_type'), 'g')

        check_warning.run()
        for metric in check_warning.dogstatsd.metrics:
            if metric['metric'] == 'bernard.warning.timing':
                metric = m
        self.assertEqual(metric.get('value'), 0.001)
        self.assertEqual(metric.get('metric_type'), 'g')
        for metric in check_warning.dogstatsd.metrics:
            if metric['metric'] == 'bernard.warning.count':
                metric = m
        self.assertEqual(metric.get('value'), 1234)
        self.assertEqual(metric.get('metric_type'), '_dd-r')


if __name__ == '__main__':
    unittest.main()

class FakeDogstatsd(DogStatsd):
    """Fake DogStatsd client, which keeps requests to test them"""

    def __init__(self, host='localhost', port=8125):
        self.host = host
        self.port = port
        self.metrics = []
        self.events = []

    def _send(self, metric, metric_type, value, tags, sample_rate):
        self.metrics.append({
            'metric': metric,
            'metric_type': metric_type,
            'value': value,
            'tags': tags,
            'sample_rate': sample_rate,
            })

    def event(self, title, text, alert_type=None, aggregation_key=None, source_type_name=None, date_happened=None, priority=None, tags=None, hostname=None):
        self.events.append({
            'title': title,
            'text': text,
            'alert_type': alert_type,
            'aggregation_key': aggregation_key,
            'source_type_name': source_type_name,
            'date_happened': date_happened,
            'priority': priority,
            'tags': tags,
            'hostname': hostname,
            })

    def flush(self):
        self.metrics = []
        self.events = []