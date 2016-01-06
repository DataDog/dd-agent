# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

@attr('linux')
@attr(requires='linux')
class TestCheckLinuxProcExtras(AgentCheckTest):
    CHECK_NAME = 'linux_proc_extras'

    INODE_GAUGES = [
        'system.inodes.total',
        'system.inodes.used'
    ]

    PROC_COUNTS = [
        'system.linux.context_switches',
        'system.linux.processes_created',
        'system.linux.interrupts'
    ]

    ENTROPY_GAUGES = [
        'system.entropy.available'
    ]

    PROCESS_STATS_GAUGES = [
        'system.processes.states',
        'system.processes.priorities'
    ]

    # Really a basic check to see if all metrics are there
    def test_check(self):
        self.run_check({'instances': []})

        # Assert metrics
        for metric in self.PROC_COUNTS + self.INODE_GAUGES + self.ENTROPY_GAUGES + self.PROCESS_STATS_GAUGES:
            self.assertMetric(metric, tags=[])

        self.coverage_report()
