"""
Redis check tests.
"""

import logging
import unittest

import nose.tools as t

from checks.db.redisDb import Redis

logger = logging.getLogger()

class TestRedis(object):

    def test_redis_default(self):
        r = Redis(logger)
        metrics = self._sort_metrics(r.check({}))
        assert metrics, "we returned metrics"

        # Assert we have values, timestamps and tags for each metric.
        for m in metrics:
            assert isinstance(m[1], int)    # timestamp
            assert isinstance(m[2], float)  # value
            t.assert_equal({"tags": ["host:localhost", "port:6379"]}, m[3])

        # Assert we have db metrics for at least one db
        t.assert_equal(metrics[0][0], "redis.db0.expires")
        t.assert_equal(metrics[1][0], "redis.db0.keys")

        # We could have any number of database metrics. just check the first 
        # and ignore the rest.
        while metrics[0][0].startswith("redis.db"):
            metrics = metrics[1:]

        # Assert we have the rest of the keys.
        remaining_keys = [m[0] for m in metrics]
        expected = ['redis.mem.used', 'redis.net.clients', 'redis.net.slaves']
        for e in expected:
            assert e in remaining_keys, e

        # Run one more check and ensure we get total command count
        metrics = self._sort_metrics(r.check({}))
        keys = [m[0] for m in metrics]
        assert 'redis.net.commands' in keys

    def _sort_metrics(self, metrics):
        def sort_by(m):
            return m[0], [1]
        return sorted(metrics, key=sort_by)

