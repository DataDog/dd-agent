import mock
from tests.common import AgentCheckTest, load_check
from collections import OrderedDict

MOCK_CONFIG = {
        'instances': [
            {'process_metrics': {
                'get_memory_info': True,
                'get_io_counters': True
            }}],
        'init_config': {}
}

AGENT_CONFIG_DEV_MODE = {
    'developer_mode': True
}

AGENT_CONFIG_NO_DEV_MODE = {
    'developer_mode': False
}

MOCK_INSTANCE_2 = {
    'process_metrics': {
        'get_memory_info': True,
        'get_io_counters': False
    }
}

MOCK_INIT_CONFIG = {
    'process_metrics': {
        'get_num_threads': True
    }
}

MOCK_STATS = {
    'memory_info': OrderedDict([('rss', 16814080), ('vms', 74522624)]),
    'io_counters': OrderedDict([('read_count', 2563708),
        ('write_count', 54282),
        ('read_bytes', 4096),
        ('write_bytes', 0)])
    }

class AgentMetricsTestCase(AgentCheckTest):

    CHECK_NAME = 'agent_metrics'

    def test_psutil_config_to_stats(self):
        check = load_check(self.CHECK_NAME, MOCK_CONFIG, AGENT_CONFIG_DEV_MODE)
        instance = MOCK_CONFIG.get('instances')[0]

        stats = check._psutil_config_to_stats(instance)
        self.assertIn('memory_info', stats)
        self.assertIn('io_counters', stats)

    def test_register_psutil_metrics(self):
        check = load_check(self.CHECK_NAME, MOCK_CONFIG, AGENT_CONFIG_DEV_MODE)
        check._register_psutil_metrics(MOCK_STATS)
        self.assertMetric('datadog.agent.memory_info.rss', value=16814000)
        self.assertMetric('datadog.agent.memory_info.vms', value=74522624)

    def test_check(self):
        pass


if __name__ == '__main__':
    import unittest; unittest.main()
