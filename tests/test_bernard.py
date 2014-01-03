import unittest
import logging
import os
import time
logger = logging.getLogger()
from bernard.scheduler import Scheduler
from bernard.check import BernardCheck, R, S
from dogstatsd_client import DogStatsd
from util import get_hostname

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

class TestBernardCheck(unittest.TestCase):
    "Tests to validate the Bernard check logic"


    def test_timeout_check(self):
        """Specific tests for timeout checks to make tests faster"""
        check_timeout = self._get_timeout_check()
        dogstatsd = FakeDogstatsd()

        start = time.time()
        check_timeout.run(dogstatsd)
        end = time.time()

        # Check status and state
        result = check_timeout.get_result()
        self.assertEqual(result.status, R.UNKNOWN)
        self.assertEqual(result.state, S.TIMEOUT)

        # Check execution duration. Timeout is 1s, let's give it 1.2s to run.
        self.assertTrue(result.execution_time < 1.2)
        self.assertTrue(end - start < 1.2)

    def test_result(self):
        """Test result of each checks: if status and states are okay"""
        check_ok, check_warning, check_wrong_exit, check_disappeared = self._get_test_checks()
        dogstatsd_client = FakeDogstatsd()

        check_ok.run(dogstatsd_client)
        check_warning.run(dogstatsd_client)
        check_wrong_exit.run(dogstatsd_client)
        check_disappeared.run(dogstatsd_client)

        result = check_ok.get_result()
        self.assertEqual(result.status, R.OK)
        self.assertEqual(result.state, S.OK)

        result = check_warning.get_result()
        self.assertEqual(result.status, R.WARNING)
        self.assertEqual(result.state, S.OK)

        result = check_wrong_exit.get_result()
        self.assertEqual(result.status, R.UNKNOWN)
        self.assertEqual(result.state, S.INVALID_OUTPUT)

        result = check_disappeared.get_result()
        self.assertEqual(result.status, R.UNKNOWN)
        self.assertEqual(result.state, S.EXCEPTION)

    def test_perfdata_metrics(self):
        """Test perfdata metrics: if the parsing, scaling and dogstatsd calls are okay"""
        check_ok, check_warning, check_wrong_exit, check_disappeared = self._get_test_checks()
        dogstatsd_client = FakeDogstatsd()
        metric = {}

        check_ok.run(dogstatsd_client)
        for m in dogstatsd_client.metrics:
            if m['metric'] == 'bernard.check_ok.metric1':
                metric = m
        self.assertEqual(metric.get('value'), 30)
        self.assertEqual(metric.get('metric_type'), 'g')

        check_warning.run(dogstatsd_client)
        for m in dogstatsd_client.metrics:
            if m['metric'] == 'bernard.check_warning.timing':
                metric = m
        self.assertEqual(metric.get('value'), 0.001)
        self.assertEqual(metric.get('metric_type'), 'g')
        for m in dogstatsd_client.metrics:
            if m['metric'] == 'bernard.check_warning.count':
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
        self.assertEqual(scheduler.schedule[0][1].name, check_ok.name)
        self.assertEqual(scheduler.schedule[1][1].name, check_warning.name)
        self.assertEqual(scheduler.schedule[2][1].name, check_wrong_exit.name)
        self.assertEqual(scheduler.schedule[3][1].name, check_disappeared.name)

        # Should run each check once
        scheduler.process()
        scheduler.process()
        scheduler.process()
        scheduler.process()

        # Look at the new schedule
        self.assertEqual(scheduler.schedule[0][1].name, check_ok.name)
        self.assertEqual(scheduler.schedule[1][1].name, check_warning.name)
        self.assertEqual(scheduler.schedule[2][1].name, check_wrong_exit.name)
        self.assertEqual(scheduler.schedule[3][1].name, check_disappeared.name)

        # Be sure that schedule order corresponds to timestamps
        self.assertTrue(scheduler.schedule[1][0] <= scheduler.schedule[1][0])
        self.assertTrue(scheduler.schedule[1][0] <= scheduler.schedule[2][0])
        self.assertTrue(scheduler.schedule[2][0] <= scheduler.schedule[3][0])

    def _get_test_checks(self):
        return [
            BernardCheck.from_config('check_ok', self._get_check_config('check_ok'), {})[0],
            BernardCheck.from_config('check_warning', self._get_check_config('check_warning'), {})[0],
            BernardCheck.from_config('check_wrong_exit', self._get_check_config('check_wrong_exit'), {})[0],
            BernardCheck.from_config('check_disappeared', self._get_check_config('check_disappeared'), {})[0],
        ]

    def _get_timeout_check(self):
        return BernardCheck.from_config('check_timeout', self._get_check_config('check_timeout'), {})[0]

    def _get_scheduler(self, checks):
        return Scheduler(checks, {}, get_hostname(), FakeDogstatsd())

    def _get_check_config(self, command):
        path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(path, 'bernard_checks')
        return {
            'command': os.path.join(path, command),
            'options': {
                'period': 60,
                'attempts': 3,
                'timeout': 1,
            }
        }


if __name__ == '__main__':
    unittest.main()

