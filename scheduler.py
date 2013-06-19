import time
import logging
import random

from util import namedtuple

from checks.bernard_check import S, R

log = logging.getLogger('bernard')


TransitionAction = namedtuple('ResultState',
    ['no_event', 'ok_event', 'warning_event', 'fail_event'])
T = TransitionAction(0, 1, 2, 3)

class Scheduler(object):
    """
    Schedule Bernard checks execution.
    """

    # Ratio of jitter to introduce in the scheduling
    JITTER_FACTOR = 0.1

    def __init__(self, checks, config, simulated_time=False):
        """Initialize scheduler"""
        self.checks = checks
        self.config = config
        self.schedule_count = 0
        self.notifier = Notifier(config)

        # Initialize schedule
        self.schedule = []
        for check in self.checks:
            self.schedule.append((0, check))
            check.last_notified_state = R.NONE

        # Simulated time allow to run checks non-stop, for test use
        # It only override methods, not to alter the normal code
        if simulated_time:
            self.virtual_time = time.time()
            self.wait_time = lambda: 0

            def reschedule_timestamp_simulated(check, waiting):
                last_result = check.get_last_result()
                timestamp = self.virtual_time + last_result.execution_time
                self.virtual_time = timestamp
                return timestamp + waiting
            self._reschedule_timestamp = reschedule_timestamp_simulated

            def pop_check_simulated():
                self.virtual_time = max(self.schedule[0][0], self.virtual_time)
                if self.schedule:
                    return self.schedule.pop(0)[1]
            self._pop_check = pop_check_simulated

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
            log.info('Run check %s' % check)
            check.run()
            self.schedule_count += 1

            # Create an event if needed
            # need_confirmation allow a fast rescheduling
            need_confirmation = self.notifier.notify_change(check)
            # Get the duration to wait for the next scheduling
            waiting = self._reschedule_waiting(check, need_confirmation)
            timestamp = self._reschedule_timestamp(check, waiting)
            # Reschedule the check
            self._reschedule_at(check, timestamp)
            log.debug('%s is rescheduled, next run in %.2fs' % (check, waiting))

        assert len(self.checks) == len(self.schedule)

    def _reschedule_waiting(self, check, fast_rescheduling=False):
        waiting = check.config['frequency']
        status = check.get_last_result().status
        if fast_rescheduling:
            waiting = waiting / 2
        elif status == S.TIMEOUT:
            waiting = waiting * 3
        elif status == S.INVALID_OUTPUT:
            waiting = waiting * 8
        elif status == S.EXCEPTION:
            waiting = waiting * 12

        jitter_range = self.JITTER_FACTOR * waiting
        jitter = random.uniform(-jitter_range, jitter_range)

        return waiting + jitter

    def _reschedule_at(self, check, timestamp):
        i = 0
        n = len(self.schedule)

        while i < n and self.schedule[i][0] < timestamp:
            i += 1
        self.schedule.insert(i, (timestamp, check))

    def _reschedule_timestamp(self, check, waiting):
        """check attribute is needed for the simulated_time"""
        return time.time() + waiting


class Notifier(object):
    """
    Create events based on Bernard checks results
    """
    ATTEMPTS_TO_CONFIRM = 3

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
            hostname = check.config['hostname']

            if action == T.ok_event:
                alert_type = 'success'
            elif action == T.warning_event:
                alert_type = 'warning'
            elif action == T.fail_event:
                alert_type = 'error'

            title = '%s is %s on %s' % (check.check_name, state, hostname)
            text = check.get_result(0).message
            if check.config['notification']:
                text = '%s\n%s' % (text, check.config['notification'])
            check.dogstatsd.event(
                title=title,
                text=text,
                alert_type=alert_type,
                aggregation_key=check.check_name,
                hostname=hostname,
            )
            check.last_notified_state = state

            log.info('Event "%s" sent' % title)

            return False

# State transitions and corresponding events
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