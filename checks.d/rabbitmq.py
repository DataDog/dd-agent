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
                'fd_used',
                'mem_used',
                'run_queue',
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

        for object_type, specified_objects in specified.iteritems():
            if type(specified_objects) != list:
                raise TypeError("%s parameter must be a list" % object_type)

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


    def get_stats(self, instance, base_url, object_type, max_detailed, specified_list):
        """
        instance: the check instance
        base_url: the url of the rabbitmq management api (e.g. http://localhost:15672/api)
        object_type: either QUEUE_TYPE or NODE_TYPE
        max_detailed: the limit of objects to collect for this type
        specified_list: a list of specified queues or nodes (specified in the yaml file)
        """

        data = self._get_data(urlparse.urljoin(base_url, object_type))
        specified_items = list(specified_list) # Make a copy of this list as we will remove items from it at each iteration

        """ data is a list of nodes or queues:
        data = [
            {'status': 'running', 'node': 'rabbit@host', 'name': 'queue1', 'consumers': 0, 'vhost': '/', 'backing_queue_status': {'q1': 0, 'q3': 0, 'q2': 0, 'q4': 0, 'avg_ack_egress_rate': 0.0, 'ram_msg_count': 0, 'ram_ack_count': 0, 'len': 0, 'persistent_count': 0, 'target_ram_count': 'infinity', 'next_seq_id': 0, 'delta': ['delta', 'undefined', 0, 'undefined'], 'pending_acks': 0, 'avg_ack_ingress_rate': 0.0, 'avg_egress_rate': 0.0, 'avg_ingress_rate': 0.0}, 'durable': True, 'idle_since': '2013-10-03 13:38:18', 'exclusive_consumer_tag': '', 'arguments': {}, 'memory': 10956, 'policy': '', 'auto_delete': False}, 
            {'status': 'running', 'node': 'rabbit@host, 'name': 'queue10', 'consumers': 0, 'vhost': '/', 'backing_queue_status': {'q1': 0, 'q3': 0, 'q2': 0, 'q4': 0, 'avg_ack_egress_rate': 0.0, 'ram_msg_count': 0, 'ram_ack_count': 0, 'len': 0, 'persistent_count': 0, 'target_ram_count': 'infinity', 'next_seq_id': 0, 'delta': ['delta', 'undefined', 0, 'undefined'], 'pending_acks': 0, 'avg_ack_ingress_rate': 0.0, 'avg_egress_rate': 0.0, 'avg_ingress_rate': 0.0}, 'durable': True, 'idle_since': '2013-10-03 13:38:18', 'exclusive_consumer_tag': '', 'arguments': {}, 'memory': 10956, 'policy': '', 'auto_delete': False}, 
            {'status': 'running', 'node': 'rabbit@host', 'name': 'queue11', 'consumers': 0, 'vhost': '/', 'backing_queue_status': {'q1': 0, 'q3': 0, 'q2': 0, 'q4': 0, 'avg_ack_egress_rate': 0.0, 'ram_msg_count': 0, 'ram_ack_count': 0, 'len': 0, 'persistent_count': 0, 'target_ram_count': 'infinity', 'next_seq_id': 0, 'delta': ['delta', 'undefined', 0, 'undefined'], 'pending_acks': 0, 'avg_ack_ingress_rate': 0.0, 'avg_egress_rate': 0.0, 'avg_ingress_rate': 0.0}, 'durable': True, 'idle_since': '2013-10-03 13:38:18', 'exclusive_consumer_tag': '', 'arguments': {}, 'memory': 10956, 'policy': '', 'auto_delete': False}, 
            ...
        ]
        """
        if len(specified_items) > max_detailed:
            raise Exception("The maximum number of %s you can specify is %d." % (object_type, max_detailed))

        if specified_items is not None and len(specified_items) > 0: # a list of queues/nodes is specified. We process only those
            if object_type == NODE_TYPE:
                for data_line in data:
                    name = data_line.get("name")
                    if name in specified_items:
                        self._get_metrics(data_line, object_type)
                        specified_items.remove(name)

            else: # object_type == QUEUE_TYPE
                for data_line in data:
                    name = data_line.get("name")
                    absolute_name = '%s/%s' % (data_line.get("vhost"), name)
                    if name in specified_items:
                        self._get_metrics(data_line, object_type)
                        specified_items.remove(name)
                    elif absolute_name in specified_items:
                        self._get_metrics(data_line, object_type)
                        specified_items.remove(absolute_name)

        else: # No queues/node are specified. We will process every queue/node if it's under the limit
            if len(data) > ALERT_THRESHOLD * max_detailed:
                # Post a message on the dogweb stream to warn
                self.alert(base_url, max_detailed, len(data), object_type)

            if len(data) > max_detailed:
                # Display a warning in the info page
                self.warning("Too many queues to fetch. You must choose the %s you are interested in by editing the rabbitmq.yaml configuration file or get in touch with Datadog Support" % object_type)

            for data_line in data[:max_detailed]:
                # We truncate the list of nodes/queues if it's above the limit
                self._get_metrics(data_line, object_type)


    def _get_metrics(self, data, object_type):
        tags = []
        tag_list = TAGS_MAP[object_type]
        for t in tag_list.keys():
            tag = data.get(t, None)
            if tag is not None:
                tags.append('rabbitmq_%s:%s' % (tag_list[t], tag))

        for attribute in ATTRIBUTES[object_type]:
            value = data.get(attribute, None)
            if value is not None:
                try:
                    self.gauge('rabbitmq.%s.%s' % (METRIC_SUFFIX[object_type], attribute), float(value), tags=tags)
                except ValueError:
                    self.log.debug("Caught ValueError for %s %s = %s  with tags: %s" % (METRIC_SUFFIX[object_type], attribute, value, tags))

    def alert(self, base_url, max_detailed, size, object_type):
        key = "%s%s" % (base_url, object_type)
        if key in self.already_alerted:
            # We have already posted an event
            return

        self.already_alerted.append(key)

        title = "RabbitMQ integration is approaching the limit on the number of %s that can be collected from on %s" % (object_type, self.hostname)
        msg = """%s %s are present. The limit is %s. 
        Please get in touch with Datadog support to increase the limit.""" % (size, object_type, max_detailed)

        event = {
                "timestamp": int(time.time()), 
                "event_type": EVENT_TYPE,
                "msg_title": title,
                "msg_text": msg,
                "alert_type": 'warning',
                "source_type_name": SOURCE_TYPE_NAME,
                "host": self.hostname,
                "tags": ["base_url:%s" % base_url, "host:%s" % self.hostname],
                "event_object": "rabbitmq.limit.%s" % object_type,
            }

        self.event(event)
