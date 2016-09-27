# stdlib
import mock

# project
from tests.checks.common import AgentCheckTest, Fixtures
from checks import AgentCheck
from utils import network


MOCK_CONFIG = {
    'init_config': {},
    'instances' : [{}]}


def mock_read_lines(path):
    files = {
        '/proc/net/netstat': 'netstat',
        '/proc/net/snmp': 'snmp',
        '/proc/net/udp': 'udp',
        '/proc/net/udp6': 'udp6'}
    return Fixtures.read_file(files[path]).splitlines()

class TestNetworkExt(AgentCheckTest):
    CHECK_NAME = 'network_ext'

    @mock.patch('utils.network.read_lines', side_effect=mock_read_lines)
    def test_success(self, mock_read_lines):
        self.run_check_twice(MOCK_CONFIG)
        self.assertMetric("system.net.tcpx.rto_algorithm", value=1)
        self.assertMetric("system.net.tcpx.sack_discard", value=0)
        self.assertMetric("system.net.tcpx.backlog_drop", value=0)
        self.assertMetric("system.net.udpx.drops", value=0, count=1, tags=["inode:29167010"])
        self.assertMetric("system.net.udpx6.drops", value=0, count=1, tags=["inode:2383"])
