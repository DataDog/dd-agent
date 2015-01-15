import unittest

import mock

from tests.common import get_check


class ActiveMQXMLTestCase(unittest.TestCase):
    def setUp(self):
        self.config = """
init_config:

instances:
   -   username: username
       password: password
       url: http://localhost:8161
"""

    def test_fetch_data(self):
        # not too concerned with the response body, just that requests.get was called
        # with the correct arguments
        check, instances = get_check('activemq_xml', self.config)
        check.requests = mock.Mock()
        check._fetch_data('http://localhost:8171', '/admin/xml/queues.jsp', None, None)
        assert check.requests.get.call_count == 1
        assert check.requests.get.call_args == mock.call(
            'http://localhost:8171/admin/xml/queues.jsp', auth=None
        )

        check.requests.get.reset_mock()
        check._fetch_data('http://localhost:8171', '/admin/xml/queues.jsp', 'user', 'pass')
        assert check.requests.get.call_count == 1
        assert check.requests.get.call_args == mock.call(
            'http://localhost:8171/admin/xml/queues.jsp', auth=('user', 'pass')
        )

    def test_check(self):
        check, instances = get_check('activemq_xml', self.config)
        check.requests = mock.Mock()

        def response_side_effect(*args, **kwargs):
            text = ''
            if '/admin/xml/topics.jsp' in args[0]:
                text = '<topics></topics>'
            elif '/admin/xml/queues.jsp' in args[0]:
                text = '<queues></queues>'
            elif '/admin/xml/subscribers.jsp' in args[0]:
                text = '<subscribers></subscribers>'
            # if text='' then we will get an xml parsing error
            # (which is what we want if we called with a url we dont know)
            return mock.Mock(text=text)

        check.requests.get.side_effect = response_side_effect
        check.check(instances[0])
        expected = {
            'url:http://localhost:8161': {
                'activemq.queue.count': (0, 'gauge'),
                'activemq.topic.count': (0, 'gauge'),
                'activemq.subscriber.count': (0, 'gauge'),
            }
        }
        self._assert_expected_metrics(expected, check.get_metrics())

    def test_process_queue_data_normal(self):
        check, instances = get_check('activemq_xml', self.config)

        data = """
        <queues>
          <queue name="Queue1">
            <stats size="0"
                   consumerCount="6"
                   enqueueCount="64714"
                   dequeueCount="64714"/>
            <feed>
              <atom>queueBrowse/Queue1;jsessionid=sess_token?view=rss&amp;feedType=atom_1.0</atom>
              <rss>queueBrowse/Queue1;jsessionid=sess_token?view=rss&amp;feedType=rss_2.0</rss>
            </feed>
          </queue>
          <queue name="Queue2">
            <stats size="10"
                   consumerCount="3"
                   enqueueCount="1165"
                   dequeueCount="1165"/>
            <feed>
              <atom>queueBrowse/Queue2;jsessionid=sess_token?view=rss&amp;feedType=atom_1.0</atom>
              <rss>queueBrowse/Queue2;jsessionid=sess_token?view=rss&amp;feedType=rss_2.0</rss>
            </feed>
          </queue>
        </queues>
        """
        check._process_data(data, "queue", [], 300, [])
        expected = {
            'queue:Queue2': {
                'activemq.queue.size': ('10', 'gauge'),
                'activemq.queue.enqueue_count': ('1165', 'gauge'),
                'activemq.queue.dequeue_count': ('1165', 'gauge'),
                'activemq.queue.consumer_count': ('3', 'gauge')
            },
            '': {
                'activemq.queue.count': (2, 'gauge')
            },
            'queue:Queue1': {
                'activemq.queue.dequeue_count': ('64714', 'gauge'),
                'activemq.queue.consumer_count': ('6', 'gauge'),
                'activemq.queue.size': ('0', 'gauge'),
                'activemq.queue.enqueue_count': ('64714', 'gauge'),
            },
        }

        self._assert_expected_metrics(expected, check.get_metrics())

    def test_process_queue_data_no_data(self):
        check, instances = get_check('activemq_xml', self.config)

        data = """
        <queues>
        </queues>
        """
        check._process_data(data, "queue", [], 300, [])
        expected = {
            '': {
                'activemq.queue.count': (0, 'gauge')
            },
        }

        self._assert_expected_metrics(expected, check.get_metrics())

    def test_process_topics_data_normal(self):
        check, instances = get_check('activemq_xml', self.config)

        data = """
        <topics>
          <topic name="Topic1">
            <stats size="5"
                   consumerCount="0"
                   enqueueCount="24"
                   dequeueCount="0"/>
          </topic>
          <topic name="Topic2">
            <stats size="1"
                   consumerCount="50"
                   enqueueCount="12"
                   dequeueCount="1200"/>
          </topic>
        </topics>
        """

        check._process_data(data, "topic", [], 300, [])
        expected = {
            'topic:Topic1': {
                'activemq.topic.size': ('5', 'gauge'),
                'activemq.topic.enqueue_count': ('24', 'gauge'),
                'activemq.topic.dequeue_count': ('0', 'gauge'),
                'activemq.topic.consumer_count': ('0', 'gauge')
            },
            '': {
                'activemq.topic.count': (2, 'gauge')
            },
            'topic:Topic2': {
                'activemq.topic.dequeue_count': ('1200', 'gauge'),
                'activemq.topic.consumer_count': ('50', 'gauge'),
                'activemq.topic.size': ('1', 'gauge'),
                'activemq.topic.enqueue_count': ('12', 'gauge'),
            },
        }

        self._assert_expected_metrics(expected, check.get_metrics())

    def test_process_topic_data_no_data(self):
        check, instances = get_check('activemq_xml', self.config)

        data = """
        <topics>
        </topics>
        """
        check._process_data(data, "topic", [], 300, [])
        expected = {
            '': {
                'activemq.topic.count': (0, 'gauge')
            },
        }

        self._assert_expected_metrics(expected, check.get_metrics())

    def test_process_subscriber_data_normal(self):
        check, instances = get_check('activemq_xml', self.config)

        data = """
        <subscribers>
          <subscriber clientId="10"
                      subscriptionName="subscription1"
                      connectionId="10"
                      destinationName="Queue1"
                      selector="*"
                      active="yes" >
            <stats pendingQueueSize="5"
                   dispatchedQueueSize="15"
                   dispatchedCounter="15"
                   enqueueCounter="235"
                   dequeueCounter="175"/>
          </subscriber>
          <subscriber clientId="5"
                      subscriptionName="subscription2"
                      connectionId="15"
                      destinationName="Topic1"
                      selector="*"
                      active="no" >
            <stats pendingQueueSize="0"
                   dispatchedQueueSize="0"
                   dispatchedCounter="5"
                   enqueueCounter="12"
                   dequeueCounter="15"/>
          </subscriber>
        </subscribers>
        """
        check._process_subscriber_data(data, [], 300, [])
        expected = {
            'active:yes-clientId:10-connectionId:10-destinationName:Queue1-selector:*-subscriptionName:subscription1': {
                'activemq.subscriber.enqueue_counter': ('235', 'gauge'),
                'activemq.subscriber.dequeue_counter': ('175', 'gauge'),
                'activemq.subscriber.dispatched_counter': ('15', 'gauge'),
                'activemq.subscriber.dispatched_queue_size': ('15', 'gauge'),
                'activemq.subscriber.pending_queue_size': ('5', 'gauge'),
            },
            '': {
                'activemq.subscriber.count': (2, 'gauge'),
            },
            'active:no-clientId:5-connectionId:15-destinationName:Topic1-selector:*-subscriptionName:subscription2': {
                'activemq.subscriber.enqueue_counter': ('12', 'gauge'),
                'activemq.subscriber.dequeue_counter': ('15', 'gauge'),
                'activemq.subscriber.dispatched_counter': ('5', 'gauge'),
                'activemq.subscriber.dispatched_queue_size': ('0', 'gauge'),
                'activemq.subscriber.pending_queue_size': ('0', 'gauge'),
            },
        }

        self._assert_expected_metrics(expected, check.get_metrics())

    def test_process_subscriber_data_no_data(self):
        check, instances = get_check('activemq_xml', self.config)

        data = """
        <subscribers>
        </subscribers>
        """
        check._process_subscriber_data(data, [], 300, [])
        expected = {
            '': {
                'activemq.subscriber.count': (0, 'gauge')
            },
        }

        self._assert_expected_metrics(expected, check.get_metrics())

    def _iter_metrics(self, metrics):
        for name, _, value, data in metrics:
            tags = sorted(data.get('tags', []))
            tags = '-'.join(tags)
            yield tags, name, value, data['type']

    def _assert_expected_metrics(self, expected, metrics):
        count = sum(len(r.keys()) for r in expected.values())
        self.assertEqual(count, len(metrics), (count, metrics))

        for tags, key, value, el_type in self._iter_metrics(metrics):
            self.assertEquals(expected.get(tags, {}).get(key), (value, el_type), (tags, key, metrics))


if __name__ == '__main__':
    unittest.main()
