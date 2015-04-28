import copy

# 3rd party
from nose.plugins.attrib import attr

# agent
from checks import AgentCheck
from tests.checks.common import AgentCheckTest

# This test is dependent of having a fully open snmpd responding at localhost:161
# with an authentication by the Community String "public"
# This setup should normally be handled by the .travis.yml file, look there if
# you want to see how to run these tests locally


@attr(requires='snmpd')
class SNMPTestCase(AgentCheckTest):
    CHECK_NAME = 'snmp'

    SNMP_CONF = {
        'ip_address': "localhost",
        'port': 11111,
        'community_string': "public",
    }

    MIBS_FOLDER = {
        'init_config': {
            'mibs_folder': "/etc/mibs"
        }
    }

    IGNORE_NONINCREASING_OID = {
        'init_config': {
            'ignore_nonincreasing_oid': True
        }
    }

    SUPPORTED_METRIC_TYPES = [
        {
            'OID': "1.3.6.1.2.1.7.1",               # Counter32
            'name': "IAmACounter32"
        }, {
            'OID': "1.3.6.1.2.1.4.31.1.1.6.1",      # Counter32
            'name': "IAmACounter64"
        }, {
            'OID': "1.3.6.1.2.1.4.24.6.0",          # Gauge32
            'name': "IAmAGauge32"
        }, {
            'OID': "1.3.6.1.2.1.88.1.1.1.0",        # Integer
            'name': "IAmAnInteger"
        }
    ]

    UNSUPPORTED_METRICS = [
        {
            'OID': "1.3.6.1.2.1.25.6.3.1.2.637",    # String (not supported)
            'name': "IAmString"
        }
    ]

    SCALAR_OBJECTS = [
        {
            'OID': "1.3.6.1.2.1.7.1.0",
            'name': "udpDatagrams"
        }, {
            'OID': "1.3.6.1.2.1.6.10",
            'name': "tcpInSegs"
        }, {
            'MIB': "TCP-MIB",
            'symbol': "tcpCurrEstab",
        }
    ]

    TABULAR_OBJECTS = [{
        'MIB': "IF-MIB",
        'table': "ifTable",
        'symbols': ["ifInOctets", "ifOutOctets"],
        'metric_tags': [
            {
                'tag': "interface",
                'column': "ifDescr"
            }, {
                'tag': "dumbindex",
                'index': 1
            }
        ]
    }]

    INVALID_METRICS = [
        {
            'MIB': "IF-MIB",
            'table': "noIdeaWhatIAmDoingHere",
            'symbols': ["ifInOctets", "ifOutOctets"],
        }
    ]

    PLAY_WITH_GET_NEXT_METRICS = [
        {
            "OID": "1.3.6.1.2.1.25.6.3.1.4",
            "name": "needFallback"
        }, {
            "OID": "1.3.6.1.2.1.25.6.3.1.4.0",
            "name": "noFallbackAndSameResult"
        }, {
            "OID": "1.3.6.1.2.1.25.6.3.1.4.547",
            "name": "failIfFallback"
        }
    ]

    CHECK_TAGS = ['snmp_device:localhost']

    @classmethod
    def generate_instance_config(cls, metrics):
        instance_config = copy.copy(cls.SNMP_CONF)
        instance_config['metrics'] = metrics
        return instance_config

    def test_command_generator(self):
        """
        Command generator's parameters should match init_config
        """
        self.run_check(self.MIBS_FOLDER)

        # Test command generator MIB source
        mib_folders = self.check.cmd_generator.snmpEngine.msgAndPduDsp\
            .mibInstrumController.mibBuilder.getMibSources()
        full_path_mib_folders = map(lambda f: f.fullPath(), mib_folders)

        self.assertTrue("/etc/mibs" in full_path_mib_folders)
        self.assertFalse(self.check.cmd_generator.ignoreNonIncreasingOid)

        # Test command generator `ignoreNonIncreasingOid` parameter
        self.run_check(self.IGNORE_NONINCREASING_OID, force_reload=True)
        self.assertTrue(self.check.cmd_generator.ignoreNonIncreasingOid)

    def test_type_support(self):
        """
        Support expected types
        """
        config = {
            'instances': [self.generate_instance_config(
                self.SUPPORTED_METRIC_TYPES + self.UNSUPPORTED_METRICS)]
        }
        self.run_check_twice(config)

        # Test metrics
        for metric in self.SUPPORTED_METRIC_TYPES:
            metric_name = "snmp." + metric['name']
            self.assertMetric(metric_name, tags=self.CHECK_TAGS, count=1)
        for metric in self.UNSUPPORTED_METRICS:
            metric_name = "snmp." + metric['name']
            self.assertMetric(metric_name, tags=self.CHECK_TAGS, count=0)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, count=1)

        self.coverage_report()

    def test_snpget(self):
        """
        When failing with 'snpget' command, SNMP check falls back to 'snpgetnext'

            > snmpget -v2c -c public localhost:11111 1.3.6.1.2.1.25.6.3.1.4
            iso.3.6.1.2.1.25.6.3.1.4 = No Such Instance currently exists at this OID
            > snmpgetnext -v2c -c public localhost:11111 1.3.6.1.2.1.25.6.3.1.4
            iso.3.6.1.2.1.25.6.3.1.4.0 = INTEGER: 4
        """
        config = {
            'instances': [self.generate_instance_config(self.PLAY_WITH_GET_NEXT_METRICS)]
        }
        self.run_check(config)

        # Test metrics
        for metric in self.PLAY_WITH_GET_NEXT_METRICS:
            metric_name = "snmp." + metric['name']
            self.assertMetric(metric_name, tags=self.CHECK_TAGS, count=1)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, count=1)

        self.coverage_report()

    def test_scalar(self):
        """
        Support SNMP scalar objects
        """
        config = {
            'instances': [self.generate_instance_config(self.SCALAR_OBJECTS)]
        }
        self.run_check_twice(config)

        # Test metrics
        for metric in self.SCALAR_OBJECTS:
            metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
            self.assertMetric(metric_name, tags=self.CHECK_TAGS, count=1)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, count=1)

        self.coverage_report()

    def test_table(self):
        """
        Support SNMP tabular objects
        """
        config = {
            'instances': [self.generate_instance_config(self.TABULAR_OBJECTS)]
        }
        self.run_check_twice(config)

        # Test metrics
        for symbol in self.TABULAR_OBJECTS[0]['symbols']:
            metric_name = "snmp." + symbol
            self.assertMetric(metric_name, at_least=1)
            self.assertMetricTag(metric_name, self.CHECK_TAGS[0], at_least=1)

            for mtag in self.TABULAR_OBJECTS[0]['metric_tags']:
                tag = mtag['tag']
                self.assertMetricTagPrefix(metric_name, tag, at_least=1)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, count=1)

        self.coverage_report()

    def test_invalid_metric(self):
        """
        Invalid metrics raise an Exception and a service check
        """
        config = {
            'instances': [self.generate_instance_config(self.INVALID_METRICS)]
        }
        self.assertRaises(Exception, self.run_check, config)

        # # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.CRITICAL,
                                tags=self.CHECK_TAGS, count=1)
        self.coverage_report()

    def test_network_failure(self):
        """
        Network failure is reported in service check
        """
        instance = self.generate_instance_config(self.SCALAR_OBJECTS)

        # Change port so connection will fail
        instance['port'] = 162

        config = {
            'instances': [instance]
        }

        self.assertRaises(Exception, self.run_check, config)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.CRITICAL,
                                tags=self.CHECK_TAGS, count=1)
        self.coverage_report()
