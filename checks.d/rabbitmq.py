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
        if not base_url.endswith('/'):
            base_url += '/'
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
            raise Exception('Cannot open RabbitMQ API url: %s %s' % (url, str(e)))
        except ValueError, e:
            self.log.info('Cannot parse JSON response from API url: %s', url)
            raise Exception('Cannot parse JSON response from API url: %s %s' % (url, str(e)))

        for node in stats:
            tags = []
            tag_list = {
                'node':'node',
                'name':'queue',
                'vhost':'vhost',
                'policy':'policy',
            }
            for t in tag_list.keys():
                tag = node.get(t, None)
                if tag is not None:
                    tags.append('rabbitmq_%s:%s' % (tag_list[t], tag))


            for attribute in QUEUE_ATTRIBUTES:
                value = node.get(attribute, None)
                if value is not None:
                    self.gauge('rabbitmq.queue.%s' % attribute, int(value), tags=tags)

    def get_node_stats(self, base_url):
        url = urlparse.urljoin(base_url, 'nodes')
        stats = []
        try:
            stats = json.loads(urllib2.urlopen(url).read())
        except urllib2.URLError, e:
            self.log.info('Cannot open RabbitMQ API url: %s', url)
            raise Exception('Cannot open RabbitMQ API url: %s %s' % (url, str(e)))
        except ValueError, e:
            self.log.info('Cannot parse JSON response from API url: %s', url)
            raise Exception('Cannot parse JSON response from API url: %s %s' % (url, str(e)))

        for node in stats:
            tags = []
            if 'name' in node:
                tags.append('rabbitmq_node:%s' % node['name'])

            for attribute in NODE_ATTRIBUTES:
                value = node.get(attribute, None)
                if value is not None:
                    self.gauge('rabbitmq.node.%s' % attribute, int(value), tags=tags)
