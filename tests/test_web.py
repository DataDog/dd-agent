import unittest
import logging
logger = logging.getLogger(__file__)

from checks.web import *


class TestWeb(unittest.TestCase):

    def setUp(self):
        self.apache = Apache(logger)
        self.nginx = Nginx(logger)

    def testApache(self):
        pass

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


if __name__ == '__main__':
    unittest.main()
