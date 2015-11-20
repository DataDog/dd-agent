import mock

from tests.checks.common import AgentCheckTest

class _PSUtilSwapStatsMock(object):
    def __init__(self, sin, sout):
        self.sin = sin
        self.sout = sout

ORIG_SWAP_IN = 115332743168
ORIG_SWAP_OUT = 22920884224

SWAP_IN_INCR = 2
SWAP_OUT_INCR = 4

MOCK_PSUTIL_SWAP_STATS = [
    _PSUtilSwapStatsMock(ORIG_SWAP_IN, ORIG_SWAP_OUT),
    _PSUtilSwapStatsMock(ORIG_SWAP_IN + SWAP_IN_INCR, ORIG_SWAP_OUT + SWAP_OUT_INCR),
]

class SystemSwapTestCase(AgentCheckTest):

    CHECK_NAME = 'system_swap'

    @mock.patch('psutil.swap_memory', side_effect=MOCK_PSUTIL_SWAP_STATS)
    def test_system_swap(self, mock_swap_stats):
        self.run_check_twice({"instances": [{}]}) # Run check twice, sleeping for 1 sec in between
        self.assertMetric('system.swap.swapped_in', value=SWAP_IN_INCR, count=1)
        self.assertMetric('system.swap.swapped_out', value=SWAP_OUT_INCR, count=1)
