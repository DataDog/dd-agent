import time
import unittest
import logging; logger = logging.getLogger(__file__)
import os
import tempfile

from tests.common import load_check
from tests.test_datadog import TailTestCase

NAGIOS_TEST_LOG = os.path.join(os.path.dirname(__file__), "nagios.log")
NAGIOS_TEST_HOST = os.path.join(os.path.dirname(__file__), "host-perfdata")
NAGIOS_TEST_SVC = os.path.join(os.path.dirname(__file__), "service-perfdata")
NAGIOS_TEST_HOST_TEMPLATE="[HOSTPERFDATA]\t$TIMET$\t$HOSTNAME$\t$HOSTEXECUTIONTIME$\t$HOSTOUTPUT$\t$HOSTPERFDATA$"
NAGIOS_TEST_SVC_TEMPLATE="[SERVICEPERFDATA]\t$TIMET$\t$HOSTNAME$\t$SERVICEDESC$\t$SERVICEEXECUTIONTIME$\t$SERVICELATENCY$\t$SERVICEOUTPUT$\t$SERVICEPERFDATA$"

class TestNagios(unittest.TestCase):

    def _setupAgentCheck(self, nagios_conf, events=False, service_perf=False, host_perf=False):
        self.nagios_cfg = tempfile.NamedTemporaryFile(mode="a+b")
        self.nagios_cfg.write(nagios_conf)
        self.nagios_cfg.flush()
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
                }
        self.config = {
                'init_config' : {'check_freq' : 5},
                'instances': [{
                    'nagios_conf': self.nagios_cfg.name,
                    'collect_events': events,
                    'collect_service_performance_data': service_perf,
                    'collect_host_performance_data': host_perf
                    }]
                }
        self.check = load_check('nagios', self.config, self.agentConfig)


    def testParseLine(self):
        """Test line parser"""
        self._setupAgentCheck('\n'.join(["log_file={0}".format(NAGIOS_TEST_LOG)]), events=True)
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
                elif t == "PROCESS_SERVICE_CHECK_RESULT":
                    assert event["host"] is not None
                    assert event["check_name"] is not None
                    assert event["return_code"] is not None

        self.assertEquals(counters["SERVICE ALERT"], 301)
        self.assertEquals(counters["SERVICE NOTIFICATION"], 120)
        self.assertEquals(counters["HOST ALERT"], 3)
        self.assertEquals(counters["SERVICE FLAPPING ALERT"], 7)
        self.assertEquals(counters["CURRENT HOST STATE"], 8)
        self.assertEquals(counters["CURRENT SERVICE STATE"], 52)
        self.assertEquals(counters["SERVICE DOWNTIME ALERT"], 3)
        self.assertEquals(counters["HOST DOWNTIME ALERT"], 5)
        self.assertEquals(counters["ACKNOWLEDGE_SVC_PROBLEM"], 4)
        self.assertEquals(counters["PROCESS_SERVICE_CHECK_RESULT"], 1)
        assert "ACKNOWLEDGE_HOST_PROBLEM" not in counters

    def testContinuousBulkParsing(self):
        """Make sure the tailer continues to parse nagios as the file grows"""
        x = open(NAGIOS_TEST_LOG).read()
        events = []
        ITERATIONS = 10
        f = tempfile.NamedTemporaryFile(mode="a+b")
        f.write(x)
        f.flush()
        self._setupAgentCheck('\n'.join(["log_file={0}".format(f.name)]), events=True)

        for i in range(ITERATIONS):
            f.write(x)
            f.flush()
            self.check.check(self.config['instances'][0])
            events.extend(self.check.get_events())
        f.close()
        self.assertEquals(len(events), ITERATIONS * 503)

