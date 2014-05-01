import unittest
from tests.common import load_check


class TestSNMP(unittest.TestCase):

    def setUp(self):
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.config = {
                "init_config": {
                    "metrics": [{
                        "MIB": "UDP-MIB",
                        "symbol": "udpInDatagrams",
                        "index": "0"
                        }]
                    },
                "instances": [{
                    "ip_address": "localhost",
                    "community_string": "public"
                    }]
                }

    def testInit(self):
        # Initialize the check from checks.d
        self.check = load_check('snmp', self.config, self.agentConfig)
        # Assert the counter state dictionary was initialized
        self.assertTrue(len(self.check.counter_state.keys()) > 0)
        # Assert that some interface got detected on the host
        self.assertTrue(len(self.check.interface_list["localhost"]) > 0)
        # Assert that the device-level metrics is accessible
        self.assertEqual(len(self.check.device_oids), 1)


    def testSNMPCheck(self):

        self.check = load_check('snmp', self.config, self.agentConfig)

        self.check.check(self.config['instances'][0])

        # Metric assertions
        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)

if __name__ == "__main__":
    unittest.main()
