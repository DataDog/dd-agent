from collections import namedtuple
import socket

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

    @mock.patch('network.Platform.is_linux', return_value=False)
    @mock.patch('network.Platform.is_bsd', return_value=False)
    @mock.patch('network.Platform.is_solaris', return_value=False)
    @mock.patch('network.Platform.is_windows', return_value=True)
    def test_win_uses_psutil(self, *args):
        self.check._check_psutil = mock.MagicMock()
        self.run_check({})
        self.check._check_psutil.assert_called_once_with()

    @mock.patch('network.Network._cx_state_psutil')
    @mock.patch('network.Network._cx_counters_psutil')
    def test_check_psutil(self, state, counters):
        self.check._cx_state_psutil = state
        self.check._cx_counters_psutil = counters

        self.check._collect_cx_state = False
        self.check._check_psutil()
        state.assert_not_called()
        counters.assert_called_once_with()

        state.reset_mock()
        counters.reset_mock()

        self.check._collect_cx_state = True
        self.check._check_psutil()
        state.assert_called_once_with()
        counters.assert_called_once_with()

    def test_cx_state_psutil(self):
        sconn = namedtuple('sconn', ['fd', 'family', 'type', 'laddr', 'raddr', 'status', 'pid'])
        conn = [
            sconn(fd=-1, family=socket.AF_INET, type=socket.SOCK_STREAM, laddr=('127.0.0.1', 50482), raddr=('127.0.0.1',2638), status='ESTABLISHED', pid=1416),
            sconn(fd=-1, family=socket.AF_INET6, type=socket.SOCK_STREAM, laddr=('::', 50482), raddr=('::',2638), status='ESTABLISHED', pid=42),
            sconn(fd=-1, family=socket.AF_INET6, type=socket.SOCK_STREAM, laddr=('::', 49163), raddr=(), status='LISTEN', pid=1416),
            sconn(fd=-1, family=socket.AF_INET, type=socket.SOCK_STREAM, laddr=('0.0.0.0', 445), raddr=(), status='LISTEN', pid=4),
            sconn(fd=-1, family=socket.AF_INET6, type=socket.SOCK_STREAM, laddr=('::1', 56521), raddr=('::1', 17123), status='TIME_WAIT', pid=0),
            sconn(fd=-1, family=socket.AF_INET6, type=socket.SOCK_DGRAM, laddr=('::', 500), raddr=(), status='NONE', pid=892),
            sconn(fd=-1, family=socket.AF_INET6, type=socket.SOCK_STREAM, laddr=('::1', 56493), raddr=('::1', 17123), status='TIME_WAIT', pid=0),
            sconn(fd=-1, family=socket.AF_INET, type=socket.SOCK_STREAM, laddr=('127.0.0.1', 54541), raddr=('127.0.0.1', 54542), status='ESTABLISHED', pid=20500),
        ]

        results = {
            'system.net.tcp6.time_wait': 2,
            'system.net.tcp4.listening': 1,
            'system.net.tcp6.closing': 0,
            'system.net.tcp4.closing': 0,
            'system.net.tcp4.time_wait': 0,
            'system.net.tcp6.established': 1,
            'system.net.tcp4.established': 2,
            'system.net.tcp6.listening': 1,
            'system.net.tcp4.opening': 0,
            'system.net.udp4.connections': 0,
            'system.net.udp6.connections': 1,
            'system.net.tcp6.opening': 0,
        }

        with mock.patch('network.psutil') as mock_psutil:
            mock_psutil.net_connections.return_value = conn
            self.check._cx_state_psutil()
            for _, m in self.check.aggregator.metrics.iteritems():
                self.assertEqual(results[m.name], m.value)

    def test_cx_counters_psutil(self):
        snetio = namedtuple('snetio', ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv', 'errin', 'errout', 'dropin', 'dropout'])
        counters = {
            'Ethernet': snetio(bytes_sent=3096403230L, bytes_recv=3280598526L, packets_sent=6777924, packets_recv=32888147, errin=0, errout=0, dropin=0, dropout=0),
            'Loopback Pseudo-Interface 1': snetio(bytes_sent=0, bytes_recv=0, packets_sent=0, packets_recv=0, errin=0, errout=0, dropin=0, dropout=0),
        }
        with mock.patch('network.psutil') as mock_psutil:
            mock_psutil.net_io_counters.return_value = counters
            self.check._excluded_ifaces = ['Loopback Pseudo-Interface 1']
            self.check._exclude_iface_re = ''
            self.check._cx_counters_psutil()
            for _, m in self.check.aggregator.metrics.iteritems():
                self.assertEqual(m.device_name, 'Ethernet')
                if 'bytes_rcvd' in m.name:  # test just one of the metrics
                    self.assertEqual(m.samples[0][1], 3280598526)

    def test_parse_protocol_psutil(self):
        import socket
        conn = mock.MagicMock()

        protocol = self.check._parse_protocol_psutil(conn)
        self.assertEqual(protocol, '')

        conn.type = socket.SOCK_STREAM
        conn.family = socket.AF_INET6
        protocol = self.check._parse_protocol_psutil(conn)
        self.assertEqual(protocol, 'tcp6')

        conn.type = socket.SOCK_DGRAM
        conn.family = socket.AF_INET
        protocol = self.check._parse_protocol_psutil(conn)
        self.assertEqual(protocol, 'udp4')
