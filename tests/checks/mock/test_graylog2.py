# standard library
import json

# third party
import mock

# project
from tests.checks.common import AgentCheckTest, Fixtures


CLUSTER_ID = '1a7f9f7d-9899-4fa4-821d-1c5ddfb5a823'
NODE_ID = '90047b0c-8f35-4db5-9205-ccf2521401c6'

CLUSTER_URI = 'http://localhost:12900/cluster'
METRICS_CLUSTER_EVENTBUS_URI = 'http://localhost:12900/cluster/%s/metrics/namespace/cluster-eventbus.' % (NODE_ID, )
METRICS_JVM_URI = 'http://localhost:12900/cluster/%s/metrics/namespace/jvm.' % (NODE_ID, )
METRICS_ORG_APACHE_URI = 'http://localhost:12900/cluster/%s/metrics/namespace/org.apache.' % (NODE_ID, )
METRICS_ORG_GRAYLOG2_URI = 'http://localhost:12900/cluster/%s/metrics/namespace/org.graylog2.' % (NODE_ID, )

def requests_mock(*args, **kwargs):
    class MockResponse(object):
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    if args[0] == CLUSTER_URI:
        with open(Fixtures.file('cluster_info'), 'r') as fp:
            body = fp.read()
            return MockResponse(body, 200)
    elif args[0] == METRICS_CLUSTER_EVENTBUS_URI:
        with open(Fixtures.file('metrics_cluster_eventbus'), 'r') as fp:
            body = fp.read()
            return MockResponse(body, 200)
    elif args[0] == METRICS_JVM_URI:
        with open(Fixtures.file('metrics_jvm'), 'r') as fp:
            body = fp.read()
            return MockResponse(body, 200)
    elif args[0] == METRICS_ORG_APACHE_URI:
        with open(Fixtures.file('metrics_org_apache'), 'r') as fp:
            body = fp.read()
            return MockResponse(body, 200)
    elif args[0] == METRICS_ORG_GRAYLOG2_URI:
        with open(Fixtures.file('metrics_org_graylog2'), 'r') as fp:
            body = fp.read()
            return MockResponse(body, 200)


class TestGraylog2(AgentCheckTest):
    CHECK_NAME = 'graylog2'
    CONFIG = {
        'transport_uri': 'http://localhost:12900/',
    }
    WHITELIST_CONFIG = {
        'transport_uri': 'http://localhost:12900/',
        'prefix_whitelist': [
            'jvm.',
        ],
    }
    BLACKLIST_CONFIG = {
        'transport_uri': 'http://localhost:12900/',
        'prefix_blacklist': [
            'jvm.',
        ],
    }

    JVM_METRICS = {
        'graylog2.jvm.memory.pools.code_cache.usage.value': 0.2557779947916667,
        'graylog2.jvm.memory.pools.ps_eden_space.committed.value': 177209344,
        'graylog2.jvm.memory.pools.ps_survivor_space.init.value': 2621440,
        'graylog2.jvm.threads.waiting.count.value': 139,
    }

    GRAYLOG_METRICS = {
        'graylog2.buffers.output.size.value': 65536,
        'graylog2.outputs.blocking_batched_es_output.batch_size.count': 962,
        'graylog2.outputs.blocking_batched_es_output.batch_size.time.95th_percentile': 3,
        'graylog2.outputs.blocking_batched_es_output.batch_size.time.98th_percentile': 3,
        'graylog2.outputs.blocking_batched_es_output.batch_size.time.99th_percentile': 3,
        'graylog2.outputs.blocking_batched_es_output.batch_size.time.max': 133,
        'graylog2.outputs.blocking_batched_es_output.batch_size.time.mean': 2,
        'graylog2.outputs.blocking_batched_es_output.batch_size.time.min': 1,
        'graylog2.outputs.blocking_batched_es_output.batch_size.time.std_dev': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.duration_unit': u'microseconds',
        'graylog2.rest.resources.streams.stream_resource.resume.rate.fifteen_minute': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.rate.five_minute': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.rate.mean': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.rate.one_minute': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.rate.total': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.rate_unit': u'events/second',
        'graylog2.rest.resources.streams.stream_resource.resume.time.95th_percentile': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.time.98th_percentile': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.time.99th_percentile': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.time.max': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.time.mean': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.time.min': 0,
        'graylog2.rest.resources.streams.stream_resource.resume.time.std_dev': 0,
        'graylog2.shared.journal.journal_reader.requested_read_count.count': 2231,
        'graylog2.shared.journal.journal_reader.requested_read_count.time.95th_percentile': 65599,
        'graylog2.shared.journal.journal_reader.requested_read_count.time.98th_percentile': 65599,
        'graylog2.shared.journal.journal_reader.requested_read_count.time.99th_percentile': 65599,
        'graylog2.shared.journal.journal_reader.requested_read_count.time.max': 65599,
        'graylog2.shared.journal.journal_reader.requested_read_count.time.mean': 65540,
        'graylog2.shared.journal.journal_reader.requested_read_count.time.min': 65440,
        'graylog2.shared.journal.journal_reader.requested_read_count.time.std_dev': 24,
    }

    EXPECTED_TAGS = [
        'node_facility:graylog-server',
        'node_hostname:ip-127-0-0-1.ec2.internal',
        'graylog_version:2.0.0-beta.1 (f8d0c45)',
        'node_cluster_id:%s' % (CLUSTER_ID, ),
        'node_codename:graylog-codename',
        'node_id:%s' % (NODE_ID, ),
    ]

    @mock.patch('requests.get', side_effect=requests_mock)
    def test_check(self, mock_requests):
        config = {
            'instances': [self.CONFIG],
        }

        # Run the check
        self.run_check(config)

        # Assert we emitted the expected graylog2 metrics
        for metric, value in self.GRAYLOG_METRICS.iteritems():
            self.assertMetric(metric, value=value, tags=self.EXPECTED_TAGS)

        # Assert we emitted the expected jvm metrics
        for metric, value in self.JVM_METRICS.iteritems():
            self.assertMetric(metric, value=value, tags=self.EXPECTED_TAGS)

        # Assert that we emitted the correct number of metrics
        expected_metrics = len(self.GRAYLOG_METRICS) + len(self.JVM_METRICS)
        self.assertEqual(expected_metrics, len(self.metrics))

    @mock.patch('requests.get', side_effect=requests_mock)
    def test_check_whitelist(self, mock_requests):
        config = {
            'instances': [self.WHITELIST_CONFIG],
        }

        # Run the check
        self.run_check(config)

        # Assert we emitted the expected metrics
        for metric, value in self.JVM_METRICS.iteritems():
            self.assertMetric(metric, value=value, tags=self.EXPECTED_TAGS)

        # Assert that we emitted *only* the JVM metrics
        self.assertEqual(len(self.JVM_METRICS), len(self.metrics))

    @mock.patch('requests.get', side_effect=requests_mock)
    def test_check_blacklist(self, mock_requests):
        config = {
            'instances': [self.BLACKLIST_CONFIG],
        }

        # Run the check
        self.run_check(config)

        # Assert we emitted the expected metrics
        for metric, value in self.GRAYLOG_METRICS.iteritems():
            self.assertMetric(metric, value=value, tags=self.EXPECTED_TAGS)

        # Assert that we emitted *only* the graylog2 metrics
        self.assertEqual(len(self.GRAYLOG_METRICS), len(self.metrics))
