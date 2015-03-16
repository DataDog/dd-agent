import logging
import unittest
from nose.plugins.attrib import attr
import time
import pprint
import redis
import random

from tests.common import load_check, AgentCheckTest
logger = logging.getLogger()

MAX_WAIT = 20
NOAUTH_PORT = 16379
AUTH_PORT = 26379
DEFAULT_PORT = 6379
MISSING_KEY_TOLERANCE = 0.5


@attr(requires='redis')
class TestRedis(AgentCheckTest):
    CHECK_NAME = "redisdb"

    def test_redis_auth(self):
        # correct password
        r = load_check('redisdb', {}, {})
        instance = {
            'host': 'localhost',
            'port': AUTH_PORT,
            'password': 'datadog-is-devops-best-friend'
        }
        r.check(instance)
        metrics = self._sort_metrics(r.get_metrics())
        assert len(metrics) > 0, "No metrics returned"

        # wrong passwords
        instances = [
            {
                'host': 'localhost',
                'port': AUTH_PORT,
                'password': ''
            },
            {
                'host': 'localhost',
                'port': AUTH_PORT,
                'password': 'badpassword'
            }
        ]

        r = load_check('redisdb', {}, {})
        try:
            r.check(instances[0])
        except Exception as e:
            self.assertTrue(
                # 2.8
                'noauth authentication required' in str(e).lower()
                # previously
                or 'operation not permitted' in str(e).lower(),
                str(e))

        r = load_check('redisdb', {}, {})
        try:
            r.check(instances[1])
        except Exception as e:
            self.assertTrue('invalid password' in str(e).lower(), str(e))

    def test_redis_default(self):
        port = NOAUTH_PORT

        instance = {
            'host': 'localhost',
            'port': port
        }

        db = redis.Redis(port=port, db=14)  # Datadog's test db
        db.flushdb()
        db.set("key1", "value")
        db.set("key2", "value")
        db.setex("expirekey", "expirevalue", 1000)

        r = load_check('redisdb', {}, {})
        r.check(instance)
        metrics = self._sort_metrics(r.get_metrics())
        assert metrics, "No metrics returned"

        # Assert we have values, timestamps and tags for each metric.
        for m in metrics:
            assert isinstance(m[1], int)    # timestamp
            assert isinstance(m[2], (int, float, long))  # value
            tags = m[3]["tags"]
            expected_tags = ["redis_host:localhost", "redis_port:%s" % port]
            for e in expected_tags:
                assert e in tags

        def assert_key_present(expected, present, tolerance):
            "Assert we have the rest of the keys (with some tolerance for missing keys)"
            e = set(expected)
            p = set(present)
            assert len(e - p) < tolerance * len(e), pprint.pformat((p, e - p))

        # gauges collected?
        remaining_keys = [m[0] for m in metrics]
        expected = r.GAUGE_KEYS.values()
        assert_key_present(expected, remaining_keys, MISSING_KEY_TOLERANCE)

        # Assert that the keys metrics are tagged by db. just check db0, since
        # it's the only one we can guarantee is there.
        db_metrics = self._sort_metrics(
            [m for m in metrics if m[0] in ['redis.keys', 'redis.expires'] and "redis_db:db14" in m[3]["tags"]])
        self.assertEquals(2, len(db_metrics))

        self.assertEquals('redis.expires', db_metrics[0][0])
        self.assertEquals(1, db_metrics[0][2])

        self.assertEquals('redis.keys', db_metrics[1][0])
        self.assertEquals(3, db_metrics[1][2])

        # Service checks
        service_checks = r.get_service_checks()
        service_checks_count = len(service_checks)
        self.assertTrue(isinstance(service_checks, list))
        self.assertTrue(service_checks_count > 0)
        self.assertEquals(
            len([sc for sc in service_checks if sc['check'] == "redis.can_connect"]), 1, service_checks)
        # Assert that all service checks have the proper tags: host and port
        self.assertEquals(
            len([sc for sc in service_checks if "redis_host:localhost" in sc['tags']]),
            service_checks_count,
            service_checks)
        self.assertEquals(
            len([sc for sc in service_checks if "redis_port:%s" % port in sc['tags']]),
            service_checks_count,
            service_checks)

        # Run one more check and ensure we get total command count
        # and other rates
        time.sleep(5)
        r.check(instance)
        metrics = self._sort_metrics(r.get_metrics())
        keys = [m[0] for m in metrics]
        assert 'redis.net.commands' in keys

    def test_redis_repl(self):
        master_instance = {
            'host': 'localhost',
            'port': NOAUTH_PORT
        }

        slave_instance = {
            'host': 'localhost',
            'port': AUTH_PORT,
            'password': 'datadog-is-devops-best-friend'
        }

        repl_metrics = [
            'redis.replication.delay',
            'redis.replication.backlog_histlen',
            'redis.replication.delay',
            'redis.replication.master_repl_offset',
        ]

        master_db = redis.Redis(port=NOAUTH_PORT, db=14)
        slave_db = redis.Redis(port=AUTH_PORT, password=slave_instance['password'], db=14)
        master_db.flushdb()

        # Assert that the replication works
        master_db.set('replicated:test', 'true')
        self.assertEquals(slave_db.get('replicated:test'), 'true')

        r = load_check('redisdb', {}, {})
        r.check(master_instance)
        metrics = self._sort_metrics(r.get_metrics())

        # Assert the presence of replication metrics
        keys = [m[0] for m in metrics]
        assert [x in keys for x in repl_metrics]

    def test_slowlog(self):
        port = NOAUTH_PORT
        test_key = "testkey"
        instance = {
            'host': 'localhost',
            'port': port
        }


        db = redis.Redis(port=port, db=14)  # Datadog's test db
        db.flushdb()

        # Generate some slow commands
        for i in range(100000):
            db.lpush(test_key, random.random())

        db.sort(test_key)

        self.assertTrue(db.slowlog_len() > 0)

        self.run_check({"init_config": {}, "instances": [instance]})

        assert self.metrics, "No metrics returned"
        self.assertMetric("redis.slowlog.micros.max", tags=["command:SORT",
            "redis_host:localhost", "redis_port:{0}".format(port)])


    def _sort_metrics(self, metrics):
        def sort_by(m):
            return m[0], m[1], m[3]
        return sorted(metrics, key=sort_by)

if __name__ == "__main__":
    unittest.main()
