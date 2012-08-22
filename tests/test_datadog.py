import logging
import unittest
from tempfile import NamedTemporaryFile
import re
import os

from checks.datadog import Dogstreams, EventDefaults, point_sorter

log = logging.getLogger('datadog.test')
NAGIOS_TEST_HOST = os.path.join(os.path.dirname(__file__), "host-perfdata")
NAGIOS_TEST_SVC = os.path.join(os.path.dirname(__file__), "service-perfdata")
NAGIOS_TEST_HOST_TEMPLATE="[HOSTPERFDATA]\t$TIMET$\t$HOSTNAME$\t$HOSTEXECUTIONTIME$\t$HOSTOUTPUT$\t$HOSTPERFDATA$"
NAGIOS_TEST_SVC_TEMPLATE="[SERVICEPERFDATA]\t$TIMET$\t$HOSTNAME$\t$SERVICEDESC$\t$SERVICEEXECUTIONTIME$\t$SERVICELATENCY$\t$SERVICEOUTPUT$\t$SERVICEPERFDATA$"

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


import time
from datetime import datetime
import calendar

log_event_pattern = re.compile("".join([
    r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ", # iso timestamp
    r"\[(?P<alert_type>(ERROR)|(RECOVERY))\] - ", # alert type
    r"(?P<msg_title>(?P<host>[^ ]*).*)"
]))
alert_types = {
    "ERROR": "error",
    "RECOVERY": "success"
}
def parse_events(logger, line):
    """ Expecting lines like this: 
        2012-05-14 12:46:01 [ERROR] - host0 is down (broke its collarbone)
    """
    match = log_event_pattern.match(line)
    if match:
        groups = match.groupdict()
        groups.update({
            'alert_type': alert_types.get(groups['alert_type'], ''),
            'timestamp':  calendar.timegm(datetime.strptime(groups['timestamp'], '%Y-%m-%d %H:%M:%S').timetuple()),
            'msg_text': line
            })

        return groups
    else:
        return None

