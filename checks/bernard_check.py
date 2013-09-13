import time
import os
import signal
import subprocess
from util import namedtuple
import logging
import re

from util import StaticWatchdog
log = logging.getLogger('bernard')

# Status of the execution of the check
ExecutionStatus = namedtuple('ExecutionStatus',
    ['OK', 'TIMEOUT', 'EXCEPTION', 'INVALID_OUTPUT'])
S = ExecutionStatus('ok', 'timeout', 'exception', 'invalid_output')

# State of check
ResultState = namedtuple('ResultState',
    ['NONE', 'OK', 'WARNING', 'CRITICAL', 'UNKNOWN'])
R = ResultState('init', 'ok', 'warning', 'critical', 'unknown')

# Represent the result of the execution of one check
CheckResult = namedtuple('CheckResult',
    ['status', 'state', 'message', 'execution_date', 'execution_time'])

class InvalidCheckOutput(Exception):
    pass

class Timeout(Exception):
    pass

class InvalidPath(Exception):
    pass

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
        return cls(remote_check.name, remote_check.command, remote_check,
                   kima)

    def __init__(self, name, command, remote_check, kima):
        self.check_name = name
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

    def post_run(self, result):
        return self.kima.post_check_run(self.remote_check,
                status=R.index(result.status),
                output=result.message,
                timestamp=result.execution_date)

class Null(object):
    def __init__(self):
        pass

    def nothing(self, *args, **kwargs):
        pass

    def __getattr__(self, key):
        return self.nothing
