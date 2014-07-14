import unittest
import time
from tests.common import load_check

# This test is dependent of having a fully open snmpd responding at localhost:161
# with an authentication by the Community String "public"
# This setup should normally be handled by the .travis.yml file, look there if
# you want to see how to run these tests locally

class TestSNMP(unittest.TestCase):

    def setUp(self):
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

    def testInit(self):
        self.config = {
                "init_config": {
                    'mibs_folder':'/etc/mibs'
                    }
                }
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

    def test_scalar_SNMPCheck(self):
        self.config = {
                "instances": [{
                    "ip_address": "localhost",
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

    def test_table_SNMPCheck(self):
        self.config = {
                "instances": [{
                    "ip_address": "localhost",
                    "port":161,
                    "community_string": "public",
                    "metrics": [{
                        "MIB": "IF-MIB",
                        "table": "ifTable",
                        "symbols": ["ifInOctets", "ifOutOctets"],
                        "metric_tags": [{
                            "tag":"interface",
                            "column":"ifDescr"
                            }, {
                            "tag":"dumbindex",
                            "index":1
                            }]
                        }]
                    }]
                }

        self.check = load_check('snmp', self.config, self.agentConfig)

        self.check.check(self.config['instances'][0])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so that we get the rates
        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()
        # nb of metrics depends on the nb of interfaces on the test machine
        # so it's not possible to specify an excat number
        self.assertTrue(len(metrics)>0, "No metrics")
        for metric in metrics:
            self.assertTrue(metric[0] in ['snmp.ifInOctets', 'snmp.ifOutOctets'],
                            metric[0])
            tags = metric[3]['tags']
            # Assert that all the wanted tags are here
            self.assertEquals(len(tags), 3, tags)
            tag_group_expected = ["snmp_device", "dumbindex", "interface"]
            for tag in tags:
                tag_group = tag.split(":")[0]
                self.assertTrue(tag_group in tag_group_expected, tag_group)
                if tag_group == "interface":
                    interface_type = tag.split(":")[1]
                    try:
                        float(interface_type)
                    except ValueError:
                        pass
                    else:
                        self.fail("Tag discovered not pretty printed %s" % interface_type)

if __name__ == "__main__":
    unittest.main()
