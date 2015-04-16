import mock
import psutil

from tests.common import AgentCheckTest

B2MB  = float(1048576)

class _PSUtilSwapStatsMock(object):
    def __init__(self, sin, sout):
        self.sin = sin
        self.sout = sout

MOCK_PSUTIL_SWAP_STATS = [
    _PSUtilSwapStatsMock(115332743168, 22920884224),
    _PSUtilSwapStatsMock(115332743170, 22920884230),
]

class SystemSwapTestCase(AgentCheckTest):

    CHECK_NAME = 'system_swap'

    @mock.patch('psutil.swap_memory', side_effect=MOCK_PSUTIL_SWAP_STATS)
    def test_system_swap(self, mock_swap_stats):
        self.run_check({"instances": [{}]})
        self.assertMetric('system.swap.swapped_in', 115332743168 / B2MB)
        self.assertMetric('system.swap.swapped_out', 22920884224 / B2MB)

        self.run_check({"instances": [{}]})
        self.assertMetric('system.swap.swapped_in', 115332743170 / B2MB)
        self.assertMetric('system.swap.swapped_out', 22920884230 / B2MB)
