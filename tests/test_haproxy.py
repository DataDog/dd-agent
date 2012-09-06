import unittest
import subprocess
import time
import urllib2
import tempfile
import os
import logging
logging.basicConfig()

from checks.net.haproxy import HAProxyEvents, HAProxyMetrics, get_data, process_data

MAX_WAIT = 30
HAPROXY_CFG = os.path.realpath(os.path.join(os.path.dirname(__file__), "haproxy.cfg"))
HAPROXY_OPEN_CFG = os.path.realpath(os.path.join(os.path.dirname(__file__), "haproxy-open.cfg"))

class HaproxyTestCase(unittest.TestCase):
    def _wait(self, url):
        loop = 0
        while True:
            try:
                STATS_URL = ";csv;norefresh"
                passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
                passman.add_password(None, url, "datadog", "isdevops")
                authhandler = urllib2.HTTPBasicAuthHandler(passman)
                opener = urllib2.build_opener(authhandler)
                urllib2.install_opener(opener)
                url = "%s%s" % (url,STATS_URL)
                req = urllib2.Request(url)
                request = urllib2.urlopen(req)
                break
            except:
                time.sleep(0.5)
                loop+=1
                if loop >= MAX_WAIT:
                    break

    def setUp(self):
        "Don't do anything here since init changes depending on the test"

    def real_setup(self, config_fn):
        self.metrics_check = HAProxyMetrics(logging.getLogger())
        self.events_check = HAProxyEvents(logging.getLogger())

        self.process = None
        try:
            self.cfg = tempfile.NamedTemporaryFile()
            self.cfg.write(open(config_fn).read())
            self.cfg.flush()
            # Start haproxy
            self.process = subprocess.Popen(["haproxy","-d", "-f", self.cfg.name],
                        executable="haproxy",
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)

            # Wait for it to really start
            self._wait("http://localhost:3834/stats")
        except:
            logging.getLogger().exception("Cannot instantiate haproxy")


    def tearDown(self):
        if self.process is not None:
            self.process.terminate()
        del self.cfg

    def testCheckEvents(self):
        self.real_setup(HAPROXY_CFG)
        agentConfig = {
            'haproxy_url': 'http://localhost:3834/stats', 
            'haproxy_user': 'datadog', 
            'haproxy_password':'isdevops',
            'version': '0.1',
            'api_key': 'apikey_2'
        }

        r = self.events_check.check(logging.getLogger(), agentConfig)

        try:
            data = get_data(agentConfig, logging.getLogger())

        except Exception,e:
            logging.getLogger().exception('Unable to get haproxy statistics %s' % e)
            assert(False)

        new_data = []

        for line in data:
            new_data.append(line.replace("OPEN", "DOWN"))

        process_data(self.events_check, agentConfig, new_data)

        self.assertTrue(len(self.events_check.events) == 1)


    def testCheckMetrics(self):
        # Metric check
        self.real_setup(HAPROXY_CFG)
        agentConfig = {
            'haproxy_url': 'http://localhost:3834/stats', 
            'haproxy_user': 'datadog', 
            'haproxy_password':'isdevops',
            'version': '0.1',
            'api_key': 'toto'
        }
        r = self.metrics_check.check(agentConfig)

        #We run it twice as we want to check counter metrics too
        r = self.metrics_check.check(agentConfig)
        self.assertTrue(r)
        self.assertTrue(type(r) == type([]))
        self.assertTrue(len(r) > 0)
        self.assertEquals(len([t for t in r if t[0] == "haproxy.backend.bytes.in_rate"]), 2, r)
        self.assertEquals(len([t for t in r if t[0] == "haproxy.frontend.session.current"]), 1, r)

    def testWrongConfig(self):
        # Same check, with wrong data
        self.real_setup(HAPROXY_CFG)
        agentConfig = {
            'haproxy_url': 'http://localhost:3834/stats',
            'haproxy_user': 'wrong', 
            'haproxy_password':'isdevops',
            'version': '0.1',
            'api_key': 'toto'
        }

        r = self.metrics_check.check(agentConfig)
        self.assertFalse(r)

    def testOpenConfig(self):
        # No passwords this time
        self.real_setup(HAPROXY_OPEN_CFG)
        agentConfig = {
            'haproxy_url': 'http://localhost:3834/stats',
            'version': '0.1',
            'api_key': 'toto'
        }

        # run the check twice to get rates
        self.metrics_check.check(agentConfig)
        r = self.metrics_check.check(agentConfig)
        self.assertTrue(r)
        self.assertTrue(type(r) == type([]))
        self.assertTrue(len(r) > 0)
        self.assertEquals(len([t for t in r if t[0] == "haproxy.backend.bytes.in_rate"]), 2, r)
        self.assertEquals(len([t for t in r if t[0] == "haproxy.frontend.session.current"]), 1, r)

if __name__ == "__main__":
    unittest.main()
