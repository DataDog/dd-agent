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
        self.assertGreater(self.check.counter_state.keys(), 0)
        self.assertGreater(self.check.interface_list.keys(), 0)

if __name__ == "__main__":
    unittest.main()
