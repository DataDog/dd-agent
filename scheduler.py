import time
import logging
import random

from util import namedtuple

# local schedule imports
from checks.bernard_check import BernardCheck
from dogstatsd_client import DogStatsd
from util import get_hostname

# remote schedule imports
from checks.bernard_check import S, R
from checks.bernard_check import RemoteBernardCheck
import kima.client

log = logging.getLogger('bernard')


TransitionAction = namedtuple('ResultState',
    ['no_event', 'ok_event', 'warning_event', 'fail_event'])
T = TransitionAction(0, 1, 2, 3)

def init_scheduler(bernard_config):
    ''' Decides which Scheduler to initialize based on the config
    '''
    remote_schedule_config = bernard_config.get('core', {}).get('remote_schedule')

    if remote_schedule_config is None:
        return Scheduler.from_config(bernard_config)
    else:
        return RemoteScheduler.from_config(bernard_config)

class Scheduler(object):
    """
    Schedule Bernard checks execution.
    """

    # Ratio of jitter to introduce in the scheduling
    JITTER_FACTOR = 0.1

    @classmethod
    def from_config(cls, bernard_config):
        schedule_config = bernard_config.get('core', {}).get('schedule', {})
        agent_config = get_config()

        hostname = get_hostname(agent_config)
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

        statsd_config = bernard_config.get('core', {}).get('dogstatsd', {})
        statsd_host = statsd_config.get('host', 'localhost')
        statsd_port = statsd_config.get('port', 8125)
        dogstatsd = DogStatsd(host=statsd_host, port=statsd_port)

        try:
            check_configs = bernard_config.get('checks') or []
            for check_config in check_configs:
                try:
                    bernard_checks.extend(BernardCheck.from_config(check_config,
                                           dogstatsd, default_check_parameter))
                except Exception, e:
                    log.exception(e)

        except AttributeError:
            log.info("Error while parsing Bernard configuration file. Be sure the structure is valid.")
            return []

        return cls(checks=bernard_checks, config=bernard_config,
                simulated_time=False)

    def __init__(self, checks, config, simulated_time=False):
        """Initialize scheduler"""
        self.checks = checks
        self.config = config
        self.schedule_count = 0

        # Initialize schedule
        self.schedule = []
        # Allow checks to be initially schedule in the same order
        position = 0
        for check in self.checks:
            self.schedule.append((position, check))
            position += 1
            check.last_notified_state = R.NONE

        # Simulated time allow to run checks non-stop, for test use
        # It only override methods, not to alter the normal code
        if simulated_time:
            self.virtual_time = time.time()
            # With simulated time, we don't wait
            self.wait_time = lambda: 0

            def reschedule_timestamp_simulated(check, waiting):
                """
                Set the virtual time at the end of the check execution
                Reschedule the check on a timestamp based on this virtual time
                """
                last_result = check.get_last_result()
                timestamp = self.virtual_time + last_result.execution_time
                self.virtual_time = timestamp
                return timestamp + waiting
            self._reschedule_timestamp = reschedule_timestamp_simulated

            def pop_check_simulated():
                """
                When going to run a next check in simulated time, move the
                simulated time to the next scheduled timestamp if
                it is in the future
                """
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
        if self.schedule[0][0] <= now:
            return 0
        else:
            return self.schedule[0][0] - now

    def process(self):
        """ Execute the next scheduled check """
        check = self._pop_check()
        check.run()
        self.schedule_count += 1

        # Create an event if needed
        # need_confirmation allow a fast rescheduling
        need_confirmation = Notifier.notify_change(check)
        # Get the duration to wait for the next scheduling
        waiting = self._reschedule_waiting(check, need_confirmation)
        timestamp = self._reschedule_timestamp(check, waiting)
        # Reschedule the check
        self._reschedule_at(check, timestamp)

        # Each check has dogstatsd as an attribute, so we use it
        check.dogstatsd.increment('bernard.scheduler.runs')
        check.dogstatsd.gauge('bernard.scheduler.check_count', len(self.checks))

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
        """Give the rescheduled timestamp

        To have a function for that allow the simulated_time
        to override it"""
        return time.time() + waiting


class Notifier(object):
    """
    Create events based on Bernard checks results
    """

    @classmethod
    def notify_change(cls, check):
        """
        Analyze last check results and create an event if needed
        Return if a transition confirmation is needed
        """
        actions = []

        # Initialize the last_notified_state with the first result state
        if check.last_notified_state == R.NONE:
            state = check.get_last_result().state
            check.last_notified_state = state

            # Notify, depending on notify_startup configuration
            notify_startup = check.config['notify_startup']

            if notify_startup == 'none':
                pass
            elif state == R.OK and notify_startup in ['all']:
                cls.send_event(T.ok_event, check)
            elif state in [R.WARNING, R.UNKNOWN] and notify_startup in ['all', 'warning']:
                cls.send_event(T.warning_event, check)
            elif state == R.CRITICAL and notify_startup in ['all', 'warning', 'critical']:
                cls.send_event(T.fail_event, check)

        ref_state = check.last_notified_state

        # Get the transitions between the last_notified_state and #{config['attempts']}
        # last results.
        #   - If only no_event, nothing to do
        #   - If contains no_event and *_event, need to confirm the transition
        #   - If only *_event, do the state change
        for i in range(check.config['attempts']):
            state = check.get_result(i).state
            try:
                actions.append(transitions[(ref_state, state)])
            except KeyError:
                log.warn("Invalid state transition, from %s to %s" % (ref_state, state))
                actions.append(T.no_event)

        actions_set = set(actions)

        if actions_set == set([T.no_event]):
            return False

        if T.no_event in actions_set:
            return True

        if T.no_event not in actions_set:
            # Notify the last state reported
            action = actions[0]
            cls.send_event(action, check)

        return False

    @classmethod
    def send_event(cls, action, check):
        alert_type = None

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

        check.dogstatsd.increment('bernard.check.events')

        log.info('Event "%s" sent' % title)

