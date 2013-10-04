#!/usr/bin/env python

# set up logging before importing any other components
from config import initialize_logging; initialize_logging('bernard')

import os; os.umask(022)

# Core modules
import logging
import os
import os.path
import random
import re
import signal
import subprocess
import sys
import time

# Check we're not using an old version of Python. We need 2.4 above because some modules (like subprocess)
# were only introduced in 2.4.
if int(sys.version_info[1]) <= 3:
    sys.stderr.write("Datadog agent requires python 2.4 or later.\n")
    sys.exit(2)

# Custom modules
from checks.check_status import AgentStatus, style
from config import get_config, get_parsed_args, get_config_path
from daemon import Daemon, AgentSupervisor
from util import (
    PidFile,
    StaticWatchdog,
    namedtuple,
    get_hostname,
    get_os,
    yaml,
    yLoader,
)

# Constants
RESTART_INTERVAL = 4 * 24 * 60 * 60 # Defaults to 4 days
BERNARD_CONF = "bernard.yaml"

# Globals
log = logging.getLogger('bernard')

# local schedule imports
from dogstatsd_client import DogStatsd

# remote schedule imports
import kima.client

class InvalidCheckOutput(Exception):
    pass

class Timeout(Exception):
    pass

class InvalidPath(Exception):
    pass

# Status of the execution of the check
ExecutionStatus = namedtuple('ExecutionStatus',
    ['OK', 'TIMEOUT', 'EXCEPTION', 'INVALID_OUTPUT'])
S = ExecutionStatus('ok', 'timeout', 'exception', 'invalid_output')

# State of check
ResultState = namedtuple('ResultState',
    ['NONE', 'OK', 'WARNING', 'CRITICAL', 'UNKNOWN'])
R = ResultState('init', 'ok', 'warning', 'critical', 'unknown')

TransitionAction = namedtuple('ResultState',
    ['no_event', 'ok_event', 'warning_event', 'fail_event'])
T = TransitionAction(0, 1, 2, 3)

# Represent the result of the execution of one check
CheckResult = namedtuple('CheckResult',
    ['status', 'state', 'message', 'execution_date', 'execution_time'])

def get_bernard_config():
    """Return the configuration of Bernard"""

    osname = get_os()
    config_path = get_config_path(os_name=get_os(), filename=BERNARD_CONF)

    try:
        f = open(config_path)
    except (IOError, TypeError):
        log.info("Bernard isn't configured: can't find %s" % BERNARD_CONF)
        return {}
    try:
        bernard_config = yaml.load(f.read(), Loader=yLoader)
        assert bernard_config is not None
        f.close()
    except:
        f.close()
        log.error("Unable to parse yaml config in %s" % config_path)
        return {}

    return bernard_config

class Bernard(Daemon):
    """
    The Bernard class is a daemon that runs the scheduler in a background process.
    """

    def __init__(self, pidfile, autorestart, start_event=True):
        """ Initialization of the Dameon """
        Daemon.__init__(self, pidfile)
        self.run_forever = True
        self.scheduler = None
        self.autorestart = autorestart
        self.start_event = start_event
        StaticWatchdog.reset()

    def _handle_sigterm(self, signum, frame):
        log.debug("Caught sigterm. Stopping run loop.")
        self.run_forever = False

    def _handle_sigusr1(self, signum, frame):
        self._handle_sigterm(signum, frame)
        self._do_restart()

    def info(self, verbose=None):
        logging.getLogger().setLevel(logging.ERROR)
        return BernardStatus.print_latest_status(verbose=verbose)

    def run(self):
        """Main loop of Bernard"""

        # Gracefully exit on sigterm.
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # A SIGUSR1 signals an exit with an autorestart
        signal.signal(signal.SIGUSR1, self._handle_sigusr1)

        # Handle Keyboard Interrupt
        signal.signal(signal.SIGINT, self._handle_sigterm)

        # load Bernard config and checks
        bernard_config = get_bernard_config()
        self.scheduler = init_scheduler(bernard_config)

        # Save the agent start-up stats.
        BernardStatus(checks=self.scheduler.checks).persist()
        self.last_info_update = time.time()

        # Initialize the auto-restarter
        self.restart_interval = int(RESTART_INTERVAL)
        self.agent_start = time.time()

        # Run the main loop.
        while self.run_forever:
            # Run the next scheduled check
            self.scheduler.process()

            wait_time = self.scheduler.wait_time()

            # Check if we should restart.
            if self.autorestart and self._should_restart():
                self._do_restart()

            # Update status only if more than 10s or before a long sleep
            if time.time() > self.last_info_update + 10 or wait_time > 10:
                BernardStatus(checks=self.scheduler.checks,
                    schedule_count=self.scheduler.schedule_count).persist()
                self.last_info_update = time.time()

            # Only plan for the next loop if we will continue,
            # otherwise just exit quickly.
            if self.run_forever:
                # Give more time to the Watchdog because of the sleep
                StaticWatchdog.reset(int(wait_time))
                # Sleep until the next task schedule
                time.sleep(self.scheduler.wait_time())

        # Now clean-up.
        BernardStatus.remove_latest_status()

        # Explicitly kill the process, because it might be running
        # as a daemon.
        log.info("Exiting. Bye bye.")
        sys.exit(0)

    def _should_restart(self):
        if time.time() - self.agent_start > self.restart_interval:
            return True
        return False

    def _do_restart(self):
        log.info("Running an auto-restart.")
        sys.exit(AgentSupervisor.RESTART_EXIT_STATUS)

