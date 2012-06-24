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
        pass

if __name__ == '__main__':
    unittest.main()
