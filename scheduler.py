import time
import logging
import random

from util import namedtuple

from checks.bernard_check import S, R
from dogstatsd_client import DogStatsd

log = logging.getLogger('bernard')


TransitionAction = namedtuple('ResultState', ['no_event', 'ok_event', 'warning_event', 'fail_event'])
T = TransitionAction(0,1,2,3)

class Scheduler(object):

    JITTER_FACTOR = 0.1

    def __init__(self, checks, config, simulated_time=False):
        self.checks = checks
        self.config = config

        self.schedule_count = 0
        self._initialize_schedule()

        self.now = time.time

        if simulated_time:
            self.wait_time = lambda: 0
            def schedule_time_simulated(check, period):
                last_result = check.get_last_result()
                return last_result.execution_date + last_result.execution_time + period
            self._schedule_time = schedule_time_simulated

        self.notifier = Notifier(config)

    def _initialize_schedule(self):
        self.schedule = []

        for check in self.checks:
            self.schedule.append((0, check))
            check.last_notified_state = R.NONE

        assert len(self.checks) == len(self.schedule)

    def _schedule_after(self, check, period):
        t = self._schedule_time(check, period)

        b = True
        i = 0
        n = len(self.schedule)

        while i < n and self.schedule[i][0] < t:
            i += 1
        self.schedule.insert(i, (t, check))
        log.debug('%s scheduled in around %ds' %(check, period))

    def _schedule_time(self, check, period):
        jitter_range = self.JITTER_FACTOR * period
        jitter = random.uniform(-jitter_range, jitter_range)
        return time.time() + period + jitter

    def _pop_check(self):
        if self.schedule:
            return self.schedule.pop(0)[1]

    def wait_time(self):
        now = time.time()
        if not self.schedule:
            return None
        else:
            if self.schedule[0][0] <= now:
                return 0
            else:
                return self.schedule[0][0] - now

    def process(self):
        """ Execute the next scheduled check """
        check = self._pop_check()
        if check:
            frequency = check.config.get('frequency')

            log.info('Run check %s' % check)
            check.run()
            self.schedule_count += 1

            need_confirmation = self.notifier.notify_change(check)
            self._reschedule(check, need_confirmation)

        assert len(self.checks) == len(self.schedule)

    def _reschedule(self, check, fast_rescheduling=False):
        frequency = check.config['frequency']
        status = check.get_last_result().status
        if fast_rescheduling:
            frequency = frequency / 2
        elif status == S.TIMEOUT:
            frequency = frequency * 3
        elif status == S.INVALID_OUTPUT:
            frequency = frequency * 8
        elif status == S.EXCEPTION:
            frequency = frequency * 12


        self._schedule_after(check, frequency)


class Notifier(object):
    ATTEMPTS_TO_CONFIRM = 4

    def __init__(self, config):
        self.config = config

    def notify_change(self, check):
        """
        Analyze last check results and create an event if needed
        Return if a transition confirmation is needed
        """
        actions = []

        # Initialize the last_notified_state with the first result state
        if check.last_notified_state == R.NONE:
            check.last_notified_state = check.get_last_result().state

        ref_state = check.last_notified_state

        for i in range(self.ATTEMPTS_TO_CONFIRM - 1):
            state = check.get_result(i).state
            try:
                actions.append(transitions[(ref_state, state)])
            except KeyError:
                log.warn("Invalid state transition, from %s to %s" % (ref_state, state))
                actions.append(T.no_event)

        actions_set = set(actions)

        if actions_set == set([T.no_event]):
            return False

        elif T.no_event in actions_set:
            return True

        if T.no_event not in actions_set:
            alert_type = None

            action = actions[0]
            state = check.get_last_result().state

            if action == T.ok_event:
                alert_type = 'success'
            elif action == T.warning_event:
                alert_type = 'warning'
            elif action == T.fail_event:
                alert_type = 'error'

            title = '%s is %s on %s' % (check.check_name, state, check.hostname)
            text = check.get_result(0).message
            if check.config['notification']:
                text = '%s\n%s' %(text, check.config['notification'])
            check.dogstatsd.event(
                title=title,
                text=text,
                alert_type=alert_type,
                aggregation_key=check.check_name,
                hostname=check.hostname,
            )
            check.last_notified_state = state

            log.info('Event "%s" sent' % title)

            return False


transitions = {
    (R.NONE, R.OK): T.no_event,
    (R.NONE, R.WARNING): T.no_event,
    (R.NONE, R.CRITICAL): T.no_event,
    (R.NONE, R.UNKNOWN): T.no_event,
    (R.NONE, R.NONE): T.no_event,

    (R.OK, R.OK): T.no_event,
    (R.OK, R.WARNING): T.warning_event,
    (R.OK, R.CRITICAL): T.fail_event,
    (R.OK, R.UNKNOWN): T.warning_event,
    (R.OK, R.NONE): T.no_event,

    (R.WARNING, R.OK): T.ok_event,
    (R.WARNING, R.WARNING): T.no_event,
    (R.WARNING, R.CRITICAL): T.fail_event,
    (R.WARNING, R.UNKNOWN): T.no_event,
    (R.WARNING, R.NONE): T.no_event,

    (R.CRITICAL, R.OK): T.ok_event,
    (R.CRITICAL, R.WARNING): T.warning_event,
    (R.CRITICAL, R.CRITICAL): T.no_event,
    (R.CRITICAL, R.UNKNOWN): T.warning_event,
    (R.WARNING, R.NONE): T.no_event,

    (R.UNKNOWN, R.OK): T.ok_event,
    (R.UNKNOWN, R.WARNING): T.no_event,
    (R.UNKNOWN, R.CRITICAL): T.fail_event,
    (R.UNKNOWN, R.UNKNOWN): T.no_event,
    (R.UNKNOWN, R.NONE): T.no_event,
}