class BernardStatus(AgentStatus):

    NAME = 'Bernard'

    def __init__(self, checks=[], schedule_count=0):
        AgentStatus.__init__(self)
        self.check_stats = [check.get_status() for check in checks]
        self.schedule_count = schedule_count

        self.STATUS_COLOR = {S.OK: 'green', S.TIMEOUT: 'yellow', S.EXCEPTION: 'red', S.INVALID_OUTPUT: 'red'}
        self.STATE_COLOR = {R.OK: 'green', R.WARNING: 'yellow', R.CRITICAL: 'red', R.UNKNOWN: 'yellow', R.NONE: 'white'}

    def body_lines(self):
        lines = [
            "Schedule count: %s" % self.schedule_count,
            "Check count: %s" % len(self.check_stats),
        ]

        lines += [
            "",
            "Checks",
            "======",
            ""
        ]

        for check in self.check_stats:
            status_color = self.STATUS_COLOR[check['status']]
            state_color = self.STATE_COLOR[check['state']]
            lines += ['  %s: [%s] #%d run is %s' % (check['check_name'], style(check['status'], status_color),
                                                    check['run_count'], style(check['state'], state_color))]
            lines += ['    %s' % ((check['message'] or ' ').splitlines()[0])]

        return lines

    def has_error(self):
        return False

    def to_dict(self):
        status_info = AgentStatus.to_dict(self)
        check_stats = {
            'checks': self.check_stats,
            'schedule_count': self.schedule_count,
        }
        status_info.update(check_stats)

        return status_info

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

