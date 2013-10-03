import urllib2
import urlparse
import time

from checks import AgentCheck
from util import json

EVENT_TYPE = SOURCE_TYPE_NAME = 'rabbitmq'
QUEUE_TYPE = 'queues'
NODE_TYPE = 'nodes'
MAX_DETAILED_QUEUES = 200
MAX_DETAILED_NODES = 100
ALERT_THRESHOLD = 0.9 # Post an event in the stream when the number of queues or nodes to collect is above 90% of the limit
QUEUE_ATTRIBUTES = [ 
        'active_consumers',
        'consumers',
        'memory',
        'messages',
        'messages_ready',
        'messages_unacknowledged'
    ]

NODE_ATTRIBUTES = [
                'fd_total',
                'fd_used',
                'mem_limit',
                'mem_used',
                'run_queue',
                'sockets_total',
                'sockets_used',
    ]

ATTRIBUTES = {
    QUEUE_TYPE: QUEUE_ATTRIBUTES,
    NODE_TYPE: NODE_ATTRIBUTES,
}



TAGS_MAP = {
    QUEUE_TYPE: {
                'node':'node',
                'name':'queue',
                'vhost':'vhost',
                'policy':'policy',
            },
    NODE_TYPE: {
                'name':'node',
    }
}

METRIC_SUFFIX = {
    QUEUE_TYPE: "queue",
    NODE_TYPE: "node",
}

class RabbitMQ(AgentCheck):
    """This check is for gathering statistics from the RabbitMQ
    Management Plugin (http://www.rabbitmq.com/management.html)
    """

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.already_alerted = []

    def _get_config(self, instance):
        # make sure 'rabbitmq_api_url; is present
        if 'rabbitmq_api_url' not in instance:
            raise Exception('Missing "rabbitmq_api_url" in RabbitMQ config.')

        # get parameters
        base_url = instance['rabbitmq_api_url']
        if not base_url.endswith('/'):
            base_url += '/'
        username = instance.get('rabbitmq_user', 'guest')
        password = instance.get('rabbitmq_pass', 'guest')

        # Limit of queues/nodes to collect metrics from
        max_detailed = {
            QUEUE_TYPE: int(instance.get('max_detailed_queues', MAX_DETAILED_QUEUES)),
            NODE_TYPE: int(instance.get('max_detailed_nodes', MAX_DETAILED_NODES)),
        }

        # List of queues/nodes to collect metrics from
        specified = { 
            QUEUE_TYPE: instance.get('queues', []),
            NODE_TYPE: instance.get('nodes', []),
        }

        # setup urllib2 for Basic Auth
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(realm='RabbitMQ Management', uri=base_url, user=username, passwd=password)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        return base_url, max_detailed, specified


    def check(self, instance):
        base_url, max_detailed, specified = self._get_config(instance)
        self.get_stats(instance, base_url, QUEUE_TYPE, max_detailed[QUEUE_TYPE], specified[QUEUE_TYPE])
        self.get_stats(instance, base_url, NODE_TYPE, max_detailed[NODE_TYPE], specified[NODE_TYPE])


    def _get_data(self, url):
        try:
            data = json.loads(urllib2.urlopen(url).read())
        except urllib2.URLError, e:
            raise Exception('Cannot open RabbitMQ API url: %s %s' % (url, str(e)))
        except ValueError, e:
            raise Exception('Cannot parse JSON response from API url: %s %s' % (url, str(e)))
        return data


    def get_stats(self, instance, base_url, object_type, max_detailed, specified):
        data = self._get_data(urlparse.urljoin(base_url, object_type))

        if len(data) > ALERT_THRESHOLD * max_detailed and not specified:
            self.alert(base_url, max_detailed, len(data), object_type)

        if len(data) > max_detailed and not specified:
            self.warning("Too many queues to fetch. You must choose the queues you are interested in by editing the rabbitmq.yaml configuration file or get in touch with Datadog Support")

        if len(specified) > max_detailed:
            raise Exception("The maximum number of %s you can specify is %d." % (object_type, max_detailed))

        limit_reached = False
        detailed = 0
        for data_line in data:
            name = data_line.get("name")
            absolute_name = name

            if object_type == QUEUE_TYPE:
                absolute_name = '%s/%s' % (data_line.get("vhost"), name)

            if len(data) < max_detailed: 
                # The number of queues or nodes is below the limit. 
                # We can collect detailed metrics for those
                self._get_metrics(data_line, object_type, detailed=True)
                detailed += 1

            elif name in specified:
                # This queue/node is specified in the config
                # We can collect detailed metrics for those
                self._get_metrics(data_line, object_type, detailed=True)
                detailed += 1
                specified.remove(name)

            elif absolute_name in specified:
                # This queue/node is specified in the config
                # We can collect detailed metrics for those
                self._get_metrics(data_line, object_type, detailed=True)
                detailed += 1
                specified.remove(absolute_name)

            elif not limit_reached and not specified:
                # No queues/nodes are specified in the config but we haven't reached the limit yet
                # We can collect detailed metrics for those
                self._get_metrics(data_line, object_type, detailed=True)
                detailed += 1

            limit_reached = detailed >= max_detailed

            if limit_reached or len(data) > max_detailed and not specified:
                self._get_metrics(data_line, object_type, detailed=False)

    def _get_metrics(self, data, object_type, detailed):
        if detailed:
            tags = []
            tag_list = TAGS_MAP[object_type]
            for t in tag_list.keys():
                tag = data.get(t, None)
                if tag is not None:
                    tags.append('rabbitmq_%s:%s' % (tag_list[t], tag))

        for attribute in ATTRIBUTES[object_type]:
            value = data.get(attribute, None)
            if value is not None:
                self.histogram('rabbitmq.%s.%s.hist' % (METRIC_SUFFIX[object_type], attribute), int(value))
                if detailed:
                    self.gauge('rabbitmq.%s.%s' % (METRIC_SUFFIX[object_type], attribute), int(value), tags=tags)

    def alert(self, base_url, max_detailed, size, object_type):
        key = "%s%s" % (base_url, object_type)
        if key in self.already_alerted:
            # We already posted an event
            return

        self.already_alerted.append(key)

        title = "RabbitMQ integration is approaching the limit on %s" % self.hostname
        msg = """%s %s are present. The limit is %s. 
        Please get in touch with Datadog support to increase the limit.""" % (size, object_type, max_detailed)

        event = {
                "timestamp": int(time.time()), 
                "event_type": EVENT_TYPE,
                "api_key": self.agentConfig['api_key'],
                "msg_title": title,
                "msg_text": msg,
                "alert_type": 'warning',
                "source_type_name": SOURCE_TYPE_NAME,
                "host": self.hostname,
                "tags": ["base_url:%s" % base_url, "host:%s" % self.hostname],
                "event_object": key,
            }

        self.event(event)






