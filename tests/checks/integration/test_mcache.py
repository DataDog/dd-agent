# stdlib
import os
from subprocess import PIPE, Popen
import time

# 3p
import memcache
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest

GAUGES = [
    "total_items",
    "curr_items",
    "limit_maxbytes",
    "uptime",
    "bytes",
    "curr_connections",
    "connection_structures",
    "threads",
    "pointer_size",

    # Computed metrics
    "get_hit_percent",
    "fill_percent",
    "avg_item_size"
]

RATES = [
    "rusage_user",
    "rusage_system",
    "cmd_get",
    "cmd_set",
    "cmd_flush",
    "get_hits",
    "get_misses",
    "delete_misses",
    "delete_hits",
    "evictions",
    "bytes_read",
    "bytes_written",
    "cas_misses",
    "cas_hits",
    "cas_badval",
    "total_connections"
]

SERVICE_CHECK = 'memcache.can_connect'

PORT = 11211


@attr(requires='memcache')
class TestMemCache(AgentCheckTest):

    CHECK_NAME = "mcache"

    def setUp(self):
        c = memcache.Client(["localhost:{0}".format(PORT)])
        c.set("foo", "bar")
        c.get("foo")

    def testCoverage(self):
        config = {
            'init_config': {},
            'instances': [
                {'url': "localhost"},
                {'url': "localhost", 'port': PORT, 'tags': ['instance:mytag']},
                {'url': "localhost", 'port': PORT, 'tags': ['foo']},
                {'socket': "foo/bar"}
            ]
        }

        self.assertRaises(Exception, self.run_check, config)

        tag_set = [
            ["url:localhost:11211"],
            ["url:localhost:11211", "instance:mytag"],
            ["url:localhost:11211", "foo"]
        ]

        for tags in tag_set:
            for m in GAUGES:
                self.assertMetric("memcache.{0}".format(m), tags=tags, count=1)

        good_service_check_tags = ["host:localhost", "port:{0}".format(PORT)]
        bad_service_check_tags = ["host:unix", "port:foo/bar"]

        self.assertServiceCheck(
            SERVICE_CHECK, status=AgentCheck.OK,
            tags=good_service_check_tags, count=3)
        self.assertServiceCheck(
            SERVICE_CHECK, status=AgentCheck.CRITICAL,
            tags=bad_service_check_tags, count=1)

        self.coverage_report()

        config = {
            'init_config': {},
            'instances': [
                {'url': "localhost"},
                {'url': "localhost", 'port': PORT, 'tags': ['instance:mytag']},
                {'url': "localhost", 'port': PORT, 'tags': ['foo']},
            ]
        }

        self.run_check_twice(config, force_reload=True)
        for tags in tag_set:
            for m in GAUGES:
                self.assertMetric("memcache.{0}".format(m), tags=tags, count=1)
            for m in RATES:
                self.assertMetric(
                    "memcache.{0}_rate".format(m), tags=tags, count=1)

        good_service_check_tags = ["host:localhost", "port:{0}".format(PORT)]

        self.assertServiceCheck(
            SERVICE_CHECK, status=AgentCheck.OK,
            tags=good_service_check_tags, count=3)

        self.coverage_report()

    def _countConnections(self, port):
        pid = os.getpid()
        p1 = Popen(
            ['lsof', '-a', '-p%s' % pid, '-i4'], stdout=PIPE)
        p2 = Popen(["grep", ":%s" % port], stdin=p1.stdout, stdout=PIPE)
        p3 = Popen(["wc", "-l"], stdin=p2.stdout, stdout=PIPE)
        output = p3.communicate()[0]
        return int(output.strip())

    def testConnectionLeaks(self):
        for i in range(3):
            # Count open connections to localhost:11211, should be 0
            self.assertEquals(self._countConnections(11211), 0)
            new_conf = {'init_config': {}, 'instances': [
                {'url': "localhost"}]
            }
            self.run_check(new_conf)
            # Verify that the count is still 0
            self.assertEquals(self._countConnections(11211), 0)

    def testMemoryLeak(self):
        config = {
            'init_config': {},
            'instances': [
                {'url': "localhost"},
                {'url': "localhost", 'port': PORT, 'tags': ['instance:mytag']},
                {'url': "localhost", 'port': PORT, 'tags': ['foo']},
            ]
        }

        self.run_check(config)

        import gc
        if not self.is_travis():
            gc.set_debug(gc.DEBUG_LEAK)
        gc.collect()
        try:
            start = len(gc.garbage)
            for i in range(10):
                self.run_check(config)
                time.sleep(0.3)
                self.check.get_metrics()

            end = len(gc.garbage)
            self.assertEquals(end - start, 0, gc.garbage)
        finally:
            gc.set_debug(0)
