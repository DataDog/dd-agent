# stdlib
import tempfile
import time

# project
from tests.checks.common import AgentCheckTest, Fixtures


class NagiosTestCase(AgentCheckTest):
    CHECK_NAME = 'nagios'
    NAGIOS_TEST_LOG = Fixtures.file('nagios.log')
    NAGIOS_TEST_HOST = Fixtures.file('host-perfdata')
    NAGIOS_TEST_SVC = Fixtures.file('service-perfdata')
    NAGIOS_TEST_HOST_TEMPLATE = "[HOSTPERFDATA]\t$TIMET$\t$HOSTNAME$\t$HOSTEXECUTIONTIME$\t$HOSTOUTPUT$\t$HOSTPERFDATA$"
    NAGIOS_TEST_SVC_TEMPLATE = "[SERVICEPERFDATA]\t$TIMET$\t$HOSTNAME$\t$SERVICEDESC$\t$SERVICEEXECUTIONTIME$\t$SERVICELATENCY$\t$SERVICEOUTPUT$\t$SERVICEPERFDATA$"

    def get_config(self, nagios_conf, events=False, service_perf=False, host_perf=False):
        """
        Helper to generate a valid Nagios configuration
        """
        self.nagios_cfg = tempfile.NamedTemporaryFile(mode="a+b")
        self.nagios_cfg.write(nagios_conf)
        self.nagios_cfg.flush()

        return {
            'instances': [{
                'nagios_conf': self.nagios_cfg.name,
                'collect_events': events,
                'collect_service_performance_data': service_perf,
                'collect_host_performance_data': host_perf
            }]
        }


class EventLogTailerTestCase(NagiosTestCase):
    def test_line_parser(self):
        """
        Parse lines
        """
        config = self.get_config(
            '\n'.join(["log_file={0}".format(self.NAGIOS_TEST_LOG)]),
            events=True
        )

        self.run_check(config)

        nagios_tailer = self.check.nagios_tails[self.nagios_cfg.name][0]
        counters = {}

        for line in open(self.NAGIOS_TEST_LOG).readlines():
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

    def test_continuous_bulk_parsing(self):
        """
        Make sure the tailer continues to parse nagios as the file grows
        """
        x = open(self.NAGIOS_TEST_LOG).read()
        events = []
        ITERATIONS = 10
        f = tempfile.NamedTemporaryFile(mode="a+b")
        f.write(x)
        f.flush()

        config = self.get_config('\n'.join(["log_file={0}".format(f.name)]), events=True)
        self.run_check(config)

        for i in range(ITERATIONS):
            f.write(x)
            f.flush()
            self.run_check(config)
            events.extend(self.events)
        f.close()
        self.assertEquals(len(events), ITERATIONS * 503)


