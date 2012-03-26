import logging
import sys
import unittest
from tempfile import NamedTemporaryFile

from checks.datadog import Dogstreams, point_sorter

log = logging.getLogger('datadog.test')

def parse_stateful(logger, line, state):
    """Simple stateful parser"""
    try:
        acc = state["test_acc"] + 1
    except KeyError:
        acc = 1
    state["test_acc"] = acc
    res = line.split()
    res[2] = acc
    res[3] = {'metric_type': 'counter'}
    return tuple(res)

class TailTestCase(unittest.TestCase):
    def setUp(self):
        self.log_file = NamedTemporaryFile()
        self.logger = logging.getLogger('test.dogstream')
    
    def _write_log(self, log_data):
        for data in log_data:
            print >> self.log_file, data
        self.log_file.flush()

    def tearDown(self):
        self.log_file.close()

class TestDogstream(TailTestCase):
    gauge = {'metric_type': 'gauge'}
    counter = {'metric_type': 'counter'}

    def setUp(self):
        TailTestCase.setUp(self)

        self.config = {
            'dogstreams': self.log_file.name,
            'checkFreq': 5,
        }
        log.info("Test config: %s" % self.config)
        self.dogstream = Dogstreams.init(self.logger, self.config)
    
    def test_dogstream_gauge(self):
        log_data = [
            # bucket 0
            ('test.metric.a', '1000000000', '10', 'metric_type=gauge'),
            ('test.metric.a', '1000000001', '20', 'metric_type=gauge'),
            ('test.metric.a', '1000000002', '3', 'metric_type=gauge'),
            ('test.metric.a', '1000000003', '4', 'metric_type=gauge'),
            ('test.metric.a', '1000000004', '5', 'metric_type=gauge'),

            # bucket 1
            ('test.metric.a', '1000000005', '12', 'metric_type=gauge'),
            ('test.metric.a', '1000000006', '7', 'metric_type=gauge'),
            ('test.metric.a', '1000000007', '8', 'metric_type=gauge'),
        ]
        
        expected_output = {
            "dogstream": [
                ('test.metric.a', 1000000000, 5.0, self.gauge),
                ('test.metric.a', 1000000005, 8.0, self.gauge),
            ]
        }
        
        self._write_log((' '.join(data) for data in log_data))

        actual_output = self.dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)
        for metric, timestamp, val, attr in expected_output['dogstream']:
            assert isinstance(val, float)
    
    def test_dogstream_counter(self):
        log_data = [
            # bucket 0
            ('test.metric.a', '1000000000', '10', 'metric_type=counter'),
            ('test.metric.a', '1000000001', '20', 'metric_type=counter'),
            ('test.metric.a', '1000000002', '3', 'metric_type=counter'),
            ('test.metric.a', '1000000003', '4', 'metric_type=counter'),
            ('test.metric.a', '1000000004', '5', 'metric_type=counter'),

            # bucket 1
            ('test.metric.a', '1000000005', '12', 'metric_type=counter'),
            ('test.metric.a', '1000000006', '7', 'metric_type=counter'),
            ('test.metric.a', '1000000007', '8', 'metric_type=counter'),
        ]
        
        expected_output = {
            "dogstream": [
                ('test.metric.a', 1000000000, 5, self.counter),
                ('test.metric.a', 1000000005, 8, self.counter),
            ]
        }
        
        self._write_log((' '.join(data) for data in log_data))

        actual_output = self.dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)
        for metric, timestamp, val, attr in expected_output['dogstream']:
            assert isinstance(val, (int, long))

    def test_dogstream_bad_input(self):
        log_data = [
            ('test.metric.e1000000000 1metric_type=gauge'),
            ('1000000001 1 metric_type=gauge tag=staging'),
            ('test_metric.e 1 1000000002 metric_type=gauge'),
            ('test_metric.e 1000000002 10 metric_type=gauge'),
        ]
        expected_output = {"dogstream":
            [('test_metric.e', 1000000000, 10, self.gauge)]
        }
        
        self._write_log(log_data)
        
        actual_output = self.dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)

    def test_dogstream_stateful(self):
        log_data = [
            'test.metric.accumulator 1000000000 1 metric_type=counter',
            'test.metric.accumulator 1100000000 1 metric_type=counter'
        ]
        expected_output = {
            "dogstream": [
                ('test.metric.accumulator', 1000000000, 1, self.counter),
                ('test.metric.accumulator', 1100000000, 2, self.counter)]
        }
        self._write_log(log_data)

        statedog = Dogstreams.init(self.logger, {'dogstreams': '%s:test_datadog:parse_stateful' % self.log_file.name})
        actual_output = statedog.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)

