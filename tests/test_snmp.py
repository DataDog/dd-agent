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
                    'mibs_folder':'/etc/mibs'
                    },
                "instances": [{
                    "ip_address": "192.168.34.10",
                    "port":161,
                    "community_string": "public",
                    "metrics": [{
                        "OID": "1.3.6.1.2.1.7.1.0", # Counter (needlessly specify the index)
                        "name": "udpDatagrams"
                        },{
                        "OID": "1.3.6.1.2.1.6.10", # Counter
                        "name": "tcpInSegs"
                        },{
                        "MIB": "TCP-MIB",          # Gauge
                        "symbol": "tcpCurrEstab",
                        }]
                    }]
                }

    def testInit(self):
        # Initialize the check from checks.d
        self.check = load_check('snmp', self.config, self.agentConfig)

        mib_folders = self.check.cmd_generator.snmpEngine.msgAndPduDsp\
                .mibInstrumController.mibBuilder.getMibSources()
        custom_folder_represented = False
        for folder in mib_folders:
            if '/etc/mibs' == folder.fullPath():
                custom_folder_represented = True
                break
        self.assertTrue(custom_folder_represented)

    def testSNMPCheck(self):

        self.check = load_check('snmp', self.config, self.agentConfig)

        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        # Assert that there is only the gauge metric because the counters are
        # used as rate so we don't report them with 1 point
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0][0], 'snmp.tcpCurrEstab')

        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rate
        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        self.assertEqual(len(metrics) ,3)
        expected_metrics = ['snmp.udpDatagrams', 'snmp.tcpCurrEstab', 'snmp.tcpInSegs']
        for metric in expected_metrics:
            for result in metrics:
                if result[0] == metric:
                    break
            else:
                self.fail("Missing metric: %s" % metric)

if __name__ == "__main__":
    unittest.main()