class PerfDataTailerTestCase(NagiosTestCase):
    POINT_TIME = (int(time.time()) / 15) * 15

    DB_LOG_DATA = [(
        "DATATYPE::SERVICEPERFDATA",
        "TIMET::%s" % POINT_TIME,
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

    DISK_LOG_DATA = [(
        "DATATYPE::SERVICEPERFDATA",
        "TIMET::%s" % POINT_TIME,
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

    HOST_LOG_DATA = [(
        "DATATYPE::HOSTPERFDATA",
        "TIMET::%s" % POINT_TIME,
        "HOSTNAME::myhost1",
        "HOSTPERFDATA::" + " ".join([
            "rta=0.978000ms;5000.000000;5000.000000;0.000000",
            "pl=0%;100;100;0",
        ]),
        "HOSTCHECKCOMMAND::check-host-alive",
        "HOSTSTATE::UP",
        "HOSTSTATETYPE::HARD",
    )]

    def _write_log(self, log_data):
        """
        Write log data to log file
        """
        for data in log_data:
            self.log_file.write(data + "\n")
        self.log_file.flush()

    def compare_metric(self, actual, expected):
        """
        Return true when `actual` metic == `expected` metric
        """
        self.assertEquals(actual[0], expected[0], "Metrics name actual:{0} vs expected:{1}"
                          .format(actual[0], expected[0]))
        self.assertEquals(actual[1], expected[1], "Timestamp actual:{0} vs expected:{1}"
                          .format(actual[1], expected[1]))
        self.assertEquals(actual[2], expected[2], "Value actual:{0} vs expected:{1}"
                          .format(actual[2], expected[2]))
        self.assertEqual(actual[3], expected[3], "Context actual:{0} vs expected:{1}"
                         .format(actual[3], expected[3]))

    def test_service_perfdata(self):
        """
        Collect Nagios Service PerfData metrics
        """
        self.log_file = tempfile.NamedTemporaryFile()
        config = self.get_config(
            '\n'.join(["service_perfdata_file=%s" % self.log_file.name, "service_perfdata_file_template=DATATYPE::SERVICEPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tSERVICEDESC::$SERVICEDESC$\tSERVICEPERFDATA::$SERVICEPERFDATA$\tSERVICECHECKCOMMAND::$SERVICECHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$\tSERVICESTATE::$SERVICESTATE$\tSERVICESTATETYPE::$SERVICESTATETYPE$"]),
            service_perf=True)
        self.run_check(config)

        # Write content to log file and run check
        self._write_log(['\t'.join(data) for data in self.DB_LOG_DATA])
        self.run_check(config)

        # Test metrics
        service_perf_data = self.DB_LOG_DATA[0][4][17:]  # 'time=0.06 db0=33;180;190;0;200 db1=1;150;190;0;200 db2=0;120;290;1;200 db3=0;110;195;5;100'

        for metric_data in service_perf_data.split(" "):
            name, info = metric_data.split("=")
            metric_name = "nagios.pgsql_backends." + name

            values = info.split(";")
            value = float(values[0])
            expected_tags = []
            if len(values) == 5:
                expected_tags.append('warn:' + values[1])
                expected_tags.append('crit:' + values[2])
                expected_tags.append('min:' + values[3])
                expected_tags.append('max:' + values[4])

            self.assertMetric(metric_name, value=value, tags=expected_tags, count=1)

        self.coverage_report()

    def test_service_perfdata_special_cases(self):
        """
        Handle special cases in PerfData metrics
        """
        self.log_file = tempfile.NamedTemporaryFile()
        config = self.get_config(
            '\n'.join(["service_perfdata_file=%s" % self.log_file.name, "service_perfdata_file_template=DATATYPE::SERVICEPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tSERVICEDESC::$SERVICEDESC$\tSERVICEPERFDATA::$SERVICEPERFDATA$\tSERVICECHECKCOMMAND::$SERVICECHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$\tSERVICESTATE::$SERVICESTATE$\tSERVICESTATETYPE::$SERVICESTATETYPE$",]),
            service_perf=True)
        self.run_check(config)

        # Write content to log file and run check
        self._write_log(['\t'.join(data) for data in self.DISK_LOG_DATA])
        self.run_check(config)

        # Test metrics
        service_perf_data = self.DISK_LOG_DATA[0][4][17:]

        for metric_data in service_perf_data.split(" "):
            name, info = metric_data.split("=")
            values = info.split(";")
            value = int(values[0][:-2])
            expected_tags = ['unit:' + values[0][-2:]]
            if len(values) == 5:
                expected_tags.append('warn:' + values[1])
                expected_tags.append('crit:' + values[2])
                expected_tags.append('min:' + values[3])
                expected_tags.append('max:' + values[4])

            self.assertMetric("nagios.disk_space", value=value, tags=expected_tags,
                              device_name=name, count=1)

        self.coverage_report()

    def test_host_perfdata(self):
        """
        Collect Nagios Host PerfData metrics
        """
        self.log_file = tempfile.NamedTemporaryFile()
        config = self.get_config(
            '\n'.join(["host_perfdata_file=%s" % self.log_file.name, "host_perfdata_file_template=DATATYPE::HOSTPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tHOSTPERFDATA::$HOSTPERFDATA$\tHOSTCHECKCOMMAND::$HOSTCHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$"]),
            host_perf=True)
        self.run_check(config)

        # Write content to log file and run check
        self._write_log(['\t'.join(data) for data in self.HOST_LOG_DATA])
        self.run_check(config)

        # Test metric
        service_perf_data = self.HOST_LOG_DATA[0][3][14:]

        for metric_data in service_perf_data.split(" "):
            name, info = metric_data.split("=")
            metric_name = "nagios.host." + name

            values = info.split(";")

            index = values[0].find("ms") if values[0].find("ms") != -1 else values[0].find("%")
            index = len(values[0]) - index
            value = float(values[0][:-index])
            expected_tags = ['unit:' + values[0][-index:]]
            if len(values) == 4:
                expected_tags.append('warn:' + values[1])
                expected_tags.append('crit:' + values[2])
                expected_tags.append('min:' + values[3])

            self.assertMetric(metric_name, value=value, tags=expected_tags, count=1)

        self.coverage_report()

    def test_alt_service_perfdata(self):
        """
        Collect Nagios Service PerfData metrics - alternative template
        """
        self.log_file = tempfile.NamedTemporaryFile()
        perfdata_file = tempfile.NamedTemporaryFile()
        config = self.get_config('\n'.join(
            ["service_perfdata_file=%s" % perfdata_file.name, "service_perfdata_file_template=%s" % self.NAGIOS_TEST_SVC_TEMPLATE]),
            service_perf=True
        )
        self.run_check(config)

        with open(self.NAGIOS_TEST_SVC, "r") as f:
            nagios_perf = f.read()

        perfdata_file.write(nagios_perf)
        perfdata_file.flush()

        self.run_check(config)

        # Test metrics
        expected_output = [
            (
                'nagios.current_users.users', 1339511440, 1.0,
                {
                    'type': 'gauge',
                    'hostname': 'localhost',
                    'tags': ['warn:20', 'crit:50', 'min:0']
                }
            ), (
                'nagios.ping.pl', 1339511500, 0.0,
                {
                    'type': 'gauge',
                    'hostname': 'localhost',
                    'tags': ['unit:%', 'warn:20', 'crit:60', 'min:0']
                }
            ), (
                'nagios.ping.rta', 1339511500, 0.065,
                {
                    'type': 'gauge',
                    'hostname': 'localhost',
                    'tags': ['unit:ms', 'warn:100.000000', 'crit:500.000000', 'min:0.000000']
                }
            ), ('nagios.root_partition', 1339511560, 2470.0,
                {
                    'type': 'gauge',
                    'hostname': 'localhost',
                    'device_name': '/',
                    'tags': ['unit:MB', 'warn:5852', 'crit:6583', 'min:0', 'max:7315']
                }
                )
        ]

        for actual, expected in zip(sorted(self.metrics), sorted(expected_output)):
            self.compare_metric(actual, expected)

        self.coverage_report()

    def test_alt_host_perfdata(self):
        """
        Collect Nagios Host PerfData metrics - alternative template
        """
        self.log_file = tempfile.NamedTemporaryFile()
        perfdata_file = tempfile.NamedTemporaryFile()
        config = self.get_config(
            '\n'.join(["host_perfdata_file=%s" % perfdata_file.name, "host_perfdata_file_template=%s" % self.NAGIOS_TEST_HOST_TEMPLATE]),
            host_perf=True)
        self.run_check(config)

        with open(self.NAGIOS_TEST_HOST, "r") as f:
            nagios_perf = f.read()

        perfdata_file.write(nagios_perf)
        perfdata_file.flush()

        self.run_check(config)

        # Test metrics
        expected_output = [
            (
                'nagios.host.pl', 1339511440, 0.0,
                {
                    'type': 'gauge',
                    'hostname': 'localhost',
                    'tags': ['unit:%', 'warn:80', 'crit:100', 'min:0']
                }
            ), (
                'nagios.host.rta', 1339511440, 0.048,
                {
                    'type': 'gauge',
                    'hostname': 'localhost',
                    'tags': ['unit:ms', 'warn:3000.000000', 'crit:5000.000000', 'min:0.000000']
                }
            )]

        for actual, expected in zip(sorted(self.metrics), sorted(expected_output)):
            self.compare_metric(actual, expected)

        self.coverage_report()
