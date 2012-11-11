import unittest
import logging
logger = logging.getLogger(__file__)

from tests.common import get_check
from checks.web import *


class TestWeb(unittest.TestCase):

    def setUp(self):
        self.nginx = Nginx(logger)
        self.apache_config = """
init_config:

instances:
    -   apache_status_url: http://localhost:9444/server-status?auto
"""

    def testApache(self):
        a, instances = get_check('apache', self.apache_config)
        a.check(instances[0])
        metrics = a.get_metrics()
        metric_names = [m[0] for m in metrics]

        for name in a.METRIC_TRANSLATION.values():
            assert name in metric_names, '%s not found' % (name)


    def testNginx(self):
        config = { "nginx_status_url": "http://localhost:44441/nginx_status/", 
                    "nginx_status_url_1": "http://localhost:44441/nginx_status/:first_one",
                    "nginx_status_url_2": "http://dummyurl:44441/nginx_status/:dummy",
                    "nginx_status_url_3": "http://localhost:44441/nginx_status/:second",
                'version': '0.1',
                'api_key': 'toto'
        }
        self.nginx.check(config)
        r = self.nginx.check(config)

        self.assertEquals(len([t for t in r if t[0] == "nginx.net.connections"]), 3, r)
        self.assertEquals(len([t for t in r if t[3].get('tags') == ["instance:second"]]), 5, r)


if __name__ == '__main__':
    unittest.main()