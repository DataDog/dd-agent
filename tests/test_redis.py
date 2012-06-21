"""
Redis check tests.
"""
import logging
import unittest
import subprocess
import time
import redis

from checks.db.redisDb import Redis as RedisCheck

logger = logging.getLogger()

MAX_WAIT = 20
NOAUTH_PORT = 16379
AUTH_PORT = 26379

class TestRedis(unittest.TestCase):

    def wait4(self, p, pattern):
        """Waits until a specific pattern shows up in the stdout
        """
        out = p.stdout
        loop = 0
        while True:
            l = out.readline()
            if l.find(pattern) > -1:
                break
            else:
                time.sleep(0.1)
                loop += 1
                if loop >= MAX_WAIT:
                    break
    def setUp(self):
        self.redis_noauth = subprocess.Popen(["redis-server", "tests/redisnoauth.cfg"], stdout=subprocess.PIPE)
        self.wait4(self.redis_noauth, "The server is now ready to accept connections")
        self.redis_auth = subprocess.Popen(["redis-server", "tests/redisauth.cfg"], stdout=subprocess.PIPE)
        self.wait4(self.redis_auth, "The server is now ready to accept connections")

    def tearDown(self):
        self.redis_noauth.terminate()
        self.redis_auth.terminate()

    def test_redis_auth(self):
        # Test connection with password
        r = RedisCheck(logger)
        # correct password
        metrics = self._sort_metrics(r.check({"redis_urls": "datadog-is-devops-best-friend@localhost:%s" % AUTH_PORT}))
        assert len(metrics) > 0, "No metrics returned"
        del r, metrics

        # wrong passwords
        for u in ("@localhost:%s" % AUTH_PORT, "localhost:%s" % AUTH_PORT, "badpassword@localhost:%s" % AUTH_PORT):
            r = RedisCheck(logger)
            metrics = self._sort_metrics(r.check({"redis_urls": u}))
            assert len(metrics) == 0, "Should have failed with bad password; got %s instead" % metrics
            del r, metrics

    def test_redis_default(self):
        # Base test, uses the noauth instance
        db = redis.Redis(port=NOAUTH_PORT, db=14) # Datadog's test db
        db.flushdb()
        db.set("key1", "value")
        db.set("key2", "value")
        db.setex("expirekey", "expirevalue", 1000)
        
        r = RedisCheck(logger)
        metrics = self._sort_metrics(r.check({"redis_urls": "localhost:%s" % NOAUTH_PORT}))
        assert metrics, "No metrics returned"

        # Assert we have values, timestamps and tags for each metric.
        for m in metrics:
            assert isinstance(m[1], int)    # timestamp
            assert isinstance(m[2], float)  # value
            tags = m[3]["tags"]
            expected_tags = ["redis_host:localhost", "redis_port:16379"]
            for e in expected_tags:
                assert e in tags

        # Assert we have the rest of the keys.
        remaining_keys = [m[0] for m in metrics]
        expected = ['redis.mem.used', 'redis.net.clients', 'redis.net.slaves']
        for e in expected:
            assert e in remaining_keys, e

        # Assert that the keys metrics are tagged by db. just check db0, since
        # it's the only one we can guarantee is there.
        db_metrics = self._sort_metrics([m for m in metrics if m[0] in ['redis.keys',
        'redis.expires'] and "redis_db:db14" in m[3]["tags"]])
        self.assertEquals(2, len(db_metrics))

        self.assertEquals('redis.expires', db_metrics[0][0])
        self.assertEquals(1, db_metrics[0][2]) 

        self.assertEquals('redis.keys', db_metrics[1][0])
        self.assertEquals(3, db_metrics[1][2]) 

        # Run one more check and ensure we get total command count
        metrics = self._sort_metrics(r.check({"redis_urls": "localhost:%s" % NOAUTH_PORT}))
        keys = [m[0] for m in metrics]
        assert 'redis.net.commands' in keys

    def _sort_metrics(self, metrics):
        def sort_by(m):
            return m[0], m[1], m[3]
        return sorted(metrics, key=sort_by)

if __name__ == "__main__":
    unittest.main()
