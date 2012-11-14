import unittest
import subprocess
import time
import urllib2
import tempfile
import os
import logging

from checks import gethostname
from tests.common import load_check, kill_subprocess

logging.basicConfig()

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

    def start_server(self, config_fn, config):
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        # Initialize the check from checks.d
        self.check = load_check('haproxy', config, self.agentConfig)

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

<<<<<<< HEAD

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
=======
    def testCheck(self):
        config = {
            'instances': [{
                'url': 'http://localhost:3834/stats',
                'username': 'datadog',
                'password': 'isdevops'
            }]
>>>>>>> checks.d
        }
        self.start_server(HAPROXY_CFG, config)

        # Run the check against our running server
        self.check.check(config['instances'][0])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rates
        self.check.check(config['instances'][0])

        # Metric assertions
        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)

        self.assertEquals(len([t for t in metrics
            if t[0] == "haproxy.backend.bytes.in_rate"]), 2, metrics)
        self.assertEquals(len([t for t in metrics
            if t[0] == "haproxy.frontend.session.current"]), 1, metrics)

        inst = config['instances'][0]
        data = self.check._fetch_data(inst['url'], inst['username'], inst['password'])
        new_data = [l.replace("OPEN", "DOWN") for l in data]

        self.check._process_data(new_data, gethostname(self.agentConfig),
            event_cb=self.check._process_events)

        assert self.check.has_events()
        assert len(self.check.get_events()) == 1

    def testWrongConfig(self):
        # Same check, with wrong data
        config = {
            'instances': [{
                'url': 'http://localhost:3834/stats',
                'username': 'wrong',
                'password': 'isdevops'
            }]
        }
        self.start_server(HAPROXY_CFG, config)

        # Run the check, make sure there are no metrics or events
        self.check.check(config['instances'][0])
        metrics = self.check.get_metrics()
        assert len(metrics) == 0
        assert self.check.has_events() == False

    def testOpenConfig(self):
        # No passwords this time
        config = {
            'instances': [{
                'url': 'http://localhost:3834/stats',
            }]
        }
        self.start_server(HAPROXY_OPEN_CFG, config)

        # Run the check against our running server
        self.check.check(config['instances'][0])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rates
        self.check.check(config['instances'][0])

        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)

        self.assertEquals(len([t for t in metrics
            if t[0] == "haproxy.backend.bytes.in_rate"]), 2, metrics)
        self.assertEquals(len([t for t in metrics
            if t[0] == "haproxy.frontend.session.current"]), 1, metrics)

    def tearDown(self):
        if self.process is not None:
            kill_subprocess(self.process)
        del self.cfg

if __name__ == "__main__":
    unittest.main()
