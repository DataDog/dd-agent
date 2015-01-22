# 3p
from nose.plugins.attrib import attr

# project
from tests.common import AgentCheckTest

CONFIG = {
    'init_config': {},
    'instances': [
        {
            'rabbitmq_api_url': 'http://localhost:15672/api/',
            'rabbitmq_user': 'guest',
            'rabbitmq_pass': 'guest',
            'queues': ['test1'],
        }
    ]
}

CONFIG_REGEX = {
    'init_config': {},
    'instances': [
        {
            'rabbitmq_api_url': 'http://localhost:15672/api/',
            'rabbitmq_user': 'guest',
            'rabbitmq_pass': 'guest',
            'queues_regexes': ['test\d+'],
        }
    ]
}


@attr(requires='rabbitmq')
class RabbitMQCheckTest(AgentCheckTest):
    CHECK_NAME = 'rabbitmq'

    def test_check(self):
        self.run_check(CONFIG)

        # Node attributes
        self.assertMetric('rabbitmq.node.fd_used')
        self.assertMetric('rabbitmq.node.mem_used')
        self.assertMetric('rabbitmq.node.run_queue')
        self.assertMetric('rabbitmq.node.sockets_used')
        self.assertMetricTagPrefix('rabbitmq.node.fd_used', 'rabbitmq_node')

        # Queue attributes, should be only one queue fetched
        Q_METRICS = [
#            'active_consumers',  # no active consumers in this test..
            'consumers',
            'memory',
            'messages',
            'messages.rate',
            'messages_ready',
            'messages_ready.rate',
            'messages_unacknowledged',
            'messages_unacknowledged.rate',
# Not available right now b/c of the way we configure rabbitmq on Travis
#            'messages.ack.count',
#            'messages.ack.rate',
#            'messages.deliver.count',
#            'messages.deliver.rate',
#            'messages.deliver_get.count',
#            'messages.deliver_get.rate',
#            'messages.publish.count',
#            'messages.publish.rate',
#            'messages.redeliver.count',
#            'messages.redeliver.rate',
        ]
        for mname in Q_METRICS:
            self.assertMetricTag('rabbitmq.queue.%s' % mname, 'rabbitmq_queue:test1', count=1)

    def test_queue_regex(self):
        self.run_check(CONFIG_REGEX)

        Q_METRICS = [
#            'active_consumers',  # no active consumers in this test..
            'consumers',
            'memory',
            'messages',
            'messages.rate',
            'messages_ready',
            'messages_ready.rate',
            'messages_unacknowledged',
            'messages_unacknowledged.rate',
# Not available right now b/c of the way we configure rabbitmq on Travis
#            'messages.ack.count',
#            'messages.ack.rate',
#            'messages.deliver.count',
#            'messages.deliver.rate',
#            'messages.deliver_get.count',
#            'messages.deliver_get.rate',
#            'messages.publish.count',
#            'messages.publish.rate',
#            'messages.redeliver.count',
#            'messages.redeliver.rate',
        ]
        for mname in Q_METRICS:
            self.assertMetricTag('rabbitmq.queue.%s' % mname, 'rabbitmq_queue:test1', count=1)
            self.assertMetricTag('rabbitmq.queue.%s' % mname, 'rabbitmq_queue:test5', count=1)
            self.assertMetricTag('rabbitmq.queue.%s' % mname, 'rabbitmq_queue:tralala', count=0)