class BernardCheck(object):
    RE_NAGIOS_PERFDATA = re.compile(r"".join([
            r"'?(?P<label>[^=']+)'?=",
            r"(?P<value>[-0-9.]+)",
            r"(?P<unit>s|us|ms|%|B|KB|MB|GB|TB|c)?",
            r"(;[^;]*;[^;]*;[^;]*;[^;]*;)?", # warn, crit, min, max
        ]))

    @classmethod
    def from_config(cls, check_config, dogstatsd, defaults):
        check_paths = []
        path = check_config.get('path', '')
        filename = check_config.get('filename', '')
        notification = check_config.get('notification', '')
        timeout = int(check_config.get('timeout', 0))
        period = int(check_config.get('period', 0))
        attempts = int(check_config.get('attempts', 0))
        name = check_config.get('name', None)
        args = check_config.get('args', [])
        notify_startup = check_config.get('notify_startup', None)
        if path:
            try:
                filenames = os.listdir(path)
                check_paths = []
                for fname in filenames:
                    # Filter hidden files
                    if not fname.startswith('.'):
                        check_path = os.path.join(path, fname)
                        # Keep only executable files
                        if os.path.isfile(check_path) and os.access(check_path, os.X_OK):
                            check_paths.append(check_path)
            except OSError, e:
                raise InvalidPath(str(e))
        if filename:
            check_paths.append(filename)

        checks = []
        if check_paths:
            check_parameter = defaults.copy()
            if notification:
                check_parameter['notification'] = notification
            if timeout:
                check_parameter['timeout'] = timeout
            if period:
                check_parameter['period'] = period
            if attempts:
                check_parameter['attempts'] = attempts
            if notify_startup:
                check_parameter['notify_startup'] = notify_startup
            if name:
                check_parameter['name'] = name
            for check_path in check_paths:
                checks.append(cls(check=check_path, config=check_parameter, dogstatsd=dogstatsd, args=args))
        return checks

    def __init__(self, check, config, dogstatsd, args=[]):
        self.check = check
        self.config = config
        self.dogstatsd = dogstatsd
        self.args = args
        self.command = [self.check] + args

        self.run_count = 0
        self.event_count = 0

        self.container_size = self.config['attempts'] + 1

        # Contains the result of #{container_size} last checks
        self.result_container = []

        # Set check_name, remove file extension and "check_" prefix
        if 'name' in config:
            check_name = config['name']
        else:
            check_name = self.check.split('/')[-1]
            if check_name.startswith('check_'):
                check_name = check_name[6:]
            check_name = check_name.rsplit('.')[0]

        self.check_name = check_name.lower()
        log.debug(u"Initialized check %s (%s)" % (self.check_name, ' '.join(self.command)))

    def __repr__(self):
        return self.check_name

    def _execute_check(self):
        timeout = self.config.get('timeout')
        output = None
        returncode = None
        # This is going to disable the StaticWatchdog
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(timeout)
        try:
            try:
                process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output = process.communicate()[0].strip()
                returncode = process.returncode
                if len(output) > 20:
                    truncated_output = output[0:17] + u'...'
                else:
                    truncated_output = output
                log.info(u"Check[%s]: %s => %s (%s)" % (
                    self.check_name,
                    u' '.join(self.command),
                    returncode,
                    truncated_output
                ))
            except Timeout:
                os.kill(process.pid, signal.SIGKILL)
        finally:
            signal.alarm(0)
            # Re enable the StaticWatchdog
            StaticWatchdog.reset()

        return output, returncode

    def timeout_handler(self, signum, frame):
        raise Timeout()

    def run(self):
        execution_date = time.time()
        try:
            output, returncode = self._execute_check()
            if output is None:
                status = S.TIMEOUT
                state = R.UNKNOWN
                message = 'Check %s timed out after %ds' % (self, self.config['timeout'])
            else:
                try:
                    state, message = self.parse_nagios(output, returncode)
                    status = S.OK
                except InvalidCheckOutput:
                    status = S.INVALID_OUTPUT
                    state = R.UNKNOWN
                    message = u'Failed to parse the output of the check: %s, returncode: %d, output: %s' % (
                        self, returncode, output)
                    log.warn(message)
        except OSError, exception:
            state = R.UNKNOWN
            status = S.EXCEPTION
            message = u'Failed to execute the check: %s' % self
            log.warn(message, exc_info=True)

        execution_time = time.time() - execution_date
        self._commit_result(status, state, message, execution_date, execution_time)

        self.run_count += 1

    def _commit_result(self, status, state, message, execution_date, execution_time):
        self.result_container.append(CheckResult(
                status=status,
                state=state,
                message=message,
                execution_date=execution_date,
                execution_time=execution_time
            ))

        if len(self.result_container) > self.container_size:
            del self.result_container[0]

    def parse_nagios(self, output, returncode):
        if returncode == 0:
            state = R.OK
        elif returncode == 1:
            state = R.WARNING
        elif returncode == 2:
            state = R.CRITICAL
        elif returncode == 3:
            state = R.UNKNOWN
        else:
            raise InvalidCheckOutput()

        output = output.strip()
        try:
            message, tail = output.split('|', 1)
        except ValueError:
            # No metric, return directly the output as a message
            return state, output

        message = message.strip()

        metrics = tail.split(' ')
        for metric in metrics:
            metric = self.RE_NAGIOS_PERFDATA.match(metric.strip())
            if metric:
                label = metric.group('label')
                value = metric.group('value')
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        log.warn("Failed to parse perfdata, check: %s, output: %s" % (self, output))
                        continue
                unit = metric.group('unit')

                dd_metric = self._metric_name(label)
                self.dogstatsd.increment('bernard.check.metric_points')

                if unit == '%':
                    value = value / 100.0
                elif unit == 'KB':
                    value = 1024 * value
                elif unit == 'MB':
                    value = 1048576 * value
                elif unit == 'GB':
                    value = 1073741824 * value
                elif unit == 'TB':
                    value = 1099511627776 * value
                elif unit == 'ms':
                    value = value / 1000.0
                elif unit == 'us':
                    value = value / 1000000.0
                elif unit == 'c':
                    self.dogstatsd.rate(dd_metric, value)
                    log.debug('Saved rate: %s:%.2f' % (dd_metric, value))
                    continue

                self.dogstatsd.gauge(dd_metric, value)
                log.debug('Saved metric: %s:%.2f' % (dd_metric, value))

        return state, message

    def _metric_name(self, label):
        return 'bernard.%s.%s' % (self.check_name, label)

    def get_last_result(self):
        return self.get_result(0)

    def get_result(self, position=0):
        if len(self.result_container) > position:
            index = - (position + 1)
            return self.result_container[index]
        elif position > self.container_size:
            raise Exception('Trying to get %dth result while container size is %d' % (position, self.container_size))
        else:
            return CheckResult(execution_date=0, status=S.OK, state=R.NONE, message='Not runned yet', execution_time=0)

    def get_status(self):
        result = self.get_last_result()

        return {
            'check_name': self.check_name,
            'run_count': self.run_count,
            'status': result.status,
            'state': result.state,
            'message': result.message,
            'execution_time': result.execution_time,
        }

