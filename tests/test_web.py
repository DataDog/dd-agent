import unittest
import logging
logging.basicConfig()
logger = logging.getLogger()

from checks.web import *
import urllib2

class TestWeb(unittest.TestCase):

    def setUp(self):
        self.apache = Apache(logger)
        self.nginx = Nginx(logger)

    def testApache(self):
        results = self.apache.check({"apacheStatusUrl": "apache", "version": "test"})
        self.assertEquals(results["apacheBusyWorkers"], 1.0)
        self.assertEquals(results["apacheIdleWorkers"], 15.0)
        self.assertEquals(results["apacheTotalAccesses"], 456.0)
        self.assertEquals(results["apacheUptime"], 3.0)
        self.assertEquals(results["apacheCPULoad"], 0.00817439)
        self.assertEquals(results["apacheTotalBytes"], 12345 * 1024.0)
        
    def testNginx(self):
        results = self.nginx.check({"nginxStatusUrl": "nginx", "version": "test"})
        self.assertEquals(results["nginxConnections"], 8.0)
        self.assertEquals(results["nginxReading"], 0.0)
        self.assertEquals(results["nginxWriting"], 1.0)
        self.assertEquals(results["nginxWaiting"], 7.0)
        
if __name__ == '__main__':
    unittest.main()