class TestNagiosPerfData(TailTestCase):
    def setUp(self):
        TailTestCase.setUp(self)
        self.nagios_config = NamedTemporaryFile()
        self.nagios_config.flush()

        self.agent_config = {
            'nagiosPerfCfg': self.nagios_config.name,
            'checkFreq': 5,
        }

    def _write_nagios_config(self, config_data):
        for data in config_data:
            print >> self.nagios_config, data
        self.nagios_config.flush()
    
    def tearDown(self):
        TailTestCase.tearDown(self)
        self.nagios_config.close()

    def test_service_perfdata(self):
        from checks.datadog import NagiosServicePerfData

        self._write_nagios_config([
            "service_perfdata_file=%s" % self.log_file.name,
            "service_perfdata_file_template=DATATYPE::SERVICEPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tSERVICEDESC::$SERVICEDESC$\tSERVICEPERFDATA::$SERVICEPERFDATA$\tSERVICECHECKCOMMAND::$SERVICECHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$\tSERVICESTATE::$SERVICESTATE$\tSERVICESTATETYPE::$SERVICESTATETYPE$",
        ])

        dogstream = Dogstreams.init(self.logger, self.agent_config)
        self.assertEquals([NagiosServicePerfData], [d.__class__ for d in dogstream.dogstreams])

        log_data = [
            ("DATATYPE::SERVICEPERFDATA", 
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
            ),
        ]
        
        expected_output = [
            ('nagios.pgsql_backends.time', 1000000000, 0.06, {
                'metric_type': 'gauge',
                'host_name': 'myhost0',
            }),
            ('nagios.pgsql_backends.db0',  1000000000,   33., {
                'metric_type': 'gauge',
                'host_name': 'myhost0',
                'warn': '180',
                'crit': '190',
                'min':    '0',
                'max':  '200',
            }),
            ('nagios.pgsql_backends.db1',  1000000000,    1., {
                'metric_type': 'gauge',
                'host_name': 'myhost0',
                'warn': '150',
                'crit': '190',
                'min':    '0',
                'max':  '200',
            }),
            ('nagios.pgsql_backends.db2',  1000000000,    0., {
                'metric_type': 'gauge',
                'host_name': 'myhost0',
                'warn': '120',
                'crit': '290',
                'min':    '1',
                'max':  '200',
            }),
            ('nagios.pgsql_backends.db3',  1000000000,    0., {
                'metric_type': 'gauge',
                'host_name': 'myhost0',
                'warn': '110',
                'crit': '195',
                'min':    '5',
                'max':  '100',
            }),
        ]
        expected_output.sort(key=point_sorter)

        self._write_log(('\t'.join(data) for data in log_data))        

        actual_output = dogstream.check(self.agent_config, move_end=False)['dogstream']
        actual_output.sort(key=point_sorter)

        self.assertEquals(expected_output, actual_output)
    
    def test_service_perfdata_special_cases(self):
        from checks.datadog import NagiosServicePerfData

        self._write_nagios_config([
            "service_perfdata_file=%s" % self.log_file.name,
            "service_perfdata_file_template=DATATYPE::SERVICEPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tSERVICEDESC::$SERVICEDESC$\tSERVICEPERFDATA::$SERVICEPERFDATA$\tSERVICECHECKCOMMAND::$SERVICECHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$\tSERVICESTATE::$SERVICESTATE$\tSERVICESTATETYPE::$SERVICESTATETYPE$",
        ])

        dogstream = Dogstreams.init(self.logger, self.agent_config)
        self.assertEquals([NagiosServicePerfData], [d.__class__ for d in dogstream.dogstreams])

        log_data = [
            (   "DATATYPE::SERVICEPERFDATA",
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
            )
        ]
        
        expected_output = [
            ('nagios.disk_space', 1000000000, 5477., {
                'metric_type': 'gauge',
                'host_name': 'myhost2',
                'device_name': '/',
                'unit': 'MB',
                'warn': '6450',
                'crit': '7256',
                'min': '0',
                'max': '8063',
            }),
            ('nagios.disk_space', 1000000000, 0., {
                'metric_type': 'gauge',
                'host_name': 'myhost2',
                'device_name': '/dev',
                'unit': 'MB',
                'warn': '2970',
                'crit': '3341',
                'min': '0',
                'max': '3713',
            }),
            ('nagios.disk_space', 1000000000, 0., {
                'metric_type': 'gauge',
                'host_name': 'myhost2',
                'device_name': '/dev/shm',
                'unit': 'MB',
                'warn': '3080',
                'crit': '3465',
                'min': '0',
                'max': '3851',
            }),
            ('nagios.disk_space', 1000000000, 0., {
                'metric_type': 'gauge',
                'host_name': 'myhost2',
                'device_name': '/var/run',
                'unit': 'MB',
                'warn': '3080',
                'crit': '3465',
                'min': '0',
                'max': '3851',
            }),
            ('nagios.disk_space', 1000000000, 0., {
                'metric_type': 'gauge',
                'host_name': 'myhost2',
                'device_name': '/var/lock',
                'unit': 'MB',
                'warn': '3080',
                'crit': '3465',
                'min': '0',
                'max': '3851',
            }),
            ('nagios.disk_space', 1000000000, 0., {
                'metric_type': 'gauge',
                'host_name': 'myhost2',
                'device_name': '/lib/init/rw',
                'unit': 'MB',
                'warn': '3080',
                'crit': '3465',
                'min': '0',
                'max': '3851',
            }),
            ('nagios.disk_space', 1000000000, 290., {
                'metric_type': 'gauge',
                'host_name': 'myhost2',
                'device_name': '/mnt',
                'unit': 'MB',
                'warn': '338636',
                'crit': '380966',
                'min': '0',
                'max': '423296',
            }),
            ('nagios.disk_space', 1000000000, 39812., {
                'metric_type': 'gauge',
                'host_name': 'myhost2',
                'device_name': '/data',
                'unit': 'MB',
                'warn': '40940',
                'crit': '46057',
                'min': '0',
                'max': '51175',
            }),
        ]
        expected_output.sort(key=point_sorter)

        self._write_log(('\t'.join(data) for data in log_data))        

        actual_output = dogstream.check(self.agent_config, move_end=False)['dogstream']
        actual_output.sort(key=point_sorter)

        self.assertEquals(expected_output, actual_output)
    def test_host_perfdata(self):
        from checks.datadog import NagiosHostPerfData

        self._write_nagios_config([
            "host_perfdata_file=%s" % self.log_file.name,
            "host_perfdata_file_template=DATATYPE::HOSTPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\tHOSTPERFDATA::$HOSTPERFDATA$\tHOSTCHECKCOMMAND::$HOSTCHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$",
        ])

        dogstream = Dogstreams.init(self.logger, self.agent_config)
        self.assertEquals([NagiosHostPerfData], [d.__class__ for d in dogstream.dogstreams])

        log_data = [
            ("DATATYPE::HOSTPERFDATA", 
             "TIMET::1000000010", 
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
            ('nagios.host.rta', 1000000010, 0.978, {
                'metric_type': 'gauge',
                'host_name': 'myhost1',
                'unit': 'ms',
                'warn': '5000.000000',
                'crit': '5000.000000',
                'min': '0.000000'
            }),
            ('nagios.host.pl',  1000000010, 0., {
                'metric_type': 'gauge',
                'host_name': 'myhost1',
                'unit': '%',
                'warn': '100',
                'crit': '100',
                'min': '0'
            }),
        ]
        expected_output.sort(key=point_sorter)

        self._write_log(('\t'.join(data) for data in log_data))        

        actual_output = dogstream.check(self.agent_config, move_end=False)['dogstream']
        actual_output.sort(key=point_sorter)

        self.assertEquals(expected_output, actual_output)


        
if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s")
    unittest.main()
