# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

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

COMMON_METRICS = [
    'rabbitmq.node.fd_used',
    'rabbitmq.node.mem_used',
    'rabbitmq.node.run_queue',
    'rabbitmq.node.sockets_used',
]


@attr(requires='rabbitmq')
class RabbitMQCheckTest(AgentCheckTest):
    CHECK_NAME = 'rabbitmq'

    def test_check(self):
        self.run_check(CONFIG)

        # Node attributes
        for mname in COMMON_METRICS:
            self.assertMetricTagPrefix(mname, 'rabbitmq_node', count=1)

        # Queue attributes, should be only one queue fetched
        # TODO: create a 'fake consumer' and get missing metrics
        # active_consumers, acks, delivers, redelivers
        Q_METRICS = [
            'consumers',
            'memory',
            'messages',
            'messages.rate',
            'messages_ready',
            'messages_ready.rate',
            'messages_unacknowledged',
            'messages_unacknowledged.rate',
            'messages.publish.count',
            'messages.publish.rate',
        ]
        for mname in Q_METRICS:
            self.assertMetricTag('rabbitmq.queue.%s' %
                                 mname, 'rabbitmq_queue:test1', count=1)

        self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:/'])

        self.coverage_report()

    def test_queue_regex(self):
        self.run_check(CONFIG_REGEX)

        # Node attributes
        for mname in COMMON_METRICS:
            self.assertMetricTagPrefix(mname, 'rabbitmq_node', count=1)

        Q_METRICS = [
            'consumers',
            'memory',
            'messages',
            'messages.rate',
            'messages_ready',
            'messages_ready.rate',
            'messages_unacknowledged',
            'messages_unacknowledged.rate',
            'messages.publish.count',
            'messages.publish.rate',
        ]
        for mname in Q_METRICS:
            self.assertMetricTag('rabbitmq.queue.%s' %
                                 mname, 'rabbitmq_queue:test1', count=1)
            self.assertMetricTag('rabbitmq.queue.%s' %
                                 mname, 'rabbitmq_queue:test5', count=1)
            self.assertMetricTag('rabbitmq.queue.%s' %
                                 mname, 'rabbitmq_queue:tralala', count=0)

        self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:/'])

        self.coverage_report()
