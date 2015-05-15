# stdlib
from itertools import product

# 3rd
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


@attr(requires='activemq')
class ActiveMQTestCase(AgentCheckTest):
    CHECK_NAME = 'activemq_xml'

    CONFIG = {
        'url': "http://localhost:8161",
        'username': "admin",
        'password': "admin"
    }

    GENERAL_METRICS = [
        "activemq.subscriber.count",
        "activemq.topic.count",
        "activemq.queue.count",
    ]

    QUEUE_METRICS = [
        "activemq.queue.consumer_count",
        "activemq.queue.dequeue_count",
        "activemq.queue.enqueue_count",
        "activemq.queue.size",
    ]

    SUBSCRIBER_METRICS = [
        "activemq.subscriber.pending_queue_size",
        "activemq.subscriber.dequeue_counter",
        "activemq.subscriber.enqueue_counter",
        "activemq.subscriber.dispatched_queue_size",
        "activemq.subscriber.dispatched_counter",
    ]

    TOPIC_METRICS = [
        "activemq.topic.consumer_count",
        "activemq.topic.dequeue_count",
        "activemq.topic.enqueue_count",
        "activemq.topic.size",
    ]

    def test_check(self):
        """
        Collect ActiveMQ metrics
        """
        config = {
            'instances': [self.CONFIG]
        }

        self.run_check(config)

        tags = ["url:{0}".format(self.CONFIG['url'])]

        # Test metrics
        for mname in self.GENERAL_METRICS:
            self.assertMetric(mname, count=1, tags=tags)

        for mname in self.QUEUE_METRICS:
            self.assertMetric(mname, count=1, tags=tags + ["queue:my_queue"])

        for mname, tname in product(self.TOPIC_METRICS,
                                    ["my_topic", "ActiveMQ.Advisory.MasterBroker"]):
            self.assertMetric(mname, count=1, tags=tags + ["topic:{0}".format(tname)])

        for mname in self.SUBSCRIBER_METRICS:
            subscriber_tags = tags + \
                ["clientId:my_client", "connectionId:NOTSET", "subscriptionName:my_subscriber",
                 "destinationName:my_topic", "selector:jms_selector", "active:no"]
            self.assertMetric(mname, count=1, tags=subscriber_tags)

        self.coverage_report()