class TestNagiosPerfData(TestNagios):
    def compare_metric(self, actual, expected):
        self.assertEquals(actual[0], expected[0], "Metrics name actual:{0} vs expected:{1}"\
                .format(actual[0], expected[0]))
        self.assertEquals(actual[1], expected[1], "Timestamp actual:{0} vs expected:{1}"\
                .format(actual[1], expected[1]))
        self.assertEquals(actual[2], expected[2], "Value actual:{0} vs expected:{1}"\
                .format(actual[2], expected[2]))
        self.assertEqual(actual[3], expected[3], "Context actual:{0} vs expected:{1}"\
                .format(actual[3], expected[3]))

    def _write_log(self, log_data):
        for data in log_data:
            self.log_file.write(data+"\n")
        self.log_file.flush()

    def test_service_perfdata(self):
        self.log_file = tempfile.NamedTemporaryFile()
        self._setupAgentCheck('\n'.join(["service_perfdata_file=%s" % self.log_file.name,
            "service_perfdata_file_template=DATATYPE::SERVICEPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tSERVICEDESC::$SERVICEDESC$\tSERVICEPERFDATA::$SERVICEPERFDATA$\tSERVICECHECKCOMMAND::$SERVICECHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$\tSERVICESTATE::$SERVICESTATE$\tSERVICESTATETYPE::$SERVICESTATETYPE$",
        ]), service_perf=True)

        point_time = (int(time.time()) / 15) * 15

        log_data = [
            ("DATATYPE::SERVICEPERFDATA",
             "TIMET::%s" % point_time,
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
            ),
        ]

        expected_output = [
            ('nagios.pgsql_backends.time', point_time, 0.06, {
                'type': 'gauge',
                'hostname': 'myhost0',
            }),
            ('nagios.pgsql_backends.db0',  point_time,   33., {
                'type': 'gauge',
                'hostname': 'myhost0',
                'tags': ['warn:180',
                    'crit:190',
                    'min:0',
                    'max:200'],
            }),
            ('nagios.pgsql_backends.db1',  point_time,    1., {
                'type': 'gauge',
                'hostname': 'myhost0',
                'tags': ['warn:150',
                    'crit:190',
                    'min:0',
                    'max:200'],
            }),
            ('nagios.pgsql_backends.db2',  point_time,    0., {
                'type': 'gauge',
                'hostname': 'myhost0',
                'tags': ['warn:120',
                    'crit:290',
                    'min:1',
                    'max:200'],
            }),
            ('nagios.pgsql_backends.db3',  point_time,    0., {
                'type': 'gauge',
                'hostname': 'myhost0',
                'tags': ['warn:110',
                    'crit:195',
                    'min:5',
                    'max:100'],
            }),
        ]

        self._write_log(['\t'.join(data) for data in log_data])
        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()
        for actual, expected in zip(sorted(metrics), sorted(expected_output)):
            self.compare_metric(actual, expected)

    def test_service_perfdata_special_cases(self):
        self.log_file = tempfile.NamedTemporaryFile()
        self._setupAgentCheck('\n'.join(["service_perfdata_file=%s" % self.log_file.name,
            "service_perfdata_file_template=DATATYPE::SERVICEPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tSERVICEDESC::$SERVICEDESC$\tSERVICEPERFDATA::$SERVICEPERFDATA$\tSERVICECHECKCOMMAND::$SERVICECHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$\tSERVICESTATE::$SERVICESTATE$\tSERVICESTATETYPE::$SERVICESTATETYPE$",
        ]), service_perf=True)

        point_time = (int(time.time()) / 15) * 15

        log_data = [
            (   "DATATYPE::SERVICEPERFDATA",
                "TIMET::%s" % point_time,
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
            )
        ]

        expected_output = [
            ('nagios.disk_space', point_time, 5477., {
                'type': 'gauge',
                'hostname': 'myhost2',
                'device_name': '/',
                'tags':['unit:MB',
                    'warn:6450',
                    'crit:7256',
                    'min:0',
                    'max:8063'],
            }),
            ('nagios.disk_space', point_time, 0., {
                'type': 'gauge',
                'hostname': 'myhost2',
                'device_name': '/dev',
                'tags':['unit:MB',
                    'warn:2970',
                    'crit:3341',
                    'min:0',
                    'max:3713'],
            }),
            ('nagios.disk_space', point_time, 0., {
                'type': 'gauge',
                'hostname': 'myhost2',
                'device_name': '/dev/shm',
                'tags':['unit:MB',
                    'warn:3080',
                    'crit:3465',
                    'min:0',
                    'max:3851'],
            }),
            ('nagios.disk_space', point_time, 0., {
                'type': 'gauge',
                'hostname': 'myhost2',
                'device_name': '/var/run',
                'tags':['unit:MB',
                    'warn:3080',
                    'crit:3465',
                    'min:0',
                    'max:3851'],
            }),
            ('nagios.disk_space', point_time, 0., {
                'type': 'gauge',
                'hostname': 'myhost2',
                'device_name': '/var/lock',
                'tags':['unit:MB',
                    'warn:3080',
                    'crit:3465',
                    'min:0',
                    'max:3851'],
            }),
            ('nagios.disk_space', point_time, 0., {
                'type': 'gauge',
                'hostname': 'myhost2',
                'device_name': '/lib/init/rw',
                'tags':['unit:MB',
                    'warn:3080',
                    'crit:3465',
                    'min:0',
                    'max:3851'],
            }),
            ('nagios.disk_space', point_time, 290., {
                'type': 'gauge',
                'hostname': 'myhost2',
                'device_name': '/mnt',
                'tags':['unit:MB',
                    'warn:338636',
                    'crit:380966',
                    'min:0',
                    'max:423296'],
            }),
            ('nagios.disk_space', point_time, 39812., {
                'type': 'gauge',
                'hostname': 'myhost2',
                'device_name': '/data',
                'tags':['unit:MB',
                    'warn:40940',
                    'crit:46057',
                    'min:0',
                    'max:51175'],
            }),
        ]
        self._write_log(['\t'.join(data) for data in log_data])
        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()
        for actual, expected in zip(sorted(metrics), sorted(expected_output)):
            self.compare_metric(actual, expected)

    def test_host_perfdata(self):
        self.log_file = tempfile.NamedTemporaryFile()
        self._setupAgentCheck('\n'.join(["host_perfdata_file=%s" % self.log_file.name,
            "host_perfdata_file_template=DATATYPE::HOSTPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tHOSTPERFDATA::$HOSTPERFDATA$\tHOSTCHECKCOMMAND::$HOSTCHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$",
        ]), host_perf=True)

        point_time = (int(time.time()) / 15) * 15

        log_data = [
            ("DATATYPE::HOSTPERFDATA",
             "TIMET::%s" % point_time,
             "HOSTNAME::myhost1",
             "HOSTPERFDATA::" + " ".join([
                "rta=0.978000ms;5000.000000;5000.000000;0.000000",
                "pl=0%;100;100;0",
             ]),
             "HOSTCHECKCOMMAND::check-host-alive",
             "HOSTSTATE::UP",
             "HOSTSTATETYPE::HARD",
            ),
        ]

        expected_output = [
            ('nagios.host.rta', point_time, 0.978, {
                'type': 'gauge',
                'hostname': 'myhost1',
                'tags':['unit:ms',
                    'warn:5000.000000',
                    'crit:5000.000000',
                    'min:0.000000']
            }),
            ('nagios.host.pl',  point_time, 0., {
                'type': 'gauge',
                'hostname': 'myhost1',
                'tags':['unit:%',
                    'warn:100',
                    'crit:100',
                    'min:0']
            }),
        ]
        self._write_log(['\t'.join(data) for data in log_data])
        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()
        for actual, expected in zip(sorted(metrics), sorted(expected_output)):
            self.compare_metric(actual, expected)

    def test_alt_service_perfdata(self):
        self.log_file = tempfile.NamedTemporaryFile()
        perfdata_file = tempfile.NamedTemporaryFile()
        self._setupAgentCheck('\n'.join(["service_perfdata_file=%s" % perfdata_file.name,
            "service_perfdata_file_template=%s" % NAGIOS_TEST_SVC_TEMPLATE,
        ]), service_perf=True)

        # Because the timestamps are already written to the file, we need to
        # prevent from ignoring old values or we won't see anything
        self.check.aggregator.recent_point_threshold = int(time.time())

        with open(NAGIOS_TEST_SVC, "r") as f:
            nagios_perf = f.read()

        perfdata_file.write(nagios_perf)
        perfdata_file.flush()

        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        expected_output = [
                ('nagios.current_users.users', 1339511440, 1.0,
                    {'type': 'gauge',
                     'hostname': 'localhost',
                     'tags':['warn:20',
                         'crit:50',
                         'min:0']
                     }
                    ),
                ('nagios.ping.pl', 1339511500, 0.0,
                     {'type': 'gauge',
                     'hostname': 'localhost',
                     'tags':['unit:%',
                         'warn:20',
                         'crit:60',
                         'min:0']
                     }
                    ),
                ('nagios.ping.rta', 1339511500, 0.065,
                    {'type': 'gauge',
                     'hostname': 'localhost',
                     'tags':['unit:ms',
                         'warn:100.000000',
                         'crit:500.000000',
                         'min:0.000000',
                         ]
                     }
                    ),
                ('nagios.root_partition', 1339511560, 2470.0,
                    {'type': 'gauge',
                     'hostname': 'localhost',
                     'device_name': '/',
                     'tags':['unit:MB',
                         'warn:5852',
                         'crit:6583',
                         'min:0',
                         'max:7315',
                         ]
                     }
                    )
                 ]
        for actual, expected in zip(sorted(metrics), sorted(expected_output)):
            self.compare_metric(actual, expected)

    def test_alt_host_perfdata(self):
        self.log_file = tempfile.NamedTemporaryFile()
        perfdata_file = tempfile.NamedTemporaryFile()
        self._setupAgentCheck('\n'.join(["host_perfdata_file=%s" % perfdata_file.name,
            "host_perfdata_file_template=%s" % NAGIOS_TEST_HOST_TEMPLATE,
        ]),host_perf=True)
        # Because the timestamps are already written to the file, we need to
        # prevent from ignoring old values or we won't see anything
        self.check.aggregator.recent_point_threshold = int(time.time())

        with open(NAGIOS_TEST_HOST, "r") as f:
            nagios_perf = f.read()

        perfdata_file.write(nagios_perf)
        perfdata_file.flush()

        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        expected_output = [
                ('nagios.host.pl', 1339511440, 0.0,
                    {
                     'type': 'gauge',
                     'hostname': 'localhost',
                     'tags': ['unit:%',
                         'warn:80',
                         'crit:100',
                         'min:0'
                         ]
                     }
                    ),
                ('nagios.host.rta', 1339511440, 0.048,
                    {
                     'type': 'gauge',
                     'hostname': 'localhost',
                     'tags':['unit:ms',
                         'warn:3000.000000',
                         'crit:5000.000000',
                         'min:0.000000'
                         ]
                     }
                    )
                ]

        for actual, expected in zip(sorted(metrics), sorted(expected_output)):
            self.compare_metric(actual, expected)

if __name__ == '__main__':
    unittest.main()
