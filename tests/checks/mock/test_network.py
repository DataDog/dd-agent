# 3p
import mock

# project
from tests.checks.common import AgentCheckTest, Fixtures


def ss_subprocess_mock(*args, **kwargs):
    if args[0][-1] == '-4':
        return (Fixtures.read_file('ss_ipv4'), "", 0)
    elif args[0][-1] == '-6':
        return (Fixtures.read_file('ss_ipv6'), "", 0)


def netstat_subprocess_mock(*args, **kwargs):
    if args[0][0] == 'ss':
        raise OSError
    elif args[0][0] == 'netstat':
        return (Fixtures.read_file('netstat'), "", 0)


class TestCheckNetwork(AgentCheckTest):
    CHECK_NAME = 'network'

    def setUp(self):
        self.config = {
            "instances": [
                {
                    "collect_connection_state": True
                }
            ]
        }
        self.load_check(self.config)

    CX_STATE_GAUGES_VALUES = {
        'system.net.udp4.connections': 2,
        'system.net.udp6.connections': 3,
        'system.net.tcp4.established': 1,
        'system.net.tcp4.opening': 0,
        'system.net.tcp4.closing': 0,
        'system.net.tcp4.listening': 2,
        'system.net.tcp4.time_wait': 2,
        'system.net.tcp6.established': 1,
        'system.net.tcp6.opening': 0,
        'system.net.tcp6.closing': 1,
        'system.net.tcp6.listening': 1,
        'system.net.tcp6.time_wait': 1,
    }

    @mock.patch('network.get_subprocess_output', side_effect=ss_subprocess_mock)
    @mock.patch('network.Platform.is_linux', return_value=True)
    def test_cx_state_linux_ss(self, mock_subprocess, mock_platform):
        self.run_check({})

        # Assert metrics
        for metric, value in self.CX_STATE_GAUGES_VALUES.iteritems():
            self.assertMetric(metric, value=value)

    @mock.patch('network.get_subprocess_output', side_effect=netstat_subprocess_mock)
    @mock.patch('network.Platform.is_linux', return_value=True)
    def test_cx_state_linux_netstat(self, mock_subprocess, mock_platform):
        self.run_check({})

        # Assert metrics
        for metric, value in self.CX_STATE_GAUGES_VALUES.iteritems():
            self.assertMetric(metric, value=value)
