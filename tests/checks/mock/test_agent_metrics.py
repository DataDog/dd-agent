import mock
from tests.checks.common import AgentCheckTest, load_check

MOCK_CONFIG = {
        'instances': [
            {'process_metrics': {
                'get_memory_info': True,
                'get_cpu_times': True
            }}],
        'init_config': {}
}

MOCK_CONFIG_2 = {
    'instances': [{}],
    'init_config': {
        'process_metrics': {
            'get_memory_info': True,
            'get_nonexistent_stat': True
        }
    }
}

AGENT_CONFIG_DEV_MODE = {
    'developer_mode': True
}

AGENT_CONFIG_DEFAULT_MODE = {}

MOCK_STATS = {
    'memory_info': dict([('rss', 16814080), ('vms', 74522624)]),
    'cpu_times': dict([('user', 0.041733968), ('system', 0.022306718)])
    }


class AgentMetricsTestCase(AgentCheckTest):

    CHECK_NAME = 'agent_metrics'

    def mock_psutil_config_to_stats(self):
        return MOCK_STATS

    ### Tests for Agent Developer Mode
    def test_psutil_config_to_stats(self):
        check = load_check(self.CHECK_NAME, MOCK_CONFIG, AGENT_CONFIG_DEV_MODE)
        instance = MOCK_CONFIG.get('instances')[0]

        stats = check._psutil_config_to_stats(instance)
        self.assertIn('memory_info', stats)
        self.assertIn('cpu_times', stats)

    def test_register_psutil_metrics(self):
        check = load_check(self.CHECK_NAME, MOCK_CONFIG, AGENT_CONFIG_DEV_MODE)
        check._register_psutil_metrics(MOCK_STATS)
        self.metrics = check.get_metrics()

        self.assertMetric('datadog.agent.collector.memory_info.rss', value=16814080)
        self.assertMetric('datadog.agent.collector.memory_info.vms', value=74522624)

    def test_bad_process_metric_check(self):
        ''' Tests that a bad configuration option for `process_metrics` gets ignored '''
        check = load_check(self.CHECK_NAME, MOCK_CONFIG_2, AGENT_CONFIG_DEV_MODE)
        instance = MOCK_CONFIG.get('instances')[0]
        stats = check._psutil_config_to_stats(instance)

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


if __name__ == '__main__':
    import unittest; unittest.main()
