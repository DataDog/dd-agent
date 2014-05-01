import unittest
import time
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
                        },{
                        "MIB": "TCP-MIB",
                        "symbol": "tcpCurrEstab",
                        "index":"0"
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
        self.assertEqual(len(self.check.device_oids), 2)


    def testSNMPCheck(self):

        self.check = load_check('snmp', self.config, self.agentConfig)

        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        # Assert that there is only the gauge metric because the counter is used
        # as a rate so we don't report with 1 point
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0][0], 'snmp.tcpCurrEstab')

        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rate
        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        self.assertEqual(len(metrics) ,2)
        expected_metrics = ['snmp.udpInDatagrams','snmp.tcpCurrEstab']
        for metric in expected_metrics:
            metric_present=False
            for result in metrics:
                if result[0] == metric:
                    metric_present = True
                    break
            self.assertTrue(metric_present)

if __name__ == "__main__":
    unittest.main()