class RemoteScheduler(Scheduler):
    @classmethod
    def from_config(cls, bernard_config):
        checks = []

        # fixme: use the same value as the agent
        host_name = 'ccabanilla-imac'
        remote_schedule_config = bernard_config.get('core', {}).get('remote_schedule', {})
        api_key = remote_schedule_config.get('api_key')
        base_url = remote_schedule_config.get('base_url', None)
        chksrv = kima.client.connect(api_key, base_url)
        tags = remote_schedule_config.get('tags', [])
        schedule = chksrv.register_agent(host_name, tags)
        for monitor in schedule.monitors:
            checks.append(RemoteBernardCheck.from_config(monitor, chksrv))

        return cls(checks=checks, config=bernard_config,
                   simulated_time=False, remote_schedule=schedule)

    def __init__(self, checks, config, simulated_time=False,
                 last_schedule_update=None, remote_schedule=None):
        Scheduler.__init__(self, checks, config, simulated_time)
        self.last_schedule_update = last_schedule_update or time.time()
        self.remote_schedule = remote_schedule

    def process(self):
        """ Execute the next scheduled check """
        check = self._pop_check()
        check.run()
        self.schedule_count += 1

        self._send_check_runs(check)

        # Get the duration to wait for the next scheduling
        waiting = self._reschedule_waiting(check, fast_rescheduling=False)
        timestamp = self._reschedule_timestamp(check, waiting)
        # Reschedule the check
        self._reschedule_at(check, timestamp)

        log.debug('%s is rescheduled, next run in %.2fs' % (check, waiting))

        assert len(self.checks) == len(self.schedule)

        # Update the check schedule, if needed
        now = time.time()
        schedule_age = now - self.last_schedule_update
        if schedule_age > self.remote_schedule.max_age:
            kima = self.checks[0].kima
            new_schedule = kima.refresh_agent_schedule(
                                                self.remote_schedule)

            prev_ids = set()
            prev_lookup = {}
            for remote_check in self.checks:
                monitor_id = remote_check.get_monitor_id()
                prev_ids.add(monitor_id)
                prev_lookup[monitor_id] = remote_check

            new_checks = []
            current_ids = set()
            current_lookup = {}
            updated_ids = set()
            for monitor in new_schedule.monitors:
                remote_check = RemoteBernardCheck.from_config(monitor, kima)
                new_checks.append(remote_check)
                monitor_id = remote_check.get_monitor_id()
                current_ids.add(monitor_id)
                current_lookup[monitor_id] = remote_check
                prev_version = prev_lookup.get(monitor_id)
                if prev_version is not None and prev_version != remote_check:
                    updated_ids.add(monitor_id)

            new_ids = current_ids - prev_ids
            removed_ids = prev_ids - current_ids

            # Build a new schedule that is the set of:
            # (current monitors) - (previously scheduled monitors),
            # making sure to preserve their order in the schedule.
            new_schedule = []
            new_position = 0
            seen = set()
            for ts, check in self.schedule:
                monitor_id = check.get_monitor_id()
                if monitor_id in current_ids:
                    updated_monitor = current_lookup.get(monitor_id)
                    new_schedule.append((ts, updated_monitor))
                    seen.add(monitor_id)
            self.schedule = new_schedule

            # Schedule the new monitors
            for monitor_id in current_ids - seen:
                monitor = current_lookup.get(monitor_id)
                self._reschedule_at(monitor,
                    self._reschedule_timestamp(monitor,
                        self._reschedule_waiting(monitor)))

            changes = [(u'Updated: %s', updated_ids, current_lookup),
                       (u'New: %s',     new_ids,     current_lookup),
                       (u'Removed: %s', removed_ids, prev_lookup)]

            msg = []
            for label, ids, lookup in changes:
                if len(ids) > 0:
                    names = [lookup[id].check_name for id in ids]
                    names.sort()
                    msg.append(label % u', '.join(names))

            if len(msg) > 0:
                log.info(u'Updated checks. %s' % '; '.join(msg))
            else:
                log.debug('Schedule is unchanged')
            self.checks = new_checks
            self.last_schedule_update = now

    def _send_check_runs(self, check):
        while len(check.result_container) > 0:
            result = check.result_container.pop()
            check.post_run(result)

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
    (R.CRITICAL, R.NONE): T.no_event,

    (R.UNKNOWN, R.OK): T.ok_event,
    (R.UNKNOWN, R.WARNING): T.no_event,
    (R.UNKNOWN, R.CRITICAL): T.fail_event,
    (R.UNKNOWN, R.UNKNOWN): T.no_event,
    (R.UNKNOWN, R.NONE): T.no_event,
}