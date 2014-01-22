import unittest
import logging
import os
import time
logger = logging.getLogger()
from bernard.scheduler import Scheduler
from bernard.check import BernardCheck, R, S
from bernard.config_parser import read_service_checks, _get_default_options
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

    def test_config_parsing(self):
        """ Dumb simple test to test that config parsing works """
        path = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(path, 'bernard_confd')
        defaults = _get_default_options()

        # A single check without an associated agent check.
        check_configs = read_service_checks([os.path.join(yaml_path, 'ntp.yaml')], defaults)
        self.assertEqual(len(check_configs), 1)
        expected_options = defaults.copy()
        expected_options.update({'timeout': 5, 'period': 15})
        ntp_check = BernardCheck.from_config(check_configs[0])
        self.assertEqual(ntp_check.options, expected_options)
        self.assertEqual(ntp_check.get_check_run_params(), {})

        # A single check with multiple instances.
        check_configs = read_service_checks([os.path.join(yaml_path, 'postgres.yaml')], defaults)
        self.assertEqual(len(check_configs), 2)
        expected_options = defaults.copy()

        pg_check1 = BernardCheck.from_config(check_configs[0])
        expected_options.update({'timeout': 2, 'period': 15, 'tag_by': ['port', 'dbname']})
        self.assertEqual(pg_check1.options, expected_options)
        self.assertEqual(pg_check1.get_check_run_params(), {'port': '5432', 'dbname': 'postgres'})

        pg_check2 = BernardCheck.from_config(check_configs[1])
        expected_options.update({'timeout': 10})
        self.assertEqual(pg_check2.options, expected_options)
        self.assertEqual(pg_check2.get_check_run_params(), {'port': '5433', 'dbname': 'proddb'})

        # Multiple checks with multiple instances, different checks per instance
        check_configs = read_service_checks([os.path.join(yaml_path, 'dd-redis.yaml')], defaults)
        self.assertEqual(len(check_configs), 4)
        expected_options = defaults.copy()

        redis_check1 = BernardCheck.from_config(check_configs[0])
        self.assertEqual(redis_check1.name, 'check_redis_latency')
        expected_options.update({'timeout': 5, 'period': 15, 'tag_by': ['port', 'db']})
        self.assertEqual(redis_check1.options, expected_options)
        self.assertEqual(redis_check1.get_check_run_params(), {'port': '6380', 'db': '0'})

        redis_check2 = BernardCheck.from_config(check_configs[1])
        self.assertEqual(redis_check2.name, 'check_redis_queue')
        expected_options.update({'additional_tags': ['redis_type:queue']})
        self.assertEqual(redis_check2.options, expected_options)
        self.assertEqual(redis_check2.get_check_run_params(), {'port': '6380', 'db': '0', 'redis_type': 'queue'})

        redis_check3 = BernardCheck.from_config(check_configs[2])
        self.assertEqual(redis_check3.name, 'check_redis_latency')
        expected_options.update({'additional_tags': []})
        self.assertEqual(redis_check3.options, expected_options)
        self.assertEqual(redis_check3.get_check_run_params(), {'port': '6379', 'db': '1'})


        redis_check4 = BernardCheck.from_config(check_configs[3])
        self.assertEqual(redis_check4.name, 'check_redis_livecache')
        expected_options.update({'additional_tags': ['redis_type:livecache']})
        self.assertEqual(redis_check4.options, expected_options)
        self.assertEqual(redis_check4.get_check_run_params(), {'port': '6379', 'db': '1', 'redis_type': 'livecache'})


    def _get_test_checks(self):
        return [
            BernardCheck.from_config(self._get_check_config('check_ok')),
            BernardCheck.from_config(self._get_check_config('check_warning')),
            BernardCheck.from_config(self._get_check_config('check_wrong_exit')),
            BernardCheck.from_config(self._get_check_config('check_disappeared')),
        ]

    def _get_timeout_check(self):
        return BernardCheck.from_config(self._get_check_config('check_timeout'))

    def _get_scheduler(self, checks):
        return Scheduler(checks, get_hostname(), FakeDogstatsd())

    def _get_check_config(self, command):
        path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(path, 'bernard_checks')
        return {
            'name': command,
            'command': os.path.join(path, command),
            'options': {
                'period': 60,
                'attempts': 3,
                'timeout': 1,
            },
            'params': {}
        }


if __name__ == '__main__':
    unittest.main()

