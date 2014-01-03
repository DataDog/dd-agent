# stdlib
import logging
import random
import time

# project
import kima.client
from bernard.check import BernardCheck, S

log = logging.getLogger(__name__)

# FIXME: Overriding the config for Kima.
API_KEY = 'apikey_2'
BASE_URL = 'http://localhost:5000'

class Scheduler(object):
    """ Schedule Bernard checks execution. """

    # Ratio of jitter to introduce in the scheduling
    JITTER_FACTOR = 0.1

    # Check config defaults
    DEFAULT_TIMEOUT = 5
    DEFAULT_PERIOD = 15

    @classmethod
    def from_config(cls, hostname, bernard_config, dogstatsd_client):
        schedule_config = bernard_config.get('core', {}).get('schedule', {})
        bernard_checks = []

        default_options = {
            'timeout': int(schedule_config.get('timeout', cls.DEFAULT_TIMEOUT)),
            'period': int(schedule_config.get('period', cls.DEFAULT_PERIOD)),
        }

        check_configs = bernard_config.get('checks') or {}
        for check_name, check_config in check_configs.iteritems():
            try:
                check = BernardCheck.from_config(check_name, check_config,
                                                 default_options, hostname)
            except Exception:
                log.exception('Unable to load check %s' % check_name)
            else:
                bernard_checks.extend(check)

        return cls(checks=bernard_checks, config=bernard_config,
                   hostname=hostname, dogstatsd_client=dogstatsd_client)

    def __init__(self, checks, config, hostname, dogstatsd_client):
        """ Initialize scheduler """
        self.checks = checks
        self.config = config
        self.hostname = hostname
        self.dogstatsd_client = dogstatsd_client
        self.schedule_count = 0

        # Initialize schedule
        self.schedule = []
        # Allow checks to be initially schedule in the same order
        position = 0
        for check in self.checks:
            self.schedule.append((position, check))
            position += 1

        # Initialize our kima client.
        self.kima = kima.client.connect(API_KEY, BASE_URL)

        # Scheduler doesn't need to be initialize if no check
        assert self.checks
        # Don't miss checks
        assert len(self.checks) == len(self.schedule)

    def _pop_check(self):
        """Return the next scheduled check
        Because we call wait_time before it, no need to
        check if the timestamp is in the past"""
        if self.schedule:
            return self.schedule.pop(0)[1]

    def wait_time(self):
        now = time.time()
        if self.schedule[0][0] <= now:
            return 0
        else:
            return self.schedule[0][0] - now

    def _now(self):
        return time.time()

    def process(self):
        """ Execute the next scheduled check """
        check = self._pop_check()
        result = check.run(self.dogstatsd_client)
        self.schedule_count += 1

        # post results
        try:
            self.post_run(check, result)
        except Exception:
            log.error("Could not post run", exc_info=True)

        # reschedule the check
        self.reschedule_check(check)

    def reschedule_check(self, check):
        # Get the duration to wait for the next scheduling
        waiting = check.get_period()
        state = check.get_result().state
        if state == S.TIMEOUT:
            waiting = waiting * 3
        elif state == S.INVALID_OUTPUT:
            waiting = waiting * 8
        elif state == S.EXCEPTION:
            waiting = waiting * 12

        jitter_range = self.JITTER_FACTOR * waiting
        jitter = random.uniform(-jitter_range, jitter_range)

        waiting += jitter
        timestamp = self._now() + waiting

        # Reschedule the check
        i = 0
        n = len(self.schedule)

        while i < n and self.schedule[i][0] < timestamp:
            i += 1
        self.schedule.insert(i, (timestamp, check))
        assert len(self.checks) == len(self.schedule)

        log.debug('%s is rescheduled, next run in %.2fs' % (check, waiting))

    def post_run(self, check, result):
        return self.kima.post_check_run(
                check=check.name,
                status=result.status,
                output=result.message,
                timestamp=result.execution_date,
                params=check.params,
                host_name=self.hostname)
