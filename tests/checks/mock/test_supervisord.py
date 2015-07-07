# stdlib
from socket import socket
import unittest
import xmlrpclib

# 3p
from mock import patch

# project
from checks import AgentCheck
from tests.checks.common import get_check


class TestSupervisordCheck(unittest.TestCase):

    TEST_CASES = [{
        'yaml':  """
init_config:
instances:
    - name: server1
      host: localhost
      port: 9001""",
        'expected_instances': [{
            'host': 'localhost',
            'name': 'server1',
            'port': 9001
        }],
        'expected_metrics': {
            'server1': [
                ('supervisord.process.count', 1, {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:up']}),
                ('supervisord.process.count', 1, {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:down']}),
                ('supervisord.process.count', 1, {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:unknown']}),
                ('supervisord.process.uptime', 0, {'type': 'gauge', 'tags': ['supervisord_server:server1', 'supervisord_process:python']}),
                ('supervisord.process.uptime', 125, {'type': 'gauge', 'tags': ['supervisord_server:server1', 'supervisord_process:mysql']}),
                ('supervisord.process.uptime', 0, {'type': 'gauge', 'tags': ['supervisord_server:server1', 'supervisord_process:java']})
            ]
        },
        'expected_service_checks': {
            'server1': [{
                'status': AgentCheck.OK,
                'tags': ['supervisord_server:server1'],
                'check': 'supervisord.can_connect',
            }, {
                'status': AgentCheck.OK,
                'tags': ['supervisord_server:server1', 'supervisord_process:mysql'],
                'check': 'supervisord.process.status'
            }, {
                'status': AgentCheck.CRITICAL,
                'tags': ['supervisord_server:server1', 'supervisord_process:java'],
                'check': 'supervisord.process.status'
            }, {
                'status': AgentCheck.UNKNOWN,
                'tags': ['supervisord_server:server1', 'supervisord_process:python'],
                'check': 'supervisord.process.status'
            }]
        }
    }, {
        'yaml': """
init_config:

instances:
  - name: server0
    host: localhost
    port: 9001
    user: user
    pass: pass
    proc_names:
      - apache2
      - webapp
  - name: server1
    host: 10.60.130.82""",
        'expected_instances': [{
            'name': 'server0',
            'host': 'localhost',
            'port': 9001,
            'user': 'user',
            'pass': 'pass',
            'proc_names': ['apache2', 'webapp'],
        }, {
            'host': '10.60.130.82',
            'name': 'server1'
        }],
        'expected_metrics': {
            'server0': [
                ('supervisord.process.count', 0, {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:up']}),
                ('supervisord.process.count', 2, {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:down']}),
                ('supervisord.process.count', 0, {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:unknown']}),
                ('supervisord.process.uptime', 0, {'type': 'gauge', 'tags': ['supervisord_server:server0', 'supervisord_process:apache2']}),
                ('supervisord.process.uptime', 2, {'type': 'gauge', 'tags': ['supervisord_server:server0', 'supervisord_process:webapp']}),
            ],
            'server1': [
                ('supervisord.process.count', 0, {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:up']}),
                ('supervisord.process.count', 1, {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:down']}),
                ('supervisord.process.count', 0, {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:unknown']}),
                ('supervisord.process.uptime', 0, {'type': 'gauge', 'tags': ['supervisord_server:server1', 'supervisord_process:ruby']})
            ]
        },
        'expected_service_checks': {
            'server0': [{
                'status': AgentCheck.OK,
                'tags': ['supervisord_server:server0'],
                'check': 'supervisord.can_connect',
            }, {
                'status': AgentCheck.CRITICAL,
                'tags': ['supervisord_server:server0', 'supervisord_process:apache2'],
                'check': 'supervisord.process.status'
            }, {
                'status': AgentCheck.CRITICAL,
                'tags': ['supervisord_server:server0', 'supervisord_process:webapp'],
                'check': 'supervisord.process.status'
            }],
            'server1': [{
                'status': AgentCheck.OK,
                'tags': ['supervisord_server:server1'],
                'check': 'supervisord.can_connect',
            }, {
                'status': AgentCheck.CRITICAL,
                'tags': ['supervisord_server:server1', 'supervisord_process:ruby'],
                'check': 'supervisord.process.status'
            }]
        }
    }, {
        'yaml': """
init_config:

instances:
  - name: server0
    host: invalid_host
    port: 9009""",
        'expected_instances': [{
            'name': 'server0',
            'host': 'invalid_host',
            'port': 9009
        }],
        'error_message': """Cannot connect to http://invalid_host:9009. Make sure that supervisor is running and XML-RPC inet interface is enabled."""
    }, {
        'yaml': """
init_config:

instances:
  - name: server0
    host: localhost
    port: 9010
    user: invalid_user
    pass: invalid_pass""",
        'expected_instances': [{
            'name': 'server0',
            'host': 'localhost',
            'port': 9010,
            'user': 'invalid_user',
            'pass': 'invalid_pass'
        }],
        'error_message': """Username or password to server0 are incorrect."""
    }, {
        'yaml': """
init_config:

instances:
  - name: server0
    host: localhost
    port: 9001
    proc_names:
      - mysql
      - invalid_process""",
        'expected_instances': [{
            'name': 'server0',
            'host': 'localhost',
            'port': 9001,
            'proc_names': ['mysql', 'invalid_process']
        }],
        'expected_metrics': {
            'server0': [
                ('supervisord.process.count', 1, {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:up']}),
                ('supervisord.process.count', 0, {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:down']}),
                ('supervisord.process.count', 0, {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:unknown']}),
                ('supervisord.process.uptime', 125, {'type': 'gauge', 'tags': ['supervisord_server:server0', 'supervisord_process:mysql']})
            ]
        },
        'expected_service_checks': {
            'server0': [{
                'status': AgentCheck.OK,
                'tags': ['supervisord_server:server0'],
                'check': 'supervisord.can_connect',
            }, {
                'status': AgentCheck.OK,
                'tags': ['supervisord_server:server0', 'supervisord_process:mysql'],
                'check': 'supervisord.process.status'
            }]
        }
    }]

    def setUp(self):
        self.patcher = patch('xmlrpclib.Server', self.mock_server)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    # Integration Test #####################################################

    def test_check(self):
        """Integration test for supervisord check. Using a mocked supervisord."""
        for tc in self.TEST_CASES:
            check, instances = get_check('supervisord', tc['yaml'])
            self.assertTrue(check is not None, msg=check)
            self.assertEquals(tc['expected_instances'], instances)
            for instance in instances:
                name = instance['name']

                try:
                    # Run the check
                    check.check(instance)
                except Exception, e:
                    if 'error_message' in tc:  # excepted error
                        self.assertEquals(str(e), tc['error_message'])
                    else:
                        self.assertTrue(False, msg=str(e))
                else:
                    # Assert that the check collected the right metrics
                    expected_metrics = tc['expected_metrics'][name]
                    self.assert_metrics(expected_metrics, check.get_metrics())

                    # Assert that the check generated the right service checks
                    expected_service_checks = tc['expected_service_checks'][name]
                    self.assert_service_checks(expected_service_checks,
                                               check.get_service_checks())

    # Unit Tests ###########################################################

    def test_build_message(self):
        """Unit test supervisord build service check message."""
        process = {
            'now': 1414815513,
            'group': 'mysql',
            'description': 'pid 787, uptime 0:02:05',
            'pid': 787,
            'stderr_logfile': '/var/log/supervisor/mysql-stderr---supervisor-3ATI82.log',
            'stop': 0,
            'statename': 'RUNNING',
            'start': 1414815388,
            'state': 20,
            'stdout_logfile': '/var/log/mysql/mysql.log',
            'logfile': '/var/log/mysql/mysql.log',
            'exitstatus': 0,
            'spawnerr': '',
            'name': 'mysql'
        }

        expected_message = """Current time: 2014-11-01 04:18:33
Process name: mysql
Process group: mysql
Description: pid 787, uptime 0:02:05
Error log file: /var/log/supervisor/mysql-stderr---supervisor-3ATI82.log
Stdout log file: /var/log/mysql/mysql.log
Log file: /var/log/mysql/mysql.log
State: RUNNING
Start time: 2014-11-01 04:16:28
Stop time: \nExit Status: 0"""

        check, _ = get_check('supervisord', self.TEST_CASES[0]['yaml'])
        self.assertEquals(expected_message, check._build_message(process))

    # Helper Methods #######################################################

    @staticmethod
    def mock_server(url):
        return MockXmlRcpServer(url)

    def assert_metrics(self, expected, actual):
        actual = [TestSupervisordCheck.norm_metric(metric) for metric in actual]
        self.assertEquals(len(actual), len(expected), msg='Invalid # metrics reported.\n'
            'Expected: {0}. Found: {1}'.format(len(expected), len(actual)))
        self.assertTrue(all([expected_metric in actual for expected_metric in expected]),
            msg='Reported metrics are incorrect.\nExpected: {0}.\n'
                'Found: {1}'.format(expected, actual))

    def assert_service_checks(self, expected, actual):
        actual = [TestSupervisordCheck.norm_service_check(service_check)
                  for service_check in actual]
        self.assertEquals(len(actual), len(expected), msg='Invalid # service checks reported.'
            '\nExpected: {0}. Found: {1}.'.format(expected, actual))
        self.assertTrue(all([expected_service_check in actual
                 for expected_service_check in expected]),
            msg='Reported service checks are incorrect.\nExpected:{0}\n'
                'Found:{1}'.format(expected, actual))

    @staticmethod
    def norm_metric(metric):
        '''Removes hostname and timestamp'''
        metric[3].pop('hostname')
        return (metric[0], metric[2], metric[3])

    @staticmethod
    def norm_service_check(service_check):
        '''Removes timestamp, host_name, message and id'''
        for field in ['timestamp', 'host_name', 'message', 'id']:
            service_check.pop(field)
        return service_check


class MockXmlRcpServer:
    """Class that mocks an XML RPC server. Initialized using a mocked
     supervisord server url, which is used to initialize the supervisord
     server.
     """
    def __init__(self, url):
        self.supervisor = MockSupervisor(url)


class MockSupervisor:
    """Class that mocks a supervisord sever. Initialized using the server url
    and mocks process methods providing mocked process information for testing
    purposes.
    """
    MOCK_PROCESSES = {
        'http://localhost:9001/RPC2': [{
            'now': 1414815513,
            'group': 'mysql',
            'description': 'pid 787, uptime 0:02:05',
            'pid': 787,
            'stderr_logfile': '/var/log/supervisor/mysql-stderr---supervisor-3ATI82.log',
            'stop': 0,
            'statename': 'RUNNING',
            'start': 1414815388,
            'state': 20,
            'stdout_logfile': '/var/log/mysql/mysql.log',
            'logfile': '/var/log/mysql/mysql.log',
            'exitstatus': 0,
            'spawnerr': '',
            'name': 'mysql'
        }, {
            'now': 1414815738,
            'group': 'java',
            'description': 'Nov 01 04:22 AM',
            'pid': 0,
            'stderr_logfile': '/var/log/supervisor/java-stderr---supervisor-lSdcKZ.log',
            'stop': 1414815722,
            'statename': 'STOPPED',
            'start': 1414815388,
            'state': 0,
            'stdout_logfile': '/var/log/java/java.log',
            'logfile': '/var/log/java/java.log',
            'exitstatus': 21,
            'spawnerr': '',
            'name': 'java'
        }, {
            'now': 1414815738,
            'group': 'python',
            'description': '',
            'pid': 2765,
            'stderr_logfile': '/var/log/supervisor/python-stderr---supervisor-vFzxIg.log',
            'stop': 1414815737,
            'statename': 'STARTING',
            'start': 1414815737,
            'state': 10,
            'stdout_logfile': '/var/log/python/python.log',
            'logfile': '/var/log/python/python.log',
            'exitstatus': 0,
            'spawnerr': '',
            'name': 'python'
        }],
        'http://user:pass@localhost:9001/RPC2': [{
            'now': 1414869824,
            'group': 'apache2',
            'description': 'Exited too quickly (process log may have details)',
            'pid': 0,
            'stderr_logfile': '/var/log/supervisor/apache2-stderr---supervisor-0PkXWd.log',
            'stop': 1414867047,
            'statename': 'FATAL',
            'start': 1414867047,
            'state': 200,
            'stdout_logfile': '/var/log/apache2/apache2.log',
            'logfile': '/var/log/apache2/apache2.log',
            'exitstatus': 0,
            'spawnerr': 'Exited too quickly (process log may have details)',
            'name': 'apache2'
        }, {
            'now': 1414871104,
            'group': 'webapp',
            'description': '',
            'pid': 17600,
            'stderr_logfile': '/var/log/supervisor/webapp-stderr---supervisor-onZK__.log',
            'stop': 1414871101,
            'statename': 'STOPPING',
            'start': 1414871102,
            'state': 40,
            'stdout_logfile': '/var/log/company/webapp.log',
            'logfile': '/var/log/company/webapp.log',
            'exitstatus': 1,
            'spawnerr': '',
            'name': 'webapp'
        }],
        'http://10.60.130.82:9001/RPC2': [{
            'now': 1414871588,
            'group': 'ruby',
            'description': 'Exited too quickly (process log may have details)',
            'pid': 0,
            'stderr_logfile': '/var/log/supervisor/ruby-stderr---supervisor-BU7Wat.log',
            'stop': 1414871588,
            'statename': 'BACKOFF',
            'start': 1414871588,
            'state': 30,
            'stdout_logfile': '/var/log/ruby/ruby.log',
            'logfile': '/var/log/ruby/ruby.log',
            'exitstatus': 0,
            'spawnerr': 'Exited too quickly (process log may have details)',
            'name': 'ruby'
        }]
    }

    def __init__(self, url):
        self.url = url

    def getAllProcessInfo(self):
        self._validate_request()
        return self.MOCK_PROCESSES[self.url]

    def getProcessInfo(self, proc_name):
        self._validate_request(proc=proc_name)
        for proc in self.MOCK_PROCESSES[self.url]:
            if proc['name'] == proc_name:
                return proc
        raise Exception('Process not found: %s' % proc_name)

    def _validate_request(self, proc=None):
        '''Validates request and simulates errors when not valid'''
        if 'invalid_host' in self.url:
            # Simulate connecting to an invalid host/port in order to
            # raise `socket.error: [Errno 111] Connection refused`
            socket().connect(('localhost', 38837))
        elif 'invalid_pass' in self.url:
            # Simulate xmlrpc exception for invalid credentials
            raise xmlrpclib.ProtocolError(self.url[7:], 401,
                                          'Unauthorized', None)
        elif proc is not None and 'invalid' in proc:
            # Simulate xmlrpc exception for process not found
            raise xmlrpclib.Fault(10, 'BAD_NAME')
