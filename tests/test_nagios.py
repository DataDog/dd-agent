import unittest
import logging; logger = logging.getLogger(__file__)
import os
import tempfile

from tests.common import load_check

NAGIOS_TEST_LOG = os.path.join(os.path.dirname(__file__), "nagios.log")

class TestNagios(unittest.TestCase):

    def _setupAgentCheck(self, path_to_log):
        self.nagios_cfg = tempfile.NamedTemporaryFile(mode="a+b")
        self.nagios_cfg.write('\n'.join(["log_file={0}".format(path_to_log)]))
        self.nagios_cfg.flush()
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
                }
        self.config = {
                'init_config' : {},
                'instances': [{
                    'nagios_conf': self.nagios_cfg.name,
                    'events': True
                    }]
                }
        self.check = load_check('nagios', self.config, self.agentConfig)

    def testParseLine(self):
        """Test line parser"""
        self._setupAgentCheck(NAGIOS_TEST_LOG)
        nagios_tailer = self.check.nagios_tails[self.nagios_cfg.name][0]
        counters = {}

        for line in open(NAGIOS_TEST_LOG).readlines():
            parsed = nagios_tailer._parse_line(line)
            if parsed:
                event = self.check.get_events()[-1]
                t = event["event_type"]
                assert t in line
                assert int(event["timestamp"]) > 0, line
                assert event["host"] is not None, line
                counters[t] = counters.get(t, 0) + 1

                if t == "SERVICE ALERT":
                    assert event["event_soft_hard"] in ("SOFT", "HARD"), line
                    assert event["event_state"] in ("CRITICAL", "WARNING", "UNKNOWN", "OK"), line
                    assert event["check_name"] is not None
                elif t == "SERVICE NOTIFICATION":
                    assert event["event_state"] in ("ACKNOWLEDGEMENT", "OK", "CRITICAL", "WARNING", "ACKNOWLEDGEMENT (CRITICAL)"), line
                elif t == "SERVICE FLAPPING ALERT":
                    assert event["flap_start_stop"] in ("STARTED", "STOPPED"), line
                    assert event["check_name"] is not None
                elif t == "ACKNOWLEDGE_SVC_PROBLEM":
                    assert event["check_name"] is not None
                    assert event["ack_author"] is not None
                    assert int(event["sticky_ack"]) >= 0
                    assert int(event["notify_ack"]) >= 0
                elif t == "ACKNOWLEDGE_HOST_PROBLEM":
                    assert event["ack_author"] is not None
                    assert int(event["sticky_ack"]) >= 0
                    assert int(event["notify_ack"]) >= 0
                elif t == "HOST DOWNTIME ALERT":
                    assert event["host"] is not None
                    assert event["downtime_start_stop"] in ("STARTED", "STOPPED")

        self.assertEquals(counters["SERVICE ALERT"], 301)
        self.assertEquals(counters["SERVICE NOTIFICATION"], 120)
        self.assertEquals(counters["HOST ALERT"], 3)
        self.assertEquals(counters["SERVICE FLAPPING ALERT"], 7)
        self.assertEquals(counters["CURRENT HOST STATE"], 8)
        self.assertEquals(counters["CURRENT SERVICE STATE"], 52)
        self.assertEquals(counters["SERVICE DOWNTIME ALERT"], 3)
        self.assertEquals(counters["HOST DOWNTIME ALERT"], 5)
        self.assertEquals(counters["ACKNOWLEDGE_SVC_PROBLEM"], 4)
        assert "ACKNOWLEDGE_HOST_PROBLEM" not in counters

    def testContinuousBulkParsing(self):
        """Make sure the tailer continues to parse nagios as the file grows"""
        x = open(NAGIOS_TEST_LOG).read()
        events = []
        ITERATIONS = 10
        f = tempfile.NamedTemporaryFile(mode="a+b")
        f.write(x)
        f.flush()
        self._setupAgentCheck(f.name)
        self.check.check(self.config['instances'][0])

        # Make sure that the lines before we start the agent are ignored
        self.assertEquals(len(self.check.get_events()), 0)
        for i in range(ITERATIONS):
            f.write(x)
            f.flush()
            self.check.check(self.config['instances'][0])
            events.extend(self.check.get_events())
        f.close()
        self.assertEquals(len(events), ITERATIONS * 503)
            

if __name__ == '__main__':
    unittest.main()