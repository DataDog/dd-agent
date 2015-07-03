# stdlib
import calendar
from datetime import datetime
import logging
import os
import re
from tempfile import gettempdir, NamedTemporaryFile
import time
import unittest

# project
from checks.datadog import Dogstreams, EventDefaults

log = logging.getLogger('datadog.test')


def parse_ancient_function_plugin(logger, line):
    """Ancient stateless parser"""
    res = line.split()
    res[3] = {'metric_type': 'gauge'}


def parse_function_plugin(logger, line, state):
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


class ParseClassPlugin(object):
    """Class-based stateful parser"""
    def __init__(self, logger=None, user_args=(), **kwargs):
        self.logger = logger
        self.args = '.'.join(user_args)
        self.acc = 0
        self.logger.info('Completed initialization')

    def parse_line(self, line):
        self.logger.info('Parsing line %r; counter is %r', line, self.acc)
        self.acc += 1
        res = line.split()
        res[0] = self.args + ':' + res[0]
        res[2] = self.acc
        res[3] = {'metric_type': 'counter'}
        return tuple(res)


log_event_pattern = re.compile("".join([
    r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ",  # iso timestamp
    r"\[(?P<alert_type>(ERROR)|(RECOVERY))\] - ",  # alert type
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
                ('test.metric.a', 1000000000, 42, self.counter),
                ('test.metric.a', 1000000005, 27, self.counter),
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

    def test_dogstream_ancient_function_plugin(self):
        """Ensure that pre-stateful plugins still work"""
        log_data = [
            'test.metric.simple 1000000000 1 metric_type=gauge',
            'test.metric.simple 1100000000 1 metric_type=gauge'
        ]
        expected_output = {
            "dogstream": [
                ('test.metric.simple', 1000000000, 1, self.gauge),
                ('test.metric.simple', 1100000000, 1, self.gauge)]
        }
        self._write_log(log_data)
        plugdog = Dogstreams.init(self.logger, {'dogstreams': '{0}:{1}:parse_ancient_function_plugin'.format(self.log_file.name, __name__)})
        actual_output = plugdog.check(self.config, move_end=False)

    def test_dogstream_log_path_globbing(self):
        """Make sure that globbed dogstream logfile matching works."""
        # Create a tmpfile to serve as a prefix for the other temporary
        # files we'll be globbing.
        first_tmpfile = NamedTemporaryFile()
        tmp_fprefix = os.path.basename(first_tmpfile.name)
        all_tmp_filenames = set([first_tmpfile.name])
        # We stick the file objects in here to avoid garbage collection (and
        # tmpfile deletion). Not sure why this was happening, but it's working
        # with this hack in.
        avoid_gc = []
        for i in range(3):
            new_tmpfile = NamedTemporaryFile(prefix=tmp_fprefix)
            all_tmp_filenames.add(new_tmpfile.name)
            avoid_gc.append(new_tmpfile)
        dogstream_glob = os.path.join(gettempdir(), tmp_fprefix + '*')
        paths = Dogstreams._get_dogstream_log_paths(dogstream_glob)
        self.assertEqual(set(paths), all_tmp_filenames)

    def test_dogstream_function_plugin(self):
        """Ensure that non-class-based stateful plugins work"""
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

        statedog = Dogstreams.init(self.logger, {'dogstreams': '{0}:{1}:parse_function_plugin'.format(self.log_file.name, __name__)})
        actual_output = statedog.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)

    def test_dogstream_new_plugin(self):
        """Ensure that class-based stateful plugins work"""
        log_data = [
            'test.metric.accumulator 1000000000 1 metric_type=counter',
            'test.metric.accumulator 1100000000 1 metric_type=counter'
        ]
        expected_output = {
            "dogstream": [
                ('foo.bar:test.metric.accumulator', 1000000000, 1, self.counter),
                ('foo.bar:test.metric.accumulator', 1100000000, 2, self.counter)]
        }
        self._write_log(log_data)

        statedog = Dogstreams.init(self.logger, {'dogstreams': '{0}:{1}:ParseClassPlugin:foo:bar'.format(self.log_file.name, __name__)})
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

        dogstream = Dogstreams.init(self.logger, {'dogstreams': '{0}:{1}:parse_events'.format(self.log_file.name, __name__)})
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

        dogstream = Dogstreams.init(self.logger, {'dogstreams': '{0}:{1}:repr_event_parser'.format(self.log_file.name, __name__)})
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
            "dogstreamEvents": [
                {
                    "timestamp": cassandra.parse_date("2012-05-12 21:10:48,058"),
                    "msg_title": "Compacting [SSTableReader(path='/var/cassandra/data/test_data/series-hc-6528-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6531-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6529-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6530-Data.db')]"[0:common.MAX_TITLE_LEN],
                    "msg_text": "Compacting [SSTableReader(path='/var/cassandra/data/test_data/series-hc-6528-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6531-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6529-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6530-Data.db')]",
                    "alert_type": alert_type,
                    "auto_priority": 0,
                    "event_type": event_type,
                    "aggregation_key": event_object,
                    "event_object": event_object,
                },  {
                    "timestamp": cassandra.parse_date("2012-05-12 21:10:54,851"),
                    "msg_title": "Compacted to [/var/cassandra/a-hc-65-Data.db,].  102,079,134 to 101,546,397",
                    "alert_type": alert_type,
                    "auto_priority": 0,
                    "event_type": event_type,
                    "aggregation_key": event_object,
                    "event_object": event_object,
                },  {
                    "timestamp": cassandra.parse_date("2012-05-13 13:15:01,927"),
                    "msg_title": "Compacting [SSTableReader(path='/var/cassandra/data/test_data/series-hc-6527-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6522-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6532-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6517-Data.db')]"[0:common.MAX_TITLE_LEN],
                    "msg_text": "Compacting [SSTableReader(path='/var/cassandra/data/test_data/series-hc-6527-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6522-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6532-Data.db'), SSTableReader(path='/var/cassandra/data/test_data/series-hc-6517-Data.db')]",
                    "alert_type": alert_type,
                    "event_type": event_type,
                    "auto_priority": 0,
                    "aggregation_key": event_object,
                    "event_object": event_object,
                },  {
                    "timestamp": cassandra.parse_date("2012-05-13 13:27:17,685"),
                    "msg_title": "Compacting large row test_data/series:6c6f677c32 (782001077 bytes) incrementally",
                    "alert_type": alert_type,
                    "event_type": event_type,
                    "auto_priority": 0,
                    "aggregation_key": event_object,
                    "event_object": event_object,
                },  {
                    "timestamp": cassandra.parse_date(datetime.utcnow().strftime("%Y-%m-%d") + " 13:27:17,685"),
                    "msg_title": "Compacting large row test_data/series:6c6f677c32 (782001077 bytes) incrementally",
                    "alert_type": alert_type,
                    "event_type": event_type,
                    "auto_priority": 0,
                    "aggregation_key": event_object,
                    "event_object": event_object,
                },
            ]
        }

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
            "dogstreamEvents": [
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
            ]
        }
        self._write_log(log_data.split("\n"))

        dogstream = Dogstreams.init(self.logger, {'dogstreams': '%s:dogstream.supervisord_log:parse_supervisord' % self.log_file.name})
        actual_output = dogstream.check(self.config, move_end=False)
        self.assertEquals(expected_output, actual_output)
