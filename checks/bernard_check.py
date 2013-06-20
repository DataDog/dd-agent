import time
import os
import signal
import subprocess
from util import namedtuple
import logging
import re
from config import initialize_logging; initialize_logging('bernard')
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

class BernardCheck(object):
    RE_NAGIOS_PERFDATA = re.compile(r"".join([
            r"'?(?P<label>[^=']+)'?=",
            r"(?P<value>[-0-9.]+)",
            r"(?P<unit>s|us|ms|%|B|KB|MB|GB|TB|c)?",
            r"(;[^;]*;[^;]*;[^;]*;[^;]*;)?", # warn, crit, min, max
        ]))
    CONTAINER_SIZE = 5

    def __init__(self, check, config, dogstatsd):
        self.check = check
        self.config = config
        self.dogstatsd = dogstatsd

        self.run_count = 0
        self.event_count = 0

        # Contains the result of #{CONTAINER_SIZE} last checks
        self.result_container = []

        # Set check_name
        check_name = self.check.split('/')[-1]
        if check_name.startswith('check_'):
            check_name = check_name[6:]
        check_name = check_name.rsplit('.')[0]

        self.check_name = check_name.lower()

    def __repr__(self):
        return self.check_name

    def _execute_check(self):
        timeout = self.config.get('timeout')
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(timeout)
        try:
            process = subprocess.Popen(self.check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = process.communicate()[0]
            signal.alarm(0)
            return output, process.returncode
        except Timeout:
            os.kill(process.pid, signal.SIGKILL)
            return None, None

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
                    status = S.EXCEPTION
                    state = R.UNKNOWN
                    message = u'Failed to parse the output of the check: %s, output: %s' % (self, output)
                    log.warn(message)
        except OSError, exception:
            state = R.UNKNOWN
            status = S.EXCEPTION
            message = u'Failed to execute the check: %s, exception: %s' % (self, exception)
            log.warn(message)

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

        if len(self.result_container) > self.CONTAINER_SIZE:
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

                if unit == 'c':
                    # We should do a rate but dogstated_client can't so we drop this metric
                    continue
                elif unit == '%':
                    value = value / 100
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

                dd_metric = self._metric_name(label)

                self.dogstatsd.gauge(dd_metric, value)
                log.debug('%s:%.2f' % (dd_metric, value))


        return state, message

    def _metric_name(self, label):
        return 'nagios.%s.%s' % (self.check_name, label)

    def get_last_result(self):
        return self.get_result(0)

    def get_result(self, position=0):
        if len(self.result_container) > position:
            index = - (position + 1)
            return self.result_container[index]
        elif position > self.CONTAINER_SIZE:
            raise Exception('Trying to get %dth result while container size is %d' % (position, self.CONTAINER_SIZE))
        else:
            return CheckResult(execution_date=0, status=S.OK, state=R.NONE, message='Not runned yet', execution_time=0)

    def get_status(self):
        result = self.get_last_result()
        state = result.state
        status = result.state
        message = result.message

        return {
            'check_name': self.check_name,
            'run_count': self.run_count,
            'status': status,
            'state': state,
            'message': message,
        }