def repr_event_parser(logger, line):
    return eval(line)

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
            'check_freq': 5,
        }
        log.info("Test config: %s" % self.config)
        self.dogstream = Dogstreams.init(self.logger, self.config)
        self.maxDiff = None
    
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

        statedog = Dogstreams.init(self.logger, {'dogstreams': '%s:tests.test_datadog:parse_stateful' % self.log_file.name})
        actual_output = statedog.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)

    def test_dogstream_events(self):
        log_data = [
            '2012-05-14 12:46:01 [ERROR] - host0 is down (broke its collarbone)',
            '2012-05-14 12:48:07 [ERROR] - host1 is down (got a bloody nose)',
            '2012-05-14 12:52:03 [RECOVERY] - host0 is up (collarbone healed)',
            '2012-05-14 12:59:09 [RECOVERY] - host1 is up (nose stopped bleeding)',
        ]
        expected_output = {
            "dogstreamEvents": [
                {
                    "timestamp": 1336999561,
                    "alert_type": "error",
                    "host": "host0",
                    "msg_title": "host0 is down (broke its collarbone)",
                    "msg_text": "2012-05-14 12:46:01 [ERROR] - host0 is down (broke its collarbone)",
                    "event_type": EventDefaults.EVENT_TYPE,
                    "aggregation_key": EventDefaults.EVENT_OBJECT,
                    "event_object": EventDefaults.EVENT_OBJECT,
                },

                {
                    "timestamp": 1336999687,
                    "alert_type": "error",
                    "host": "host1",
                    "msg_title": "host1 is down (got a bloody nose)",
                    "msg_text": "2012-05-14 12:48:07 [ERROR] - host1 is down (got a bloody nose)",
                    "event_type": EventDefaults.EVENT_TYPE,
                    "aggregation_key": EventDefaults.EVENT_OBJECT,
                    "event_object": EventDefaults.EVENT_OBJECT,
                },

                {
                    "timestamp": 1336999923,
                    "alert_type": "success",
                    "host": "host0",
                    "msg_title": "host0 is up (collarbone healed)",
                    "msg_text": "2012-05-14 12:52:03 [RECOVERY] - host0 is up (collarbone healed)",
                    "event_type": EventDefaults.EVENT_TYPE,
                    "aggregation_key": EventDefaults.EVENT_OBJECT,
                    "event_object": EventDefaults.EVENT_OBJECT,
                },

                {
                    "timestamp": 1337000349,
                    "alert_type": "success",
                    "host": "host1",
                    "msg_title": "host1 is up (nose stopped bleeding)",
                    "msg_text": "2012-05-14 12:59:09 [RECOVERY] - host1 is up (nose stopped bleeding)",
                    "event_type": EventDefaults.EVENT_TYPE,
                    "aggregation_key": EventDefaults.EVENT_OBJECT,
                    "event_object": EventDefaults.EVENT_OBJECT,
                },

            ]
        }

        self._write_log(log_data)

        dogstream = Dogstreams.init(self.logger, {'dogstreams': '%s:tests.test_datadog:parse_events' % self.log_file.name})
        actual_output = dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)

    def test_dogstream_events_validation(self):
        log_data = [
            {"msg_title": "title", "timestamp": 1336999561},
            {"msg_text": "body", "timestamp": 1336999561},
            {"none of the above": "should get filtered out", "timestamp": 1336999561},
        ]

        expected_output = {
            "dogstreamEvents": [
                {
                    "timestamp": 1336999561,
                    "msg_title": "title",
                    "event_type": EventDefaults.EVENT_TYPE,
                    "aggregation_key": EventDefaults.EVENT_OBJECT,
                    "event_object": EventDefaults.EVENT_OBJECT,
                },

                {
                    "timestamp": 1336999561,
                    "msg_text": "body",
                    "event_type": EventDefaults.EVENT_TYPE,
                    "aggregation_key": EventDefaults.EVENT_OBJECT,
                    "event_object": EventDefaults.EVENT_OBJECT,
                },

            ]
        }

        self._write_log([repr(d) for d in log_data])

        dogstream = Dogstreams.init(self.logger, {'dogstreams': '%s:tests.test_datadog:repr_event_parser' % self.log_file.name})
        actual_output = dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)

    def test_cassandra_parser(self):
        from dogstream import cassandra, common

        log_data = """ INFO [CompactionExecutor:1594] 2012-05-12 21:05:12,924 Saved test_data-Encodings-KeyCache (86400 items) in 85 ms
 INFO [CompactionExecutor:1595] 2012-05-12 21:05:15,144 Saved test_data-Metrics-KeyCache (86400 items) in 96 ms
 INFO [CompactionExecutor:1596] 2012-05-12 21:10:48,058 Compacting [SSTableReader(path='/var/cassandra/data/test_data/series-hc-6528-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6531-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6529-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6530-Data.db')]
 INFO [CompactionExecutor:1596] 2012-05-12 21:10:54,851 Compacted to [/var/cassandra/a-hc-65-Data.db,].  102,079,134 to 101,546,397
 INFO [CompactionExecutor:1598] 2012-05-12 22:05:04,313 Saved test_data-ResourcesMetadata-KeyCache (1 items) in 10 ms
 INFO [CompactionExecutor:1599] 2012-05-12 22:05:14,813 Saved test_data-Encodings-KeyCache (86400 items) in 83 ms
 INFO [CompactionExecutor:1630] 2012-05-13 13:05:44,963 Saved test_data-Metrics-KeyCache (86400 items) in 77 ms
 INFO [CompactionExecutor:1631] 2012-05-13 13:15:01,923 Nothing to compact in data_log.  Use forceUserDefinedCompaction if you wish to force compaction of single sstables (e.g. for tombstone collection)
 INFO [CompactionExecutor:1632] 2012-05-13 13:15:01,927 Compacting [SSTableReader(path='/var/cassandra/data/test_data/series-hc-6527-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6522-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6532-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6517-Data.db')]
 INFO [CompactionExecutor:1632] 2012-05-13 13:27:17,685 Compacting large row test_data/series:6c6f677c32 (782001077 bytes) incrementally
 INFO [CompactionExecutor:34] 2012-05-14 18:00:41,281 Saved test_data-Encodings-KeyCache (86400 items) in 78 ms
 INFO 13:27:17,685 Compacting large row test_data/series:6c6f677c32 (782001077 bytes) incrementally
"""
        alert_type = cassandra.ALERT_TYPES["INFO"]
        event_type = cassandra.EVENT_TYPE
        event_object = EventDefaults.EVENT_OBJECT

        expected_output = {
            "dogstreamEvents":[
            {
                "timestamp": common.parse_date("2012-05-12 21:10:48,058", cassandra.DATE_FORMAT),
                "msg_title": "Compacting [SSTableReader(path='/var/cassandra/data/test_data/series-hc-6528-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6531-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6529-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6530-Data.db')]"[0:common.MAX_TITLE_LEN],
                "msg_text": "Compacting [SSTableReader(path='/var/cassandra/data/test_data/series-hc-6528-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6531-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6529-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6530-Data.db')]",
                "alert_type": alert_type,
                "auto_priority": 0,
                "event_type": event_type,
                "aggregation_key": event_object,
                "event_object": event_object,
            },  {
                "timestamp": common.parse_date("2012-05-12 21:10:54,851", cassandra.DATE_FORMAT),
                "msg_title": "Compacted to [/var/cassandra/a-hc-65-Data.db,].  102,079,134 to 101,546,397",
                "alert_type": alert_type,
                "auto_priority": 0,
                "event_type": event_type,
                "aggregation_key": event_object,
                "event_object": event_object,
            },  {
                "timestamp": common.parse_date("2012-05-13 13:15:01,927", cassandra.DATE_FORMAT),
                "msg_title": "Compacting [SSTableReader(path='/var/cassandra/data/test_data/series-hc-6527-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6522-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6532-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6517-Data.db')]"[0:common.MAX_TITLE_LEN],
                "msg_text": "Compacting [SSTableReader(path='/var/cassandra/data/test_data/series-hc-6527-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6522-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6532-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6517-Data.db')]",
                "alert_type": alert_type,
                "event_type": event_type,
                "auto_priority": 0,
                "aggregation_key": event_object,
                "event_object": event_object,
            },  {
                "timestamp": common.parse_date("2012-05-13 13:27:17,685", cassandra.DATE_FORMAT),
                "msg_title": "Compacting large row test_data/series:6c6f677c32 (782001077 bytes) incrementally",
                "alert_type": alert_type,
                "event_type": event_type,
                "auto_priority": 0,
                "aggregation_key": event_object,
                "event_object": event_object,
            },  {
                "timestamp": common.parse_date(datetime.utcnow().strftime("%Y-%m-%d") + " 13:27:17,685", cassandra.DATE_FORMAT),
                "msg_title": "Compacting large row test_data/series:6c6f677c32 (782001077 bytes) incrementally",
                "alert_type": alert_type,
                "event_type": event_type,
                "auto_priority": 0,
                "aggregation_key": event_object,
                "event_object": event_object,
            },
        ]}

        self._write_log(log_data.split("\n"))

        dogstream = Dogstreams.init(self.logger, {'dogstreams': '%s:dogstream.cassandra:parse_cassandra' % self.log_file.name})
        actual_output = dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)

    def test_supervisord_parser(self):
        from dogstream import supervisord_log
        log_data = """2012-07-16 22:30:48,335 INFO spawned: 'monitor' with pid 20216
2012-07-14 03:02:47,325 INFO success: foo_bar entered RUNNING state, process has stayed up for > than 2 seconds (startsecs)
2012-07-17 02:53:04,600 CRIT Server 'inet_http_server' running without any HTTP authentication checking
2012-07-14 04:54:34,193 WARN received SIGTERM indicating exit request
"""
        event_type = supervisord_log.EVENT_TYPE

        expected_output = {
            "dogstreamEvents":[
                {
                    "alert_type": "info", "event_type": event_type,
                    "aggregation_key": "monitor",
                    "event_object": "monitor",
                    "msg_title": "spawned: 'monitor' with pid 20216",
                    "timestamp": int(time.mktime(datetime(2012, 7, 16, 22, 30, 48).timetuple())),
                }, {
                    "alert_type": "success", "event_type": event_type,
                    "aggregation_key": "foo_bar",
                    "event_object": "foo_bar",
                    "msg_title": "success: foo_bar entered RUNNING state, "
                    "process has stayed up for > than 2 seconds (startsecs)",
                    "timestamp": int(time.mktime(datetime(2012, 7, 14, 3, 2, 47).timetuple())),
                }, {
                    "alert_type": "error", "event_type": event_type,
                    "aggregation_key": "inet_http_server",
                    "event_object": "inet_http_server",
                    "msg_title": "Server 'inet_http_server' running without any HTTP authentication checking",
                    "timestamp": int(time.mktime(datetime(2012, 7, 17, 2, 53, 4).timetuple())),
                }, {
                    "alert_type": "warning", "event_type": event_type,
                    "aggregation_key": "SIGTERM",
                    "event_object": "SIGTERM",
                    "msg_title": "received SIGTERM indicating exit request",
                    "timestamp": int(time.mktime(datetime(2012, 7, 14, 4, 54, 34).timetuple())),
                },
            ]}
        self._write_log(log_data.split("\n"))

        dogstream = Dogstreams.init(self.logger, {'dogstreams': '%s:dogstream.supervisord_log:parse_supervisord' % self.log_file.name})
        actual_output = dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)

