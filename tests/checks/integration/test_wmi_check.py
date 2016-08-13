# stdlib
import copy

# 3p
from mock import Mock
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

INSTANCE = {
    'class': 'Win32_PerfFormattedData_PerfProc_Process',
    'metrics': [
        ['ThreadCount', 'proc.threads.count', 'gauge'],
        ['IOReadBytesPerSec', 'proc.io.bytes_read', 'gauge'],
        ['VirtualBytes', 'proc.mem.virtual', 'gauge'],
        ['PercentProcessorTime', 'proc.cpu_pct', 'gauge'],
    ],
    'tag_by': 'Name',
}

INSTANCE_METRICS = [
    'proc.threads.count',
    'proc.io.bytes_read',
    'proc.mem.virtual',
    'proc.cpu_pct',
]


@attr('windows')
@attr(requires='windows')
class WMICheckTest(AgentCheckTest):
    CHECK_NAME = 'wmi_check'

    def test_basic_check(self):
        instance = copy.deepcopy(INSTANCE)
        instance['filters'] = [{'Name': 'svchost'}]
        self.run_check({'instances': [instance]})

        for metric in INSTANCE_METRICS:
            self.assertMetric(metric, tags=['name:svchost'], count=1)

        self.coverage_report()

    def test_check_with_wildcard(self):
        instance = copy.deepcopy(INSTANCE)
        instance['filters'] = [{'Name': 'svchost%'}]
        self.run_check({'instances': [instance]})

        for metric in INSTANCE_METRICS:
            # We can assume that at least 2 svchost processes are running
            self.assertMetric(metric, tags=['name:svchost'], count=1)
            self.assertMetric(metric, tags=['name:svchost#1'], count=1)

    def test_check_with_tag_queries(self):
        instance = copy.deepcopy(INSTANCE)
        instance['filters'] = [{'Name': 'svchost%'}]
        # `CreationDate` is a good property to test the tag queries but would obviously not be useful as a tag in DD
        instance['tag_queries'] = [['IDProcess', 'Win32_Process', 'Handle', 'CreationDate']]
        self.run_check({'instances': [instance]})

        for metric in INSTANCE_METRICS:
            # No instance "number" (`#`) when tag_queries is specified
            self.assertMetricTag(metric, tag='name:svchost#1', count=0)
            self.assertMetricTag(metric, tag='name:svchost')
            self.assertMetricTagPrefix(metric, tag_prefix='creationdate:')

    def test_invalid_class(self):
        instance = copy.deepcopy(INSTANCE)
        instance['class'] = 'Unix'
        logger = Mock()

        self.run_check({'instances': [instance]}, mocks={'log': logger})

        # A warning is logged
        self.assertEquals(logger.warning.call_count, 1)

        # No metrics/service check
        self.coverage_report()

    def test_invalid_metrics(self):
        instance = copy.deepcopy(INSTANCE)
        instance['metrics'].append(['InvalidProperty', 'proc.will.not.be.reported', 'gauge'])
        logger = Mock()

        self.run_check({'instances': [instance]}, mocks={'log': logger})

        # A warning is logged
        self.assertEquals(logger.warning.call_count, 1)

        # No metrics/service check
        self.coverage_report()
