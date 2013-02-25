import unittest
import logging
logger = logging.getLogger(__file__)

from tests.common import get_check

class TestWeb(unittest.TestCase):

    def setUp(self):
        self.apache_config = """
init_config:

instances:
    -   apache_status_url: http://localhost:9444/server-status?auto
        tags:
            - instance:first
    -   apache_status_url: http://localhost:9444/server-status?auto
        tags:
            - instance:second
"""

        self.nginx_config = """
init_config:

instances:
    -   nginx_status_url: http://localhost:44441/nginx_status/
    -   nginx_status_url: http://localhost:44441/nginx_status/
        tags:
            - first_one
    -   nginx_status_url: http://dummyurl:44441/nginx_status/
        tags:
            - dummy
    -   nginx_status_url: http://localhost:44441/nginx_status/
        tags:
            - second
"""

        self.lighttpd_config = """
init_config:

instances:
    -   lighttpd_status_url: http://localhost:9445/server-status?auto
        tags:
            - instance:first
    -   lighttpd_status_url: http://localhost:9445/server-status?auto
        tags:
            - instance:second
"""

    def testApache(self):
        a, instances = get_check('apache', self.apache_config)

        a.check(instances[0])
        metrics = a.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:first'])

        a.check(instances[1])
        metrics = a.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:second'])

    def testApacheOldConfig(self):
        a, _ = get_check('apache', self.apache_config)
        config = {
            'apache_status_url': 'http://example.com/server-status?auto'
        }
        instances = a.parse_agent_config(config)['instances']
        assert instances[0]['apache_status_url'] == config['apache_status_url']

    def testNginx(self):
        nginx, instances = get_check('nginx', self.nginx_config)
        nginx.check(instances[0])
        r = nginx.get_metrics()
        self.assertEquals(len([t for t in r if t[0] == "nginx.net.connections"]), 1, r)

        nginx.check(instances[1])
        r = nginx.get_metrics()
        self.assertEquals(r[0][3].get('tags'), ['first_one'])

    def testNginxOldConfig(self):
        nginx, _ = get_check('nginx', self.nginx_config)
        config = {
            'nginx_status_url_1': 'http://www.example.com/nginx_status:first_tag',
            'nginx_status_url_2': 'http://www.example2.com/nginx_status:8080:second_tag',
            'nginx_status_url_3': 'http://www.example3.com/nginx_status:third_tag'
        }
        instances = nginx.parse_agent_config(config)['instances']
        self.assertEquals(len(instances), 3)
        for i, instance in enumerate(instances):
            assert ':'.join(config.values()[i].split(':')[:-1]) == instance['nginx_status_url']

    def testLighttpd(self):
        l, instances = get_check('lighttpd', self.lighttpd_config)

        l.check(instances[0])
        metrics = l.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:first'])

        l.check(instances[1])
        metrics = l.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:second'])


if __name__ == '__main__':
    unittest.main()