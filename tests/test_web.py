import unittest
import logging
logger = logging.getLogger(__file__)

from checks.web import *

NGINX_CONF = os.path.realpath(os.path.join(os.path.dirname(__file__), "nginx.conf"))

class TestWeb(unittest.TestCase):

    def setUp(self):
        self.apache = Apache(logger)
        self.nginx = Nginx(logger)
        try:
            self.conf = tempfile.NamedTemporaryFile()
            self.conf.write(open(NGINX_CONF).read())
            self.flush()

    def testApache(self):
        pass

    def testNginx(self):
        config = { "nginx_status_url": "http://localhost/nginx_status/", 
                    "nginx_status_url_1": "http://localhost/nginx_status/:first_one",
                    "nginx_status_url_2": "http://localhost/nginx_status/:dummy",
                    "nginx_status_url_3": "http://localhost/nginx_status/:second",
                'version': '0.1',
                'api_key': 'toto'
        }
        self.nginx.check(config)
        r = self.nginx.check(config)

        self.assertEquals(len([t for t in r if t[0] == "nginx.net.connections"]), 3, r)


if __name__ == '__main__':
    unittest.main()
