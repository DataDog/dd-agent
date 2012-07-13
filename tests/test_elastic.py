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
        self.process = None
        try:
            # Start elasticsearch
            self.process = subprocess.Popen(["elasticsearch","-f","elasticsearch"],
                        executable="elasticsearch",
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)

            # Wait for it to really start
            self._wait("http://localhost:%s" % PORT)
        except:
            logging.getLogger().exception("Cannot instantiate elasticsearch")

    def tearDown(self):
        if self.process is not None:
            self.process.terminate()

    def testCheck(self):
        agentConfig = { 'elasticsearch': 'http://localhost:%s/_cluster/nodes/stats?all=true' % PORT,
                      'version': '0.1',
                      'apiKey': 'toto' }

        r = self.c.check(agentConfig)
        def _check(slf, r):
            slf.assertTrue(type(r) == type([]))
            slf.assertTrue(len(r) > 0)
            slf.assertEquals(len([t for t in r if t[0] == "elasticsearch.get.total"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "elasticsearch.search.fetch.total"]), 1, r)
        _check(self, r)

        # Same check, only given hostname
        agentConfig = { 'elasticsearch': 'http://localhost:%s' % PORT,
                      'version': '0.1',
                      'apiKey': 'toto' }

        r = self.c.check(agentConfig)
        _check(self, r)

        # Same check, only given hostname
        agentConfig = { 'elasticsearch': 'http://localhost:%s/wrong_url' % PORT,
                      'version': '0.1',
                      'apiKey': 'toto' }

        r = self.c.check(agentConfig)
        self.assertFalse(r)
        

if __name__ == "__main__":
    unittest.main()
