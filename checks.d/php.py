import re
import time
import urllib2

from util import headers
from checks import AgentCheck

class Php(AgentCheck):
    """Tracks basic php-fpm metrics via the status module
    * accepted conn
    * listen queue
    * max listen queue
    * listen queue len
    * idle processes
    * active processes
    * total processes
    * max active processes
    * max children reached
    * slow requests

    Requires php-fpm pools to have the status option.
    See http://www.php.net/manual/de/install.fpm.configuration.php#pm.status-path for more details

    """
    def check(self, instance):
        if 'php_status_url' not in instance:
            raise Exception('php instance missing "php_status_url" value.')
        tags = instance.get('tags', [])

        self._get_metrics(instance['php_status_url'], tags)

    def _get_metrics(self, url, tags):
        req = urllib2.Request(url, None, headers(self.agentConfig))
        request = urllib2.urlopen(req)
        response = request.read()

        # accepted conn
        parsed = re.search(r'accepted conn:\s+(\d+)', response)
        if parsed:
            accepted_conn = int(parsed.group(1))
            self.increment("php.accepted_conn", accepted_conn, tags=tags)

        # listen queue
        parsed = re.search(r'listen queue:\s+(\d+)', response)
        if parsed:
            listen_queue = int(parsed.group(1))
            self.gauge("php.listen_queue", listen_queue, tags=tags)

        # max listen queue
        parsed = re.search(r'max listen queue:\s+(\d+)', response)
        if parsed:
            max_listen_queue = int(parsed.group(1))
            self.gauge("php.max_listen_queue", max_listen_queue, tags=tags)

        # listen queue len
        parsed = re.search(r'listen queue len:\s+(\d+)', response)
        if parsed:
            listen_queue_len = int(parsed.group(1))
            self.gauge("php.listen_queue_len", listen_queue_len, tags=tags)

        # idle processes
        parsed = re.search(r'idle processes:\s+(\d+)', response)
        if parsed:
            idle_processes = int(parsed.group(1))
            self.gauge("php.idle_processes", idle_processes, tags=tags)

        # active processes
        parsed = re.search(r'active processes:\s+(\d+)', response)
        if parsed:
            active_processes = int(parsed.group(1))
            self.gauge("php.active_processes", active_processes, tags=tags)

        # total processes
        parsed = re.search(r'total processes:\s+(\d+)', response)
        if parsed:
            total_processes = int(parsed.group(1))
            self.gauge("php.total_processes", total_processes, tags=tags)

        # max active processes
        parsed = re.search(r'max active processes:\s+(\d+)', response)
        if parsed:
            max_active_processes = int(parsed.group(1))
            self.gauge("php.max_active_processes", max_active_processes, tags=tags)

        # max children reached
        parsed = re.search(r'max children reached:\s+(\d+)', response)
        if parsed:
            max_children_reached = int(parsed.group(1))
            self.gauge("php.max_children_reached", max_children_reached, tags=tags)

        # slow requests
        parsed = re.search(r'slow requests:\s+(\d+)', response)
        if parsed:
            slow_requests = int(parsed.group(1))
            self.increment("php.slow_requests", slow_requests, tags=tags)

    @staticmethod
    def parse_agent_config(agentConfig):
        instances = []

        # Try loading from the very old format
        php_url = agentConfig.get("php_status_url", None)
        if php_url is not None:
            instances.append({
                'php_status_url': php_url
            })

        # Try the older multi-instance style
        # php_status_url_1: http://www.example.com/php_status:first_tag
        # php_status_url_2: http://www.example2.com/php_status:8080:second_tag
        # php_status_url_2: http://www.example3.com/php_status:third_tag
        def load_conf(index=1):
            instance = agentConfig.get("php_status_url_%s" % index, None)
            if instance is not None:
                instance = instance.split(":")
                instances.append({
                    'php_status_url': ":".join(instance[:-1]),
                    'tags': ['instance:%s' % instance[-1]]
                })
                load_conf(index+1)

        load_conf()

        if not instances:
            return False

        return {
            'instances': instances
        }
