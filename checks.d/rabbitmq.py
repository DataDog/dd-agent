import urllib2
import urlparse

from checks import AgentCheck
from util import json

QUEUE_ATTRIBUTES = [
        'active_consumers',
        'consumers',
        'memory',
        'messages',
        'messages_ready',
        'messages_unacknowledged'
    ]

NODE_ATTRIBUTES = [
                'disk_free',
                'disk_free_limit',
                'fd_total',
                'fd_used',
                'mem_limit',
                'mem_used',
                'proc_total',
                'proc_used',
                'processors',
                'run_queue',
                'sockets_total',
                'sockets_used',
    ]

MAX_QUEUES = 5
MAX_NODES = 3

QUEUE_LIMIT = 100
NODE_LIMIT = 100

class RabbitMQ(AgentCheck):
    """This check is for gathering statistics from the RabbitMQ
    Management Plugin (http://www.rabbitmq.com/management.html)
    """
    def check(self, instance):
        # make sure 'rabbitmq_api_url; is present
        if 'rabbitmq_api_url' not in instance:
            raise Exception('Missing "rabbitmq_api_url" in RabbitMQ config.')

        # get parameters
        base_url = instance['rabbitmq_api_url']
        if not base_url.endswith('/'):
            base_url += '/'
        username = instance.get('rabbitmq_user', 'guest')
        password = instance.get('rabbitmq_pass', 'guest')

        # setup urllib2 for Basic Auth
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(realm='RabbitMQ Management', uri=base_url, user=username, passwd=password)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        self.get_queue_stats(instance, base_url)
        self.get_node_stats(instance, base_url)

    def _get_data(self, url):
        try:
            data = json.loads(urllib2.urlopen(url).read())
        except urllib2.URLError, e:
            raise Exception('Cannot open RabbitMQ API url: %s %s' % (url, str(e)))
        except ValueError, e:
            raise Exception('Cannot parse JSON response from API url: %s %s' % (url, str(e)))
        return data


    def _get_metrics_for_queue(self, queue, is_gauge=False, send_histogram=True):
        if is_gauge:
            tags = []
            tag_list = {
                'node':'node',
                'name':'queue',
                'vhost':'vhost',
                'policy':'policy',
            }
            for t in tag_list.keys():
                tag = queue.get(t, None)
                if tag is not None:
                    tags.append('rabbitmq_%s:%s' % (tag_list[t], tag))

        else:
            tags = None

        for attribute in QUEUE_ATTRIBUTES:
            value = queue.get(attribute, None)
            if value is not None:
                if send_histogram:
                    self.histogram('rabbitmq.queue.%s.hist' % attribute, int(value))
                if is_gauge:
                    self.gauge('rabbitmq.queue.%s' % attribute, int(value), tags=tags)
                    

    def _get_metrics_for_node(self, node, is_gauge=False, send_histogram=True):
        if is_gauge:
            tags = []
            if 'name' in node:
                tags.append('rabbitmq_node:%s' % node['name'])

        for attribute in NODE_ATTRIBUTES:
            value = node.get(attribute, None)
            if value is not None:
                if send_histogram:
                    self.histogram('rabbitmq.node.%s.hist' % attribute, int(value))
                if is_gauge:
                    self.gauge('rabbitmq.node.%s' % attribute, int(value), tags=tags)


    def get_queue_stats(self, instance, base_url):
        url = urlparse.urljoin(base_url, 'queues')
        queues = self._get_data(url)

        if len(queues) > 100 and not instance.get('queues', None):
            self.warning("Too many queues to fetch. You must choose the queues you are interested in by editing the rabbitmq.yaml configuration file")

        allowed_queues = instance.get('queues', [])
        if len(allowed_queues) > MAX_QUEUES:
            raise Exception("The maximum number of queues you can specify is %d." % MAX_QUEUES)

        if not allowed_queues:
            allowed_queues = [q.get('name') for q in queues[:MAX_QUEUES]]
            # If no queues are specified in the config, we only get metrics for the 5 first ones.
            # Others will be aggregated

        i = 0
        queue_Limit_reached = False
        for queue in queues:
            name = queue.get('name')
            if name in allowed_queues:
                self._get_metrics_for_queue(queue, is_gauge=True, send_histogram=len(queues) > MAX_QUEUES)
                allowed_queues.remove(name)
            elif queue_Limit_reached:
                if not allowed_queues:
                    # We have reached the limit and we have already processed the config specified queues
                    break
                # We have reached the limit but some queues specified in the config still haven't been processed
                continue
            else:
                self._get_metrics_for_queue(queue)

            i += 1
            if i > QUEUE_LIMIT:
                self.warning("More than %s queues are present. Only collecting data using the 100 first" % QUEUE_LIMIT)
                queue_Limit_reached = True
                

    def get_node_stats(self, instance, base_url):
        url = urlparse.urljoin(base_url, 'nodes')
        nodes = self._get_data(url)

        if len(nodes) > 100 and not instance.get('nodes', None):
            self.warning("Too many queues to fetch. You must choose the queues you are interested in by editing the rabbitmq.yaml configuration file")

        allowed_nodes = instance.get('nodes', [])
        if len(allowed_nodes) > MAX_NODES:
            raise Exception("The maximum number of nodes you can specify is %d." % MAX_NODES)

        if not allowed_nodes:
            allowed_nodes = [n.get('name') for n in nodes[:MAX_NODES]]
            # If no nodes are specified in the config, we only get metrics for the 5 first ones.
            # Others will be aggregated

        i = 0
        node_limit_reached = False
        for node in nodes:
            name = node.get('name')
            if name in allowed_nodes:
                self._get_metrics_for_node(node, is_gauge=True, send_histogram=len(nodes) > MAX_NODES)
                allowed_nodes.remove(name)
            elif node_limit_reached:
                if not allowed_nodes:
                    # We have reached the limit and we have already processed the config specified nodes
                    break
                # We have reached the limit but some nodes specified in the config still haven't been processed
                continue
            else:
                self._get_metrics_for_node(node)

            i += 1
            if i > NODE_LIMIT:
                self.warning("More than %s nodes are present. Only collecting data using the 100 first" % NODE_LIMIT)
                node_limit_reached = True
