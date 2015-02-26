import unittest
import subprocess
import time
import tempfile
import os
import logging
import requests
from util import get_hostname
from tests.common import load_check, kill_subprocess
from nose.plugins.attrib import attr
logging.basicConfig()

MAX_WAIT = 30
HAPROXY_CFG = os.path.realpath(os.path.join(os.path.dirname(__file__), "haproxy.cfg"))
HAPROXY_OPEN_CFG = os.path.realpath(os.path.join(os.path.dirname(__file__), "haproxy-open.cfg"))

@attr(requires='haproxy')
class HaproxyTestCase(unittest.TestCase):
    def _wait(self, url):
        loop = 0
        while True:
            try:
                STATS_URL = ";csv;norefresh"
                auth = ("datadog", "isdevops")
                url = "%s%s" % (url,STATS_URL)

                r = requests.get(url, auth=auth)
                r.raise_for_status()

                break
            except Exception:
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
        except Exception:
            logging.getLogger().exception("Cannot instantiate haproxy")

    def testCheck(self):
        config = {
            'init_config': {},
            'instances': [{
                'url': 'http://localhost:3834/stats',
                'username': 'datadog',
                'password': 'isdevops',
                'status_check': True,
                'collect_aggregates_only': False,
                'tag_service_check_by_host': True,
            }]
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
        service_checks = self.check.get_service_checks()
        assert service_checks
        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(len(service_checks) > 0)

        self.assertEquals(len([t for t in metrics
            if t[0] == "haproxy.backend.bytes.in_rate"]), 3, metrics)
        self.assertEquals(len([t for t in metrics
            if t[0] == "haproxy.frontend.session.current"]), 1, metrics)
        # check was run 2 times
        #       - FRONTEND is reporting OPEN that we ignore
        #       - only the BACKEND aggregate is reporting UP -> OK
        #       - The 3 individual servers are returning no check -> UNKNOWN
        self.assertEquals(len([t for t in service_checks
            if t['status']== 0]), 2, service_checks)
        self.assertEquals(len([t for t in service_checks
            if t['status']== 3]), 6, service_checks)

        # Make sure the service checks aren't tagged with an empty hostname.
        for service_check in service_checks:
            self.assertEquals(service_check['host_name'], get_hostname())

        inst = config['instances'][0]
        data = self.check._fetch_data(inst['url'], inst['username'], inst['password'])
        new_data = [l.replace("no check", "UP") for l in data]
        self.check._process_data(new_data, False, True, inst['url']),

        assert self.check.has_events()
        assert len(self.check.get_events()) == 3 # The 3 individual backend servers were switched to UP
        service_checks = self.check.get_service_checks()
        # The 3 servers + the backend aggregate are reporting UP
        self.assertEquals(len([t for t in service_checks
            if t['status'] == 0]), 4, service_checks)

    def testCountPerStatuses(self):
        try:
            from collections import defaultdict
        except ImportError:
            from compat.defaultdict import defaultdict
        config = { # won't be used but still needs to be valid
            'init_config': {},
            'instances': [{
                'url': 'http://localhost:3834/stats',
                'collect_aggregates_only': False,
            }]
        }
        self.start_server(HAPROXY_OPEN_CFG, config)

        data = """# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,
a,FRONTEND,,,1,2,12,1,11,11,0,0,0,,,,,OPEN,,,,,,,,,1,1,0,,,,0,1,0,2,,,,0,1,0,0,0,0,,1,1,1,,,
a,BACKEND,0,0,0,0,12,0,11,11,0,0,,0,0,0,0,UP,0,0,0,,0,1221810,0,,1,1,0,,0,,1,0,,0,,,,0,0,0,0,0,0,,,,,0,0,
b,FRONTEND,,,1,2,12,11,11,0,0,0,0,,,,,OPEN,,,,,,,,,1,2,0,,,,0,0,0,1,,,,,,,,,,,0,0,0,,,
b,i-1,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-2,0,0,1,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,0,1,0,,1,3,2,,71,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-3,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,BACKEND,0,0,1,2,0,421,1,0,0,0,,0,0,0,0,UP,6,6,0,,0,1,0,,1,3,0,,421,,1,0,,1,,,,,,,,,,,,,,0,0,
""".split('\n')

        # per service
        self.check._process_data(data, True, False, collect_status_metrics=True, collect_status_metrics_by_host=False)

        expected_hosts_statuses = defaultdict(int)
        expected_hosts_statuses[('b', 'OPEN')] = 1
        expected_hosts_statuses[('b', 'UP')] = 3
        expected_hosts_statuses[('a', 'OPEN')] = 1
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        # with collect_aggregates_only set to True
        self.check._process_data(data, True, True, collect_status_metrics=True, collect_status_metrics_by_host=False)
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        # per host
        self.check._process_data(data, True, False, collect_status_metrics=True, collect_status_metrics_by_host=True)
        expected_hosts_statuses = defaultdict(int)
        expected_hosts_statuses[('b', 'FRONTEND', 'OPEN')] = 1
        expected_hosts_statuses[('a', 'FRONTEND', 'OPEN')] = 1
        expected_hosts_statuses[('b', 'i-1', 'UP')] = 1
        expected_hosts_statuses[('b', 'i-2', 'UP')] = 1
        expected_hosts_statuses[('b', 'i-3', 'UP')] = 1
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        self.check._process_data(data, True, True, collect_status_metrics=True, collect_status_metrics_by_host=True)
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

    def testWrongConfig(self):
        # Same check, with wrong data
        config = {
            'init_config': {},
            'instances': [{
                'url': 'http://localhost:3834/stats',
                'username': 'wrong',
                'password': 'isdevops',
                'collect_aggregates_only': False,
            }]
        }
        self.start_server(HAPROXY_CFG, config)

        # Run the check, make sure there are no metrics or events
        try:
            self.check.check(config['instances'][0])
        except Exception:
            pass
        else:
            assert False, "Should raise an error"
        metrics = self.check.get_metrics()
        assert len(metrics) == 0
        assert self.check.has_events() == False

    def testOpenConfig(self):
        # No passwords this time
        config = {
            'init_config': {},
            'instances': [{
                'url': 'http://localhost:3834/stats',
                'collect_aggregates_only': False,
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
            if t[0] == "haproxy.backend.bytes.in_rate"]), 3, metrics)
        self.assertEquals(len([t for t in metrics
            if t[0] == "haproxy.frontend.session.current"]), 1, metrics)

        # Make sure the default case has empty hostnames.
        for service_check in  self.check.get_service_checks():
            self.assertEquals(service_check['host_name'], '')


    def tearDown(self):
        if self.process is not None:
            kill_subprocess(self.process)
        del self.cfg

if __name__ == "__main__":
    unittest.main()

