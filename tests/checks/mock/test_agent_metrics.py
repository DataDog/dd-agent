# 3p
import mock

# project
from checks import AGENT_METRICS_CHECK_NAME
from tests.checks.common import AgentCheckTest, load_check, log as tests_log

import logging

def setup_logging(logger, level):
    logger.setLevel(level)
    ch = logging.StreamHandler()
    logger.addHandler(ch)

setup_logging(tests_log, logging.INFO)


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

MOCK_CONFIG_3 = {
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
    'init_config': {
        'log_num_metrics': 'yes'
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

    def test_num_metrics(self):
        check = load_check(self.CHECK_NAME, MOCK_CONFIG_3, AGENT_CONFIG_DEV_MODE)
        check.log = tests_log

        self.assertTrue(check.in_developer_mode)
        self.assertTrue(check.log_num_metrics)

        metrics = [1, 2, 3]
        events = [1, 2]
        payload = {
            'metrics': metrics,
            'events': events
        }
        cpu_time = 300
        collection_time = 100
        emit_time = 200
        context = {
            'collection_time': collection_time,
            'emit_time': emit_time,
            'cpu_time': cpu_time
        }
        check.set_metric_context(payload, context)
        self.check = check

        self.run_check(MOCK_CONFIG_3)

        self.assertMetric('datadog.agent.collector.num_metrics', value=len(metrics))
        self.assertMetric('datadog.agent.collector.num_events', value=len(events))

        self.assertMetric('datadog.agent.collector.collection.time', value=collection_time)
        self.assertMetric('datadog.agent.emitter.emit.time', value=emit_time)

        cpu_used_pct = 100.0 * float(cpu_time)/float(collection_time)
        self.assertMetric('datadog.agent.collector.cpu.used', value=cpu_used_pct)
