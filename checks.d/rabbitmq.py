import urllib2
import urlparse

from checks import AgentCheck
from util import json


class RabbitMQ(AgentCheck):
    """This check is for gathering statistics from the RabbitMQ
    Management Plugin (http://www.rabbitmq.com/management.html)
    """
    def check(self, instance):
        # make sure 'rabbitmq_api_url; is present
        if 'rabbitmq_api_url' not in instance:
            self.log.info('Skipping instance "rabbitmq_api_url" not found')
            return

        # get parameters
        base_url = instance['rabbitmq_api_url']
        username = instance.get('rabbitmq_user', 'guest')
        password = instance.get('rabbitmq_pass', 'guest')

        # setup urllib2 for Basic Auth
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(realm='RabbitMQ Management', uri=base_url, user=username, passwd=password)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        self.get_queue_stats(base_url)
        self.get_node_stats(base_url)

    def get_queue_stats(self, base_url):
        url = urlparse.urljoin(base_url, 'queues')
        stats = []
        try:
            stats = json.loads(urllib2.urlopen(url).read())
        except urllib2.URLError, e:
            self.log.info('Cannot open RabbitMQ API url: %s', url)
        except ValueError, e:
            self.log.info('Cannot parse JSON response from API url: %s', url)

        for node in stats:
            tags = []
            tags.append('rabbitmq_node:%s' % node['node'])
            tags.append('rabbitmq_queue:%s' % node['name'])
            tags.append('rabbitmq_vhost:%s' % node['vhost'])
            tags.append('rabbitmq_policy:%s' % node['policy'])

            self.gauge('rabbitmq.queue.active_consumers', int(node['active_consumers']), tags=tags)
            self.gauge('rabbitmq.queue.consumers', int(node['consumers']), tags=tags)
            self.gauge('rabbitmq.queue.memory', int(node['memory']), tags=tags)
            self.gauge('rabbitmq.queue.messages', int(node['messages']), tags=tags)
            self.gauge('rabbitmq.queue.messages_ready', int(node['messages_ready']), tags=tags)
            self.gauge('rabbitmq.queue.messages_unacknowledged', int(node['messages_unacknowledged']), tags=tags)

    def get_node_stats(self, base_url):
        url = urlparse.urljoin(base_url, 'nodes')
        stats = []
        try:
            stats = json.loads(urllib2.urlopen(url).read())
        except urllib2.URLError, e:
            self.log.info('Cannot open RabbitMQ API url: %s', url)
        except ValueError, e:
            self.log.info('Cannot parse JSON response from API url: %s', url)

        for node in stats:
            tags = []
            tags.append('rabbitmq_node:%s' % node['name'])

            self.gauge('rabbitmq.node.disk_free', int(node['disk_free']), tags=tags)
            self.gauge('rabbitmq.node.disk_free_limit', int(node['disk_free_limit']), tags=tags)
            self.gauge('rabbitmq.node.fd_total', int(node['fd_total']), tags=tags)
            self.gauge('rabbitmq.node.fd_used', int(node['fd_used']), tags=tags)
            self.gauge('rabbitmq.node.mem_limit', int(node['mem_limit']), tags=tags)
            self.gauge('rabbitmq.node.mem_used', int(node['mem_used']), tags=tags)
            self.gauge('rabbitmq.node.proc_total', int(node['proc_total']), tags=tags)
            self.gauge('rabbitmq.node.proc_used', int(node['proc_used']), tags=tags)
            self.gauge('rabbitmq.node.processors', int(node['processors']), tags=tags)
            self.gauge('rabbitmq.node.run_queue', int(node['run_queue']), tags=tags)
            self.gauge('rabbitmq.node.sockets_total', int(node['sockets_total']), tags=tags)
            self.gauge('rabbitmq.node.sockets_used', int(node['sockets_used']), tags=tags)
