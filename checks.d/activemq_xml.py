# stdlib
import urllib2
from xml.etree import ElementTree

# project
from checks import AgentCheck
from util import headers

QUEUE_URL = "/admin/xml/queues.jsp"


class ActiveMQXML(AgentCheck):
    def check(self, instance):
        url = instance.get("url")
        username = instance.get("username")
        password = instance.get("password")

        self.log.debug("Processing ActiveMQ data for %s" % url)

        data = self._fetch_data(url, username, password)
        self._process_data(data)

    def _fetch_data(self, url, username, password):
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, url, username, password)
        authhandler = urllib2.HTTPBasicAuthHandler(passman)
        opener = urllib2.build_opener(authhandler)
        urllib2.install_opener(opener)
        url = "%s%s" % (url, QUEUE_URL)

        self.log.debug("ActiveMQ Fetching queue data from: %s" % url)

        req = urllib2.Request(url, None, headers(self.agentConfig))
        request = urllib2.urlopen(req)
        return request.read()

    def _process_data(self, data):
        root = ElementTree.fromstring(data)
        queues = []

        for queue in root.iter("queue"):
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
