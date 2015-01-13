# stdlib
from xml.etree import ElementTree

# third party
import requests

# project
from checks import AgentCheck

QUEUE_URL = "/admin/xml/queues.jsp"
TOPIC_URL = "/admin/xml/topics.jsp"
SUBSCRIBER_URL = "/admin/xml/subscribers.jsp"


class ActiveMQXML(AgentCheck):
    # do this so we can mock out requests in unit tests
    requests = requests

    def check(self, instance):
        url = instance.get("url")
        username = instance.get("username")
        password = instance.get("password")

        self.log.debug("Processing ActiveMQ data for %s" % url)

        data = self._fetch_data(url, QUEUE_URL, username, password)
        self._process_queue_data(data)

        data = self._fetch_data(url, TOPIC_URL, username, password)
        self._process_topic_data(data)

        data = self._fetch_data(url, SUBSCRIBER_URL, username, password)
        self._process_subscriber_data(data)

    def _fetch_data(self, base_url, xml_url, username, password):
        auth = None
        if username and password:
            auth = (username, password)
        url = "%s%s" % (base_url, xml_url)
        self.log.debug("ActiveMQ Fetching queue data from: %s" % url)
        req = self.requests.get(url, auth=auth)
        return req.text

    def _process_queue_data(self, data):
        root = ElementTree.fromstring(data)
        queues = []

        for queue in root.findall("queue"):
            name = queue.get("name")
            if not name:
                continue
            queues.append(name)
            stats = queue.find("stats")
            if stats is None:
                continue
            tags = [
                "queue:%s" % (name, )
            ]
            consumer_count = stats.get("consumerCount", 0)
            dequeue_count = stats.get("dequeueCount", 0)
            enqueue_count = stats.get("enqueueCount", 0)
            size = stats.get("size", 0)

            self.log.debug(
                "ActiveMQ Queue %s: %s %s %s %s" % (
                    name, consumer_count, dequeue_count,
                    enqueue_count, size
                )
            )
            self.gauge("activemq.queue.consumer_count", consumer_count, tags=tags)
            self.gauge("activemq.queue.dequeue_count", dequeue_count, tags=tags)
            self.gauge("activemq.queue.enqueue_count", enqueue_count, tags=tags)
            self.gauge("activemq.queue.size", size, tags=tags)

        self.log.debug("ActiveMQ Queue Count: %s" % (len(queues), ))
        self.gauge("activemq.queues.count", len(queues))

    def _process_topic_data(self, data):
        root = ElementTree.fromstring(data)
        topics = []

        for topic in root.findall("topic"):
            name = topic.get("name")
            if not name:
                continue
            topics.append(name)
            stats = topic.find("stats")
            if stats is None:
                continue
            tags = [
                "topic:%s" % (name, )
            ]
            consumer_count = stats.get("consumerCount", 0)
            dequeue_count = stats.get("dequeueCount", 0)
            enqueue_count = stats.get("enqueueCount", 0)
            size = stats.get("size", 0)

            self.log.debug(
                "ActiveMQ Topic %s: %s %s %s %s" % (
                    name, consumer_count, dequeue_count,
                    enqueue_count, size
                )
            )
            self.gauge("activemq.topic.consumer_count", consumer_count, tags=tags)
            self.gauge("activemq.topic.dequeue_count", dequeue_count, tags=tags)
            self.gauge("activemq.topic.enqueue_count", enqueue_count, tags=tags)
            self.gauge("activemq.topic.size", size, tags=tags)

        self.log.debug("ActiveMQ Topic Count: %s" % (len(topics), ))
        self.gauge("activemq.topic.count", len(topics))

    def _process_subscriber_data(self, data):
        root = ElementTree.fromstring(data)
        subscribers = []

        tag_names = [
            "connectionId",
            "subscriptionName",
            "destinationName",
            "selector",
            "active",
        ]

        for subscriber in root.findall("subscriber"):
            clientId = subscriber.get("clientId")
            if not clientId:
                continue
            subscribers.append(clientId)
            stats = subscriber.find("stats")
            if stats is None:
                continue
            tags = [
                "clientId:%s" % (clientId, ),
            ]

            for name in tag_names:
                value = subscriber.get(name)
                if value is not None:
                    tags.append("%s:%s" % (name, value))

            pending_queue_size = stats.get("pendingQueueSize", 0)
            dequeue_counter = stats.get("dequeueCounter", 0)
            enqueue_counter = stats.get("enqueueCounter", 0)
            dispatched_queue_size = stats.get("dispatchedQueueSize", 0)
            dispatched_counter = stats.get("dispatchedCounter", 0)

            self.log.debug(
                "ActiveMQ Subscriber %s: %s %s %s %s %s" % (
                    clientId, pending_queue_size, dequeue_counter,
                    enqueue_counter, dispatched_queue_size, dispatched_counter
                )
            )
            self.gauge("activemq.subscriber.pending_queue_size", pending_queue_size, tags=tags)
            self.gauge("activemq.subscriber.dequeue_counter", dequeue_counter, tags=tags)
            self.gauge("activemq.subscriber.enqueue_counter", enqueue_counter, tags=tags)
            self.gauge("activemq.subscriber.dispatched_queue_size", dispatched_queue_size, tags=tags)
            self.gauge("activemq.subscriber.dispatched_counter", dispatched_counter, tags=tags)

        self.log.debug("ActiveMQ Subscriber Count: %s" % (len(subscribers), ))
        self.gauge("activemq.subscriber.count", len(subscribers))
