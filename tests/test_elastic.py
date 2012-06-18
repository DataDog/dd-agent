import unittest
import logging
logging.basicConfig()
import subprocess
import time
import urllib2

from checks.db.elastic import ElasticSearch

PORT = 9200
MAX_WAIT = 150

class TestElastic(unittest.TestCase):

    def _wait(self, url):
        loop = 0
        while True:
            try:
                req = urllib2.Request(url, None)
                request = urllib2.urlopen(req)
                break
            except:
                time.sleep(0.5)
                loop = loop + 1
                if loop >= MAX_WAIT:
                    break              

    def setUp(self):
        self.c = ElasticSearch(logging.getLogger())
        try:
            # Start elasticsearch
            self.process = subprocess.Popen(["elasticsearch","-f","elasticsearch"],
                        executable="elasticsearch",
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)

            # Wait for it to really start
            self._wait("http://localhost:%s" % PORT)
        except:
            logging.getLogger().exception("Cannot instatiate elasticsearch")

    def tearDown(self):
        try:
            if "process" in dir(self):
                self.process.terminate()
        except:
            logging.getLogger().exception("Could not terminate elasticsearch")

    def testCheck(self):

        agentConfig = { 'elasticsearch': 'http://localhost:%s' % PORT,
                      'version': '0.1',
                      'apiKey': 'toto' }

        r = self.c.check(agentConfig)
        self.assertTrue(type(r) == type([]))
        self.assertTrue(len(r) > 0)

if __name__ == "__main__":
    unittest.main()