class TestNagiosPerfData(TailTestCase):
    def setUp(self):
        TailTestCase.setUp(self)
        self.nagios_config = NamedTemporaryFile()
        self.nagios_config.flush()

        self.agent_config = {
            'nagios_perf_cfg': self.nagios_config.name,
            'check_freq': 5,
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

    def test_alt_service_perfdata(self):
        from checks.datadog import NagiosServicePerfData

        self._write_nagios_config([
            "service_perfdata_file=%s" % NAGIOS_TEST_SVC,
            "service_perfdata_file_template=%s" % NAGIOS_TEST_SVC_TEMPLATE,
        ])

        dogstream = Dogstreams.init(self.logger, self.agent_config)
        self.assertEquals([NagiosServicePerfData], [d.__class__ for d in dogstream.dogstreams])
        actual_output = dogstream.check(self.agent_config, move_end=False)

        expected_output = {'dogstream': [('nagios.current_users.users', 1339511440, 1.0, {'metric_type': 'gauge', 'warn': '20', 'host_name': 'localhost', 'crit': '50', 'min': '0'}), ('nagios.ping.pl', 1339511500, 0.0, {'warn': '20', 'metric_type': 'gauge', 'host_name': 'localhost', 'min': '0', 'crit': '60', 'unit': '%'}), ('nagios.ping.rta', 1339511500, 0.065, {'warn': '100.000000', 'metric_type': 'gauge', 'host_name': 'localhost', 'min': '0.000000', 'crit': '500.000000', 'unit': 'ms'}), ('nagios.root_partition', 1339511560, 2470.0, {'min': '0', 'max': '7315', 'device_name': '/', 'warn': '5852', 'metric_type': 'gauge', 'host_name': 'localhost', 'crit': '6583', 'unit': 'MB'})]}
        self.assertEquals(expected_output, actual_output)

    def test_alt_host_perfdata(self):
        from checks.datadog import NagiosHostPerfData

        self._write_nagios_config([
            "host_perfdata_file=%s" % NAGIOS_TEST_HOST,
            "host_perfdata_file_template=%s" % NAGIOS_TEST_HOST_TEMPLATE,
        ])

        dogstream = Dogstreams.init(self.logger, self.agent_config)
        self.assertEquals([NagiosHostPerfData], [d.__class__ for d in dogstream.dogstreams])
        actual_output = dogstream.check(self.agent_config, move_end=False)

        expected_output = {'dogstream': [('nagios.host.pl', 1339511440, 0.0, {'warn': '80', 'metric_type': 'gauge', 'host_name': 'localhost', 'min': '0', 'crit': '100', 'unit': '%'}), ('nagios.host.rta', 1339511440, 0.048, {'warn': '3000.000000', 'metric_type': 'gauge', 'host_name': 'localhost', 'min': '0.000000', 'crit': '5000.000000', 'unit': 'ms'})]}
        self.assertEquals(expected_output, actual_output)

if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s")
    unittest.main()
