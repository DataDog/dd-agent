# stdlib
import time

# 3p
import mock

# project
from tests.checks.common import AgentCheckTest, Fixtures


class TestLinuxVMExtras(AgentCheckTest):
    CHECK_NAME = 'linux_vm_extras'

    EXPECTED_METRICS = (
        ('system.linux.vm.pages.in', 0),
        ('system.linux.vm.pages.out', 33140),
        ('system.linux.vm.pages.swapped_in', 0),
        ('system.linux.vm.pages.swapped_out', 0),
        ('system.linux.vm.pages.faults', 797955),
        ('system.linux.vm.pages.major_faults', 0),
    )

    def test_check(self):
        config = {'instances': [{'tags': ['tag1:key1', 'tag2:key2']}]}
        with mock.patch('__builtin__.open',
                        return_value=open(Fixtures.file('proc_vmstat_1'), 'r'), autospec=True):
            self.run_check(config)

        # Run the check twice to compute `monotonic_count`s
        time.sleep(1)
        with mock.patch('__builtin__.open',
                        return_value=open(Fixtures.file('proc_vmstat_2'), 'r'), autospec=True):
            self.run_check(config)

        for metric, value in self.EXPECTED_METRICS:
            self.assertMetric(metric, value=value, tags=('tag1:key1', 'tag2:key2'), count=1)

        self.coverage_report()