class RemoteBernardCheck(BernardCheck):
    @classmethod
    def from_config(cls, remote_check, kima):
        return cls(remote_check.command, remote_check, kima)

    def __init__(self, command, remote_check, kima):
        self.command = command.split(' ')
        self.remote_check = remote_check
        self.kima = kima
        self.result_container = []
        self.container_size = 3
        self.run_count = 0
        # FIXME: get from yaml
        self.config = {
            'timeout': 10,
            'notify_startup': False,
            'attempts': 1,
            'frequency': 2
        }
        self.dogstatsd = Null()

    def __eq__(self, other):
        return self.remote_check == other.remote_check

    def __ne__(self, other):
        return not (self == other)

    def get_monitor_id(self):
        return self.remote_check.id

    def empty(self):
        return len(self.result_container) == 0

    @property
    def check_name(self):
        # This is a property to conform to the interface of the base class
        return self.remote_check.name

    def get_monitor_id(self):
        return self.remote_check.id

    def run(self):
        execution_date = time.time()
        state = None
        try:
            message, state = self._execute_check()
            if message is None:
                status = S.TIMEOUT
                message = 'Check %s timed out after %ds' % (self, self.config['timeout'])
            else:
                status = S.OK
        except OSError:
            status = S.EXCEPTION
            message = u'Failed to execute the check: %s' % self
            log.warn(message, exc_info=True)

        execution_time = time.time() - execution_date
        self._commit_result(status, state, message, execution_date, execution_time)

        self.run_count += 1

    def post_run(self, result):
        # fixme: use the same value as the agent
        host_name = 'ccabanilla-imac'
        return self.kima.post_monitor_run(self.remote_check,
                # Impedence mismatch: bernard calls states what the server
                # knows as statuses. Should reconcile.
                status=result.state,
                output=result.message,
                timestamp=result.execution_date,
                host_name=host_name)

class Null(object):
    def __init__(self):
        pass

    def nothing(self, *args, **kwargs):
        pass

    def __getattr__(self, key):
        return self.nothing

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

def main():
    """" Execution of Bernard"""
    options, args = get_parsed_args()
    agentConfig = get_config(options=options)
    autorestart = agentConfig.get('autorestart', False)

    COMMANDS = [
        'start',
        'stop',
        'restart',
        'foreground',
        'status',
        'info',
    ]

    if len(args) < 1:
        sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], "|".join(COMMANDS)))
        return 2

    command = args[0]
    if command not in COMMANDS:
        sys.stderr.write("Unknown command: %s\n" % command)
        return 3

    pid_file = PidFile('bernard')

    if options.clean:
        pid_file.clean()

    bernard = Bernard(pid_file.get_path(), autorestart)

    if 'start' == command:
        log.info('Start daemon')
        bernard.start()

    elif 'stop' == command:
        log.info('Stop daemon')
        bernard.stop()

    elif 'restart' == command:
        log.info('Restart daemon')
        bernard.restart()

    elif 'status' == command:
        bernard.status()

    elif 'info' == command:
        bernard.info(verbose=options.verbose)

    elif 'foreground' == command:
        logging.info('Running in foreground')
        if autorestart:
            # Set-up the supervisor callbacks and fork it.
            logging.info('Running Bernard with auto-restart ON')
            def child_func(): bernard.run()
            def parent_func(): bernard.start_event = False
            AgentSupervisor.start(parent_func, child_func)
        else:
            # Run in the standard foreground.
            bernard.run()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except StandardError:
        # Try our best to log the error.
        try:
            log.exception("Uncaught error running the agent")
        except:
            pass
        raise

