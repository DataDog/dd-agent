# stdlib
import logging
import os
import re
import signal
import shlex
import subprocess
import time

# project
from util import (
    get_hostname,
    namedtuple,
    StaticWatchdog,
)

class Timeout(Exception):
    pass

class InvalidPath(Exception):
    pass

# Represent the result of the execution of one check
CheckResult = namedtuple('CheckResult',
    ['status', 'state', 'message', 'execution_date', 'execution_time'])

# State of the last execution of the check
ExecutionState = namedtuple('ExecutionState',
    ['OK', 'TIMEOUT', 'EXCEPTION', 'INVALID_OUTPUT'])
S = ExecutionState('ok', 'timeout', 'exception', 'invalid_output')

# Check result status
class R():
    OK, WARNING, CRITICAL, UNKNOWN, NONE = (0, 1, 2, 3, 4)
    ALL = (OK, WARNING, CRITICAL, UNKNOWN, NONE)

log = logging.getLogger(__name__)

class BernardCheck(object):
    RE_NAGIOS_PERFDATA = re.compile(r"".join([
            r"'?(?P<label>[^=']+)'?=",
            r"(?P<value>[-0-9.]+)",
            r"(?P<unit>s|us|ms|%|B|KB|MB|GB|TB|c)?",
            r"(;[^;]*;[^;]*;[^;]*;[^;]*;)?", # warn, crit, min, max
        ]))

    @classmethod
    def from_config(cls, name, check_config, defaults, hostname=None):
        options = check_config.get('options', {})
        timeout = int(options.get('timeout', 0))
        period = int(options.get('period', 0))
        raw_command = check_config.get('command')
        params_list = check_config.get('params') or [{}]
        hostname = hostname or get_hostname()

        check_config = {
            'timeout': timeout or defaults['timeout'],
            'period': period or defaults['period'],
        }
        checks = []

        # For every set of params (e.g.: {'port': 8888}) return a single check.
        # We'll template the $variables in the `command` value with the params.
        for param_dict in params_list:
            command = _subprocess_command(raw_command, param_dict, hostname)
            checks.append(cls(name, command, check_config))

        return checks

    def __init__(self, name, command, config):
        """ Initializes a BernardCheck with the given `name` and `command`.
            Any additional config (e.g. timeout or period) are given in the
            `config` dict. `command` is expected to be in a subprocess-friendly
            form, e.g.: ['check_foo', ['-h', 'localhost']].
        """
        self.name = name
        self.config = config
        self.command = command
        self.run_count = 0
        self.event_count = 0

        # Always holds the latest result.
        self.result = None

        log.debug(u"Initialized check %s (%s)" % (self.name, command))

    def __repr__(self):
        return self.name

    def get_period(self):
        return self.config['period']

    def _execute_check(self):
        timeout = self.config.get('timeout')
        output = None
        returncode = None

        # This is going to disable the StaticWatchdog
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(timeout)
        try:
            try:
                process = subprocess.Popen(self.command,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                output = process.communicate()[0].strip()
                returncode = process.returncode
                if len(output) > 20:
                    truncated_output = output[0:17] + u'...'
                else:
                    truncated_output = output
                log.info(u"Check[%s]: %s => %s (%s)" % (
                    self.name,
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

    def run(self, dogstatsd_client):
        execution_date = time.time()
        try:
            output, returncode = self._execute_check()

            if output is None:
                state = S.TIMEOUT
                status = R.UNKNOWN
                message = 'Check %s timed out after %ds' % (self, self.config['timeout'])
            else:
                if returncode not in R.ALL:
                    state = S.INVALID_OUTPUT
                    status = R.UNKNOWN
                    message = u'Failed to parse the output of the check: %s, ' \
                               'returncode: %d, output: %s' \
                                    % (self, returncode, output)
                    log.warn(message)
                else:
                    message = self.parse_nagios(output, dogstatsd_client)
                    state = S.OK
                    status = returncode
        except OSError:
            status = R.UNKNOWN
            state = S.EXCEPTION
            message = u'Failed to execute the check: %s' % self
            log.warn(message, exc_info=True)

        execution_time = time.time() - execution_date
        self.run_count += 1

        check_result = CheckResult(
            status=status,
            state=state,
            message=message,
            execution_date=execution_date,
            execution_time=execution_time
        )
        self.result = check_result
        return check_result

    def parse_nagios(self, output, dogstatsd_client):
        output = output.strip()
        try:
            message, tail = output.split('|', 1)
        except ValueError:
            # No metric, return directly the output as a message
            return output

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
                dogstatsd_client.increment('bernard.check.metric_points')

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
                    dogstatsd_client.rate(dd_metric, value)
                    log.debug('Saved rate: %s:%.2f' % (dd_metric, value))
                    continue

                dogstatsd_client.gauge(dd_metric, value)
                log.debug('Saved metric: %s:%.2f' % (dd_metric, value))

        return message

    def _metric_name(self, label):
        return 'bernard.%s.%s' % (self.name, label)

    def get_result(self):
        if self.result:
            return self.result
        return CheckResult(execution_date=0, state=S.OK, status=R.NONE,
                           message='Not yet run.', execution_time=0)

    def get_status(self):
        result = self.get_result()

        return {
            'check_name': self.name,
            'run_count': self.run_count,
            'status': result.status,
            'state': result.state,
            'message': result.message,
            'execution_time': result.execution_time,
        }


def _subprocess_command(raw_command, params, hostname):
    """ Given a raw command from the Bernard config and a dictionary of check
        parameter, return a list that's subprocess-compatible for running the
        command. We'll replace all command "variables" with a real parameter.

    >>> _subprocess_command("/usr/bin/check_pg -p $port", {'port': '5433'})
    ['/usr/bin/check_pg', ['-p', '5433']]
    """
    # $host is always available as a parameter.
    if 'host' not in params:
        params['host'] = hostname

    # Replace variables.
    for param, val in params.iteritems():
        raw_command = raw_command.replace('$%s' % param, str(val))

    # Split into subprocess format.
    command_split = raw_command.split()
    if len(command_split) == 0:
        raise Exception('Invalid command in config: %v' % raw_command)
    parsed_command = [command_split[0]]
    if len(command_split[1:]):
        parsed_command.extend(shlex.split(' '.join(command_split[1:])))
    return parsed_command
