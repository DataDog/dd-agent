import unittest
import logging
import os
import time
logger = logging.getLogger()
from scheduler import Scheduler, Notifier
from checks.bernard_check import BernardCheck, R, S
from dogstatsd_client import DogStatsd

class TestBernardCheck(unittest.TestCase):
    "Tests to validate the Bernard check logic"


    def test_timeout_check(self):
        """Specific tests for timeout checks to make tests faster"""
        check_timeout = self._get_timeout_check()

        start = time.time()
        check_timeout.run()
        end = time.time()

        # Check status and state
        result = check_timeout.get_last_result()
        self.assertEqual(result.state, R.UNKNOWN)
        self.assertEqual(result.status, S.TIMEOUT)

        # Check execution duration. Timeout is 1s, let's give it 1.2s to run.
        self.assertTrue(result.execution_time < 1.2)
        self.assertTrue(end - start < 1.2)

    def test_result(self):
        """Test result of each checks: if status and states are okay"""
        check_ok, check_warning, check_wrong_exit, check_disappeared = self._get_test_checks()

        check_ok.run()
        check_warning.run()
        check_wrong_exit.run()
        check_disappeared.run()

        result = check_ok.get_last_result()
        self.assertEqual(result.state, R.OK)
        self.assertEqual(result.status, S.OK)

        result = check_warning.get_last_result()
        self.assertEqual(result.state, R.WARNING)
        self.assertEqual(result.status, S.OK)

        result = check_wrong_exit.get_last_result()
        self.assertEqual(result.state, R.UNKNOWN)
        self.assertEqual(result.status, S.INVALID_OUTPUT)

        result = check_disappeared.get_last_result()
        self.assertEqual(result.state, R.UNKNOWN)
        self.assertEqual(result.status, S.EXCEPTION)

    def test_perfdata_metrics(self):
        """Test perfdata metrics: if the parsing, scaling and dogstatsd calls are okay"""
        check_ok, check_warning, check_wrong_exit, check_disappeared = self._get_test_checks()
        metric = {}

        check_ok.run()
        for m in check_ok.dogstatsd.metrics:
            if m['metric'] == 'bernard.ok.metric1':
                metric = m
        self.assertEqual(metric.get('value'), 30)
        self.assertEqual(metric.get('metric_type'), 'g')

        check_warning.run()
        for m in check_warning.dogstatsd.metrics:
            if m['metric'] == 'bernard.warning.timing':
                metric = m
        self.assertEqual(metric.get('value'), 0.001)
        self.assertEqual(metric.get('metric_type'), 'g')
        for m in check_warning.dogstatsd.metrics:
            if m['metric'] == 'bernard.warning.count':
                metric = m
        self.assertEqual(metric.get('value'), 1234)
        self.assertEqual(metric.get('metric_type'), '_dd-r')

    def test_scheduler(self):
        """Test the scheduler: correct order, different schedule depending on the status"""
        checks = self._get_test_checks()
        check_ok, check_warning, check_wrong_exit, check_disappeared = checks

        scheduler = self._get_scheduler(checks)
        # Make the scheduler deterministic
        scheduler.JITTER_FACTOR = 0

        # Be sure it keeps the initial order
        self.assertEqual(scheduler.schedule[0][1].check_name, check_ok.check_name)
        self.assertEqual(scheduler.schedule[1][1].check_name, check_warning.check_name)
        self.assertEqual(scheduler.schedule[2][1].check_name, check_wrong_exit.check_name)
        self.assertEqual(scheduler.schedule[3][1].check_name, check_disappeared.check_name)

        # Should run each check once
        scheduler.process()
        scheduler.process()
        scheduler.process()
        scheduler.process()

        # Look at the new schedule
        self.assertEqual(scheduler.schedule[0][1].check_name, check_ok.check_name)
        self.assertEqual(scheduler.schedule[1][1].check_name, check_warning.check_name)
        self.assertEqual(scheduler.schedule[2][1].check_name, check_wrong_exit.check_name)
        self.assertEqual(scheduler.schedule[3][1].check_name, check_disappeared.check_name)

        # Be sure that schedule order corresponds to timestamps
        self.assertTrue(scheduler.schedule[1][0] <= scheduler.schedule[1][0])
        self.assertTrue(scheduler.schedule[1][0] <= scheduler.schedule[2][0])
        self.assertTrue(scheduler.schedule[2][0] <= scheduler.schedule[3][0])


    def _get_check_parameters(self):
        dogstatsd = FakeDogstatsd()
        path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(path, 'bernard_checks')

        config = {
            'frequency': 60,
            'attempts': 3,
            'timeout': 1,
            'notification': '',
            'notify_startup': 'none',
        }

        return path, config, dogstatsd

    def _get_test_checks(self):
        path, config, dogstatsd = self._get_check_parameters()

        return [
            BernardCheck(os.path.join(path, 'check_ok'), config, dogstatsd),
            BernardCheck(os.path.join(path, 'check_warning'), config, dogstatsd),
            BernardCheck(os.path.join(path, 'check_wrong_exit'), config, dogstatsd),
            BernardCheck(os.path.join(path, 'check_disappeared'), config, dogstatsd),
        ]

    def _get_timeout_check(self):
        path, config, dogstatsd = self._get_check_parameters()

        return BernardCheck(os.path.join(path, 'check_timeout'), config, dogstatsd)

    def _get_scheduler(self, checks):
        return Scheduler(checks=checks, config={})


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