# stdlib
import logging
import pprint
import random
import time

# 3p
from nose.plugins.attrib import attr
import redis

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest, load_check

logger = logging.getLogger()

MAX_WAIT = 20
NOAUTH_PORT = 16379
AUTH_PORT = 26379
SLAVE_HEALTHY_PORT = 36379
SLAVE_UNHEALTHY_PORT = 46379
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

        # Service metadata
        service_metadata = r.get_service_metadata()
        service_metadata_count = len(service_metadata)
        self.assertTrue(service_metadata_count > 0)
        for meta_dict in service_metadata:
            assert meta_dict

    def test_redis_replication_link_metric(self):
        metric_name = 'redis.replication.master_link_down_since_seconds'
        r = load_check('redisdb', {}, {})

        def extract_metric(instance):
            r.check(instance)
            metrics = [m for m in r.get_metrics() if m[0] == metric_name]
            return (metrics and metrics[0]) or None

        # Healthy host
        metric = extract_metric({
            'host': 'localhost',
            'port': SLAVE_HEALTHY_PORT
        })
        assert metric, "%s metric not returned" % metric_name
        self.assertEqual(metric[2], 0, "Value of %s should be 0" % metric_name)

        # Unhealthy host
        time.sleep(5)  # Give time for the replication failure metrics to build up
        metric = extract_metric({
            'host': 'localhost',
            'port': SLAVE_UNHEALTHY_PORT
        })
        self.assert_(metric[2] > 0, "Value of %s should be greater than 0" % metric_name)

    def test_redis_replication_service_check(self):
        check_name = 'redis.replication.master_link_status'
        r = load_check('redisdb', {}, {})

        def extract_check(instance):
            r.check(instance)
            checks = [c for c in r.get_service_checks() if c['check'] == check_name]
            return (checks and checks[0]) or None

        # Healthy host
        time.sleep(5)  # Give time for the replication failure metrics to build up
        check = extract_check({
            'host': 'localhost',
            'port': SLAVE_HEALTHY_PORT
        })
        assert check, "%s service check not returned" % check_name
        self.assertEqual(check['status'], AgentCheck.OK, "Value of %s service check should be OK" % check_name)

        # Unhealthy host
        check = extract_check({
            'host': 'localhost',
            'port': SLAVE_UNHEALTHY_PORT
        })
        self.assertEqual(check['status'], AgentCheck.CRITICAL, "Value of %s service check should be CRITICAL" % check_name)

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

        # Tweaking Redis's config to have the test run faster
        old_sl_thresh = db.config_get('slowlog-log-slower-than')['slowlog-log-slower-than']
        db.config_set('slowlog-log-slower-than', 0)

        db.flushdb()

        # Generate some slow commands
        for i in range(100):
            db.lpush(test_key, random.random())

        db.sort(test_key)

        self.assertTrue(db.slowlog_len() > 0)

        db.config_set('slowlog-log-slower-than', old_sl_thresh)

        self.run_check({"init_config": {}, "instances": [instance]})

        assert self.metrics, "No metrics returned"
        self.assertMetric("redis.slowlog.micros.max", tags=["command:SORT",
            "redis_host:localhost", "redis_port:{0}".format(port)])

    def test_custom_slowlog(self):
        port = NOAUTH_PORT
        test_key = "testkey"
        instance = {
            'host': 'localhost',
            'port': port,
            'slowlog-max-len': 1
        }

        db = redis.Redis(port=port, db=14)  # Datadog's test db

        # Tweaking Redis's config to have the test run faster
        old_sl_thresh = db.config_get('slowlog-log-slower-than')['slowlog-log-slower-than']
        db.config_set('slowlog-log-slower-than', 0)

        db.flushdb()

        # Generate some slow commands
        for i in range(100):
            db.lpush(test_key, random.random())

        db.sort(test_key)

        db.config_set('slowlog-log-slower-than', old_sl_thresh)

        self.assertTrue(db.slowlog_len() > 0)

        self.run_check({"init_config": {}, "instances": [instance]})

        assert self.metrics, "No metrics returned"

        # Let's check that we didn't put more than one slowlog entry in the
        # payload, as specified in the above agent configuration
        self.assertMetric("redis.slowlog.micros.count", tags=["command:SORT",
            "redis_host:localhost", "redis_port:{0}".format(port)], value=1.0)

    def _sort_metrics(self, metrics):
        def sort_by(m):
            return m[0], m[1], m[3]
        return sorted(metrics, key=sort_by)
