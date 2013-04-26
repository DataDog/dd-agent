import unittest
import os
import tempfile

from tests.common import load_check

NAGIOS_TEST_LOG = os.path.join(os.path.dirname(__file__), "nagios.log")
NAGIOS_TEST_HOST = os.path.join(os.path.dirname(__file__), "host-perfdata")
NAGIOS_TEST_SVC = os.path.join(os.path.dirname(__file__), "service-perfdata")
NAGIOS_TEST_HOST_TEMPLATE="[HOSTPERFDATA]\t$TIMET$\t$HOSTNAME$\t$HOSTEXECUTIONTIME$\t$HOSTOUTPUT$\t$HOSTPERFDATA$"
NAGIOS_TEST_SVC_TEMPLATE="[SERVICEPERFDATA]\t$TIMET$\t$HOSTNAME$\t$SERVICEDESC$\t$SERVICEEXECUTIONTIME$\t$SERVICELATENCY$\t$SERVICEOUTPUT$\t$SERVICEPERFDATA$"


class TestNagios(unittest.TestCase):
    def setUp(self):
        self.nagios_config = tempfile.NamedTemporaryFile()
        self.nagios_config.flush()
        self.agentConfig = {
            'nagios_perf_cfg': self.nagios_config.name,
            'check_freq': 5,
            'api_key': '123'
        }

        # Initialize the check from checks.d
        self.check = load_check('nagios', {'init_config': {}, 'instances': {}}, self.agentConfig)

    def _write_log(self, log_data):
        for data in log_data:
            print >> self.log_file, data
        self.log_file.flush()

    def _write_nagios_config(self, config_data):
        for data in config_data:
            print >> self.nagios_config, data
        self.nagios_config.flush()

    def _point_sorter(self, p):
        # Sort and group by timestamp, metric name, host_name, device_name
        return (p[1], p[0], p[3].get('host_name', None), p[3].get('device_name', None))

    def tearDown(self):
        self.nagios_config.close()

    def testParseLine(self):
        """Test line parser"""
        import imp

        cur_path = os.path.dirname(os.path.realpath(__file__))
        nagiospy_source_path = os.path.join(cur_path, os.pardir, 'checks.d', 'nagios.py')
        nagios_module = imp.load_source('checksd_nagios', nagiospy_source_path)

        # Instantiate a dummy nagios log parser
        log_parser = nagios_module.NagiosLogParser(self.check.log, None)

        counters = {}

        for line in open(NAGIOS_TEST_LOG).readlines():
            parsed = log_parser._parse_line(line)
            if parsed:
                # Handle the event created by the log parser by passing it into
                # the create_event method of the check and then retrieving the result
                self.check.create_event(log_parser._get_events()[-1])
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

        new_agent_conf = {'nagios_log': f.name}

        new_conf = self.check.parse_agent_config(new_agent_conf)

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
        log_f = tempfile.NamedTemporaryFile(mode="a+b")
        log_f2 = tempfile.NamedTemporaryFile(mode="a+b")

        log_files = [log_f, log_f2]

        instances = [
            {'log_file': log_f.name},
            {'log_file': log_f2.name}
        ]

        for index, instance in enumerate(instances):
            cur_file = log_files[index]

            # Give each of the files a different number of lines
            for i in range(index):
                cur_file.writelines(x)
            cur_file.flush()

            self.check.check(instance)
            events = self.check.get_events()
            assert len(events) == 503 * index

        log_f.close()
        log_f2.close()

    def test_service_perfdata(self):
        self.log_file = tempfile.NamedTemporaryFile()

        self._write_nagios_config([
            "service_perfdata_file=%s" % self.log_file.name,
            "service_perfdata_file_template=DATATYPE::SERVICEPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tSERVICEDESC::$SERVICEDESC$\tSERVICEPERFDATA::$SERVICEPERFDATA$\tSERVICECHECKCOMMAND::$SERVICECHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$\tSERVICESTATE::$SERVICESTATE$\tSERVICESTATETYPE::$SERVICESTATETYPE$",
        ])

        instance = {
            'cfg_file': self.nagios_config.name,
            'event_log': False,
            'perf_data': True
        }

        log_data = [(
            "DATATYPE::SERVICEPERFDATA",
            "TIMET::1000000000",
            "HOSTNAME::myhost0",
            "SERVICEDESC::Pgsql Backends",
            "SERVICEPERFDATA::" + " ".join([
                "time=0.06",
                "db0=33;180;190;0;200",
                "db1=1;150;190;0;200",
                "db2=0;120;290;1;200",
                "db3=0;110;195;5;100"
            ]),
            "SERVICECHECKCOMMAND::check_nrpe_1arg!check_postgres_backends",
            "HOSTSTATE::UP",
            "HOSTSTATETYPE::HARD",
            "SERVICESTATE::OK",
            "SERVICESTATETYPE::HARD",
        )]

        self._write_log(('\t'.join(data) for data in log_data))

        self.check.check(instance)
        actual_output = self.check.get_metrics()
        flush_timestamp = actual_output[0][1]
        actual_output.sort(key=self._point_sorter)

        expected_output = [
            ('nagios.pgsql_backends.time', flush_timestamp, 0.06, {
                'hostname': 'myhost0'
            }),
            ('nagios.pgsql_backends.db0', flush_timestamp, 33, {
                'hostname': 'myhost0'
            }),
            ('nagios.pgsql_backends.db1', flush_timestamp, 1, {
                'hostname': 'myhost0'
            }),
            ('nagios.pgsql_backends.db2', flush_timestamp, 0, {
                'hostname': 'myhost0'
            }),
            ('nagios.pgsql_backends.db3', flush_timestamp, 0, {
                'hostname': 'myhost0'
            })
        ]
        expected_output.sort(key=self._point_sorter)

        self.assertEquals(expected_output, actual_output)
        self.log_file.close()

    def test_service_perfdata_special_cases(self):
        self.log_file = tempfile.NamedTemporaryFile()

        self._write_nagios_config([
            "service_perfdata_file=%s" % self.log_file.name,
            "service_perfdata_file_template=DATATYPE::SERVICEPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tSERVICEDESC::$SERVICEDESC$\tSERVICEPERFDATA::$SERVICEPERFDATA$\tSERVICECHECKCOMMAND::$SERVICECHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$\tSERVICESTATE::$SERVICESTATE$\tSERVICESTATETYPE::$SERVICESTATETYPE$",
        ])

        instance = {
            'cfg_file': self.nagios_config.name,
            'event_log': False,
            'perf_data': True
        }

        log_data = [(
            "DATATYPE::SERVICEPERFDATA",
            "TIMET::1000000000",
            "HOSTNAME::myhost2",
            "SERVICEDESC::Disk Space",
            "SERVICEPERFDATA::" + " ".join([
                "/=5477MB;6450;7256;0;8063",
                "/dev=0MB;2970;3341;0;3713",
                "/dev/shm=0MB;3080;3465;0;3851",
                "/var/run=0MB;3080;3465;0;3851",
                "/var/lock=0MB;3080;3465;0;3851",
                "/lib/init/rw=0MB;3080;3465;0;3851",
                "/mnt=290MB;338636;380966;0;423296",
                "/data=39812MB;40940;46057;0;51175",
            ]),
            "SERVICECHECKCOMMAND::check_all_disks!20%!10%",
            "HOSTSTATE::UP",
            "HOSTSTATETYPE::HARD",
            "SERVICESTATE::OK",
            "SERVICESTATETYPE::HARD",
        )]

        self._write_log(('\t'.join(data) for data in log_data))

        self.check.check(instance)
        actual_output = self.check.get_metrics()
        flush_timestamp = actual_output[0][1]
        actual_output.sort(key=self._point_sorter)

        expected_output = [
            ('nagios.disk_space', flush_timestamp, 5477, {
                'hostname': 'myhost2',
                'device_name': '/'
            }),
            ('nagios.disk_space', flush_timestamp, 0, {
                'hostname': 'myhost2',
                'device_name': '/dev'
            }),
            ('nagios.disk_space', flush_timestamp, 0, {
                'hostname': 'myhost2',
                'device_name': '/dev/shm'
            }),
            ('nagios.disk_space', flush_timestamp, 0, {
                'hostname': 'myhost2',
                'device_name': '/var/run'
            }),
            ('nagios.disk_space', flush_timestamp, 0, {
                'hostname': 'myhost2',
                'device_name': '/var/lock'
            }),
            ('nagios.disk_space', flush_timestamp, 0, {
                'hostname': 'myhost2',
                'device_name': '/lib/init/rw'
            }),
            ('nagios.disk_space', flush_timestamp, 290, {
                'hostname': 'myhost2',
                'device_name': '/mnt'
            }),
            ('nagios.disk_space', flush_timestamp, 39812, {
                'hostname': 'myhost2',
                'device_name': '/data'
            })
        ]
        expected_output.sort(key=self._point_sorter)

        self.assertEquals(expected_output, actual_output)
        self.log_file.close()

    def test_host_perfdata(self):
        self.log_file = tempfile.NamedTemporaryFile()

        self._write_nagios_config([
            "host_perfdata_file=%s" % self.log_file.name,
            "host_perfdata_file_template=DATATYPE::HOSTPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tHOSTPERFDATA::$HOSTPERFDATA$\tHOSTCHECKCOMMAND::$HOSTCHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$",
        ])

        instance = {
            'cfg_file': self.nagios_config.name,
            'event_log': False,
            'perf_data': True
        }

        log_data = [(
            "DATATYPE::HOSTPERFDATA",
            "TIMET::1000000010",
            "HOSTNAME::myhost1",
            "HOSTPERFDATA::" + " ".join([
                "rta=0.978000ms;5000.000000;5000.000000;0.000000",
                "pl=0%;100;100;0",
            ]),
            "HOSTCHECKCOMMAND::check-host-alive",
            "HOSTSTATE::UP",
            "HOSTSTATETYPE::HARD",
        )]

        self._write_log(('\t'.join(data) for data in log_data))

        self.check.check(instance)
        actual_output = self.check.get_metrics()
        flush_timestamp = actual_output[0][1]
        actual_output.sort(key=self._point_sorter)

        expected_output = [
            ('nagios.host.rta', flush_timestamp, 0.978, {
                'hostname': 'myhost1'
            }),
            ('nagios.host.pl', flush_timestamp, 0, {
                'hostname': 'myhost1'
            })
        ]
        expected_output.sort(key=self._point_sorter)

        self.assertEquals(expected_output, actual_output)
        self.log_file.close()

    def test_alt_service_perfdata(self):
        self._write_nagios_config([
            "service_perfdata_file=%s" % NAGIOS_TEST_SVC,
            "service_perfdata_file_template=%s" % NAGIOS_TEST_SVC_TEMPLATE,
        ])

        instance = {
            'cfg_file': self.nagios_config.name,
            'event_log': False,
            'perf_data': True
        }

        self.check.check(instance)
        actual_output = self.check.get_metrics()
        flush_timestamp = actual_output[0][1]
        actual_output.sort(key=self._point_sorter)

        expected_output = [
            ('nagios.current_users.users', flush_timestamp, 1.0, {
                'hostname': 'localhost'
            }),
            ('nagios.ping.pl', flush_timestamp, 0.0, {
                'hostname': 'localhost'
            }),
            ('nagios.ping.rta', flush_timestamp, 0.065, {
                'hostname': 'localhost'
            }),
            ('nagios.root_partition', flush_timestamp, 2470.0, {
                'hostname': 'localhost',
                'device_name': '/'
            })
        ]
        expected_output.sort(key=self._point_sorter)

        self.assertEquals(expected_output, actual_output)

    def test_alt_host_perfdata(self):

        self._write_nagios_config([
            "host_perfdata_file=%s" % NAGIOS_TEST_HOST,
            "host_perfdata_file_template=%s" % NAGIOS_TEST_HOST_TEMPLATE,
        ])

        instance = {
            'cfg_file': self.nagios_config.name,
            'event_log': False,
            'perf_data': True
        }

        self.check.check(instance)
        actual_output = self.check.get_metrics()
        flush_timestamp = actual_output[0][1]
        actual_output.sort(key=self._point_sorter)

        expected_output = [
            ('nagios.host.pl', flush_timestamp, 0.0, {
                'hostname': 'localhost'
            }),
            ('nagios.host.rta', flush_timestamp, 0.048, {
                'hostname': 'localhost'
            })
        ]
        expected_output.sort(key=self._point_sorter)

        self.assertEquals(expected_output, actual_output)

    def test_fake_config_file(self):

        instance = {
            'cfg_file': 'fake_config_file'
        }

        self.assertRaises(IOError, self.check.check, instance)

if __name__ == '__main__':
    unittest.main()
