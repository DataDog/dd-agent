# 3p
import mock

# project
from checks import AGENT_METRICS_CHECK_NAME
from tests.checks.common import AgentCheckTest, load_check

MOCK_CONFIG = {
    'instances': [
        {'process_metrics': [
            {
                'name': 'memory_info',
                'type': 'gauge',
                'active': 'yes'
            },
            {
                'name': 'cpu_times',
                'type': 'rate',
                'active': 'yes'
            },
        ]}],
    'init_config': {}
}

MOCK_CONFIG_2 = {
    'instances': [
        {'process_metrics': [
            {
                'name': 'memory_info',
                'type': 'gauge',
                'active': 'yes'
            },
            {
                'name': 'get_non_existent_stat',
                'type': 'gauge',
                'active': 'yes'
            },
        ]}],
    'init_config': {}
}

AGENT_CONFIG_DEV_MODE = {
    'developer_mode': True
}

AGENT_CONFIG_DEFAULT_MODE = {}

MOCK_STATS = {
    'memory_info': dict([('rss', 16814080), ('vms', 74522624)]),
    'cpu_times': dict([('user', 0.041733968), ('system', 0.022306718)])
}

MOCK_NAMES_TO_METRIC_TYPES = {
    'memory_info': 'gauge',
    'cpu_times': 'gauge'
}


class AgentMetricsTestCase(AgentCheckTest):

    CHECK_NAME = AGENT_METRICS_CHECK_NAME

    def mock_psutil_config_to_stats(self):
        return MOCK_STATS, MOCK_NAMES_TO_METRIC_TYPES

    ### Tests for Agent Developer Mode
    def test_psutil_config_to_stats(self):
        check = load_check(self.CHECK_NAME, MOCK_CONFIG, AGENT_CONFIG_DEV_MODE)
        instance = MOCK_CONFIG.get('instances')[0]

        stats, names_to_metric_types = check._psutil_config_to_stats(instance)
        self.assertIn('memory_info', names_to_metric_types)
        self.assertEqual(names_to_metric_types['memory_info'], 'gauge')

        self.assertIn('cpu_times', names_to_metric_types)
        self.assertEqual(names_to_metric_types['cpu_times'], 'rate')

        self.assertIn('memory_info', stats)
        self.assertIn('cpu_times', stats)

    def test_send_single_metric(self):
        check = load_check(self.CHECK_NAME, MOCK_CONFIG, AGENT_CONFIG_DEV_MODE)
        check.gauge = mock.MagicMock()
        check.rate = mock.MagicMock()

        check._send_single_metric('datadog.agent.collector.memory_info.vms', 16814081, 'gauge')
        check.gauge.assert_called_with('datadog.agent.collector.memory_info.vms', 16814081)

        check._send_single_metric('datadog.agent.collector.memory_info.vms', 16814081, 'rate')
        check.rate.assert_called_with('datadog.agent.collector.memory_info.vms', 16814081)

        self.assertRaises(Exception, check._send_single_metric,
                          *('datadog.agent.collector.memory_info.vms', 16814081, 'bogus'))

    def test_register_psutil_metrics(self):
        check = load_check(self.CHECK_NAME, MOCK_CONFIG, AGENT_CONFIG_DEV_MODE)
        check._register_psutil_metrics(MOCK_STATS, MOCK_NAMES_TO_METRIC_TYPES)
        self.metrics = check.get_metrics()

        self.assertMetric('datadog.agent.collector.memory_info.rss', value=16814080)
        self.assertMetric('datadog.agent.collector.memory_info.vms', value=74522624)

    def test_bad_process_metric_check(self):
        ''' Tests that a bad configuration option for `process_metrics` gets ignored '''
        check = load_check(self.CHECK_NAME, MOCK_CONFIG_2, AGENT_CONFIG_DEV_MODE)
        instance = MOCK_CONFIG.get('instances')[0]
        stats, names_to_metric_types = check._psutil_config_to_stats(instance)

        self.assertIn('memory_info', names_to_metric_types)
        self.assertEqual(names_to_metric_types['memory_info'], 'gauge')

        self.assertNotIn('non_existent_stat', names_to_metric_types)

        self.assertIn('memory_info', stats)
        self.assertNotIn('non_existent_stat', stats)

    ### Tests for Agent Default Mode
    def test_no_process_metrics_collected(self):
        ''' Test that additional process metrics are not collected when in default mode '''
        mocks = {
            '_register_psutil_metrics': mock.MagicMock(side_effect=AssertionError),
            '_psutil_config_to_stats': mock.MagicMock(side_effect=AssertionError),
        }

        self.run_check(MOCK_CONFIG, mocks=mocks)
