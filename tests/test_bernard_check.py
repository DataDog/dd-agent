import unittest
import logging
import os
logger = logging.getLogger()
from checks.bernard_check import BernardCheck, R, S

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


if __name__ == '__main__':
    unittest.main()

class FakeDogstatsd(object):
    """Fake DogStatsD client, which keeps requests to test them"""

    def __init__(self, host='localhost', port=8125):
        self.host = host
        self.port = port
        self.metrics = []
        self.events = []

    def gauge(self, *args, **kargs):
        self.metrics.append(args, kargs)

    def event(self, *args, **kargs):
        self.events.append(args, kargs)
