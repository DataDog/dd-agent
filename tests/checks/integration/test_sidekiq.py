# stdlib
import logging

# 3p
from nose.plugins.attrib import attr
import redis

# project
from tests.checks.common import AgentCheckTest, load_check

logger = logging.getLogger()

MAX_WAIT = 20
NOAUTH_PORT = 16379
AUTH_PORT = 26379
SLAVE_HEALTHY_PORT = 36379
SLAVE_UNHEALTHY_PORT = 46379
DEFAULT_PORT = 6379
MISSING_KEY_TOLERANCE = 0.6


@attr(requires='sidekiq')
class TestSidkiq(AgentCheckTest):
    CHECK_NAME = "sidekiq"

    def test_redis_default(self):
        port = NOAUTH_PORT
        db = 14 # Datadog's test db

        instance = {
            'host': 'localhost',
            'port': port,
            'db': db
        }

        db = redis.Redis(port=port, db=db)
        db.flushdb()
        db.sadd("queues", "foo", "bar")
        db.lpush("queue:foo", "item1")
        db.lpush("queue:bar", "item1", "item2")

        r = load_check('sidekiq', {}, {})
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

        # Assert queue length metrics are correct
        m = self._metric(metrics, 'sidekiq.queue.length', 'queue:foo')[0]
        self.assertEquals(1, m[2])

        m = self._metric(metrics, 'sidekiq.queue.length', 'queue:bar')[0]
        self.assertEquals(2, m[2])

    def _sort_metrics(self, metrics):
        def sort_by(m):
            return m[0], m[1], m[3]
        return sorted(metrics, key=sort_by)

    def _metric(self, metrics, name, tag=None):
        res = [m for m in metrics if m[0] == name]
        if tag:
            res = [m for m in metrics if tag in m[3]["tags"]]
        return self._sort_metrics(res)
