# stdlib
import logging
import random
import time

# project
import datadog.checks
from bernard.check import BernardCheck, S
from config import get_config

log = logging.getLogger(__name__)

MAX_WAIT_TIME = 300

class Scheduler(object):
    """ Schedule Bernard checks execution. """

    # Ratio of jitter to introduce in the scheduling
    JITTER_FACTOR = 0.1

    @classmethod
    def from_config(cls, hostname, bernard_config, dogstatsd_client):
        bernard_checks = []

        check_configs = bernard_config.get('checks') or []
        for check_config in check_configs:
            try:
                check = BernardCheck.from_config(check_config, hostname)
            except Exception:
                log.exception('Unable to load check %s' % check_config['name'])
            else:
                bernard_checks.extend(check)

        return cls(checks=bernard_checks, hostname=hostname,
                   dogstatsd_client=dogstatsd_client)

    def __init__(self, checks, hostname, dogstatsd_client):
        """ Initialize scheduler """
        self.checks = checks
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
        agent_config = get_config()
        api_key = agent_config.get('api_key')
        dd_url = agent_config.get('dd_url')
        self.checkserv_client = datadog.checks.connect(api_key, dd_url)

    def _pop_check(self):
        """ Return the next scheduled check. Because we call wait_time before,
            no need to check if the timestamp is in the past
        """
        if self.schedule:
            return self.schedule.pop(0)[1]

    def wait_time(self):
        now = time.time()
        # FIXME: We're letting bernard run even when there are no checks
        # defined so that the init script works. We can either adjust the init
        # script to allow bernard to stop immediately or continue this way.
        if not len(self.schedule):
            return MAX_WAIT_TIME

        if self.schedule[0][0] <= now:
            return 0
        else:
            return self.schedule[0][0] - now

    def _now(self):
        return time.time()

    def process(self):
        """ Execute the next scheduled check """
        check = self._pop_check()
        if not check:
            return
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
        return self.checkserv_client.post_check_run(
                check=check.name,
                status=result.status,
                output=result.message,
                timestamp=result.execution_date,
                tags=check.get_check_run_tags(),
                host_name=self.hostname)
