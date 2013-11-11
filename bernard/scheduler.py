import logging
import random
import time
import kima.client

from bernard.check import BernardCheck, R, S

log = logging.getLogger(__name__)

class Scheduler(object):
    """
    Schedule Bernard checks execution.
    """

    # Ratio of jitter to introduce in the scheduling
    JITTER_FACTOR = 0.1

    @classmethod
    def from_config(cls, hostname, bernard_config):
        schedule_config = bernard_config.get('core', {}).get('schedule', {})
        bernard_checks = []

        DEFAULT_TIMEOUT = 5
        DEFAULT_FREQUENCY = 60
        DEFAULT_ATTEMPTS = 3

        default_check_parameter = {
            'hostname': hostname,
            'timeout': int(schedule_config.get('timeout', DEFAULT_TIMEOUT)),
            'frequency': int(schedule_config.get('period', DEFAULT_FREQUENCY)),
            'attempts': int(schedule_config.get('period', DEFAULT_ATTEMPTS)),
            'notification': bernard_config.get('core', {}).get('notification', None),
            'notify_startup': bernard_config.get('core', {}).get('notify_startup', "none"),
        }

        try:
            check_configs = bernard_config.get('checks') or []
            for check_config in check_configs:
                try:
                    bernard_checks.extend(BernardCheck.from_config(check_config, default_check_parameter))
                except Exception, e:
                    log.exception(e)

        except AttributeError:
            log.info("Error while parsing Bernard configuration file. Be sure the structure is valid.")
            return []

        return cls(checks=bernard_checks, config=bernard_config,
                   hostname=hostname)

    def __init__(self, checks, config, hostname):
        """Initialize scheduler"""
        self.checks = checks
        self.config = config
        self.hostname = hostname
        self.schedule_count = 0

        # Initialize schedule
        self.schedule = []
        # Allow checks to be initially schedule in the same order
        position = 0
        for check in self.checks:
            self.schedule.append((position, check))
            position += 1
            check.last_notified_state = R.NONE

        api_key = 'apikey_2'
        base_url = 'http://localhost:9000'
        self.kima = kima.client.connect(api_key, base_url)

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
        result = check.run()
        self.schedule_count += 1

        # post results
        try:
            self.post_run(result)
        except Exception:
            log.error("Could not post run", exc_info=True)

        # reschedule the check
        self.reschedule_check(check)

    def reschedule_check(self, check):
        # Get the duration to wait for the next scheduling
        waiting = check.config['frequency']
        status = check.get_last_result().status
        if status == S.TIMEOUT:
            waiting = waiting * 3
        elif status == S.INVALID_OUTPUT:
            waiting = waiting * 8
        elif status == S.EXCEPTION:
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

    def post_run(self, result):
        return self.kima.post_monitor_run(
                # Impedence mismatch: bernard calls states what the server
                # knows as statuses. Should reconcile.
                status=result.state,
                output=result.message,
                timestamp=result.execution_date,
                host_name=self.hostname)

class SimulatedScheduler(Scheduler):
    def __init__(self, *args, **kwargs):
        Scheduler.__init__(self, *args, **kwargs)
        self.virtual_time = time.time()

    def wait_time(self):
        return 0

    def _now(self):
        """
        Set the virtual time at the end of the check execution
        Reschedule the check on a timestamp based on this virtual time
        """
        last_result = check.get_last_result()
        timestamp = self.virtual_time + last_result.execution_time
        self.virtual_time = timestamp
        return timestamp

    def _pop_check(self):
        """
        When going to run a next check in simulated time, move the
        simulated time to the next scheduled timestamp if
        it is in the future
        """
        self.virtual_time = max(self.schedule[0][0], self.virtual_time)
        if self.schedule:
            return self.schedule.pop(0)[1]

