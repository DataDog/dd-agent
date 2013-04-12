import unittest
import os
import tempfile

from tests.common import load_check

NAGIOS_TEST_LOG = os.path.join(os.path.dirname(__file__), "nagios.log")


class TestNagios(unittest.TestCase):
    def setUp(self):
        self.agentConfig = {
            'api_key': '123'
        }

        # Initialize the check from checks.d
        self.check = load_check('nagios', {'init_config': {}, 'instances': {}}, self.agentConfig)

    def testParseLine(self):
        """Test line parser"""
        self.check.event_count = 0
        counters = {}

        for line in open(NAGIOS_TEST_LOG).readlines():
            parsed = self.check._parse_line(line)
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
        new_conf = self.check.parse_agent_config({"nagios_log": f.name})

        # Open the file for an initial determination of position
        self.check.check(new_conf['instances'][0])
        for i in range(ITERATIONS):
            f.write(x)
            f.flush()
            self.check.check(new_conf['instances'][0])
            events.extend(self.check.get_events())
            if i == 0:
                assert len([e for e in events if e["api_key"] == "123"]) > 500, "Missing api-keys in events"
        f.close()
        self.assertEquals(len(events), ITERATIONS * 503)

    def testMultiInstance(self):
        """Make sure the check can handle multiple instances"""
        x = open(NAGIOS_TEST_LOG).readlines()
        f = tempfile.NamedTemporaryFile(mode="a+b")
        f2 = tempfile.NamedTemporaryFile(mode="a+b")

        files = [f, f2]

        instances = [
            {'log_file': f.name},
            {'log_file': f2.name}
        ]

        for index, instance in enumerate(instances):
            cur_file = files[index]
            # Open the file for an initial determination of position
            self.check.check(instance)
            for i in range(index):
                cur_file.writelines(x)
            cur_file.flush()
            self.check.check(instance)
            events = self.check.get_events()
            assert len(events) == 503 * index

        f.close()
        f2.close()


if __name__ == '__main__':
    unittest.main()
