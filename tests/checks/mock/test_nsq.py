# 3p
import simplejson as json

# project
from tests.checks.common import AgentCheckTest, Fixtures
from checks import AgentCheck

class TestNsq(AgentCheckTest):
    CHECK_NAME = 'nsq'

    def test_simple_metrics(self):
        mocks = {
            'get_json': lambda x,y: json.loads(Fixtures.read_file('nsq_stats.json')),
        }
        config = {
            'instances': [{'url': 'http://localhost:44151'}]
        }

        self.run_check(config, mocks=mocks, force_reload=True)

        expected_metrics = ['nsq.topic_count']

        for metric in expected_metrics:
            self.assertMetric(metric, count=1, tags=[])

        topic_expected_metrics = ['depth', 'backend_depth', 'message_count']
        for metric in topic_expected_metrics:
            self.assertMetric('nsq.topic.' + metric, count=1, tags=['topic_name:bapi_events'])

        channel_expected_metrics = ['depth', 'backend_depth', 'message_count', 'in_flight_count', 'deferred_count', 'requeue_count', 'timeout_count', 'e2e_processing_latency.p50']
        for metric in channel_expected_metrics:
            self.assertMetric('nsq.topic.channel.' + metric, count=1, tags=['topic_name:bapi_events', 'channel_name:nsq_to_file'])

        client_expected_metrics = ['ready_count', 'in_flight_count', 'message_count', 'finish_count', 'requeue_count']
        for metric in client_expected_metrics:
            self.assertMetric('nsq.topic.channel.client.' + metric, count=1, tags=['topic_name:bapi_events', 'channel_name:nsq_to_file', 'client_id:nsqsink2', 'client_version:V2', 'tls:False', 'user_agent:nsq_to_file/0.2.31 go-nsq/1.0.1-alpha', 'deflate:False', 'snappy:False'])
