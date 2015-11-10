# stdlib
import logging
import time
import json

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

    def test_sidekiq_default(self):
        port = NOAUTH_PORT
        db = 14 # Datadog's test db

        instance = {
            'host': 'localhost',
            'port': port,
            'db': db
        }

        db = redis.Redis(port=port, db=db)
        db.flushdb()
        self._reset_sidekiq(db)
        db.set('stat:processed', '123')
        db.set('stat:failed', '456')
        db.sadd("queues", "foo", "bar")
        db.lpush("queue:foo", self._job())
        db.lpush("queue:bar", self._job(), self._job())

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

        # Assert global stats exist
        m = self._metric(metrics, 'sidekiq.processed')
        self.assertEquals(123, m[0][2])
        m = self._metric(metrics, 'sidekiq.failed')
        self.assertEquals(456, m[0][2])

        # Assert queue length metrics are correct
        m = self._metric(metrics, 'sidekiq.queue.length', 'queue:foo')
        self.assertEquals(1, len(m))
        self.assertEquals(1, m[0][2])

        m = self._metric(metrics, 'sidekiq.queue.length', 'queue:bar')
        self.assertEquals(1, len(m))
        self.assertEquals(2, m[0][2])

        # Assert queue latency metrics exist
        m = self._metric(metrics, 'sidekiq.queue.latency', 'queue:foo')
        assert m, "No sidekiq.queue.latecy metric returned for queue:foo"

        m = self._metric(metrics, 'sidekiq.queue.latency', 'queue:bar')
        assert m, "No sidekiq.queue.latecy metric returned for queue:bar"

    def test_sidekiq_namespace(self):
        port = NOAUTH_PORT
        db = 14 # Datadog's test db

        instance = {
            'host': 'localhost',
            'port': port,
            'db': db,
            'namespace': 'ns'
        }

        db = redis.Redis(port=port, db=db)
        db.flushdb()
        self._reset_sidekiq(db, 'ns')
        db.sadd("ns:queues", "foo", "bar")
        db.lpush("ns:queue:foo", self._job())

        r = load_check('sidekiq', {}, {})
        r.check(instance)
        metrics = self._sort_metrics(r.get_metrics())
        assert metrics, "No metrics returned"

        # Assert queue length metrics are correct
        m = self._metric(metrics, 'sidekiq.queue.length', 'queue:foo')
        self.assertEquals(1, len(m))
        self.assertEquals(1, m[0][2])

    def _reset_sidekiq(self, db, namespace=None):
        def k(n):
            return "%s:%s" % (namespace, n) if namespace else n

        db.delete(k('queues'), k('processes'), k('schedule'), k('retry'), k('dead'))
        db.set(k('stat:processed'), '0')
        db.set(k('stat:failed'), '0')

    def _sort_metrics(self, metrics):
        def sort_by(m):
            return m[0], m[1], m[3]
        return sorted(metrics, key=sort_by)

    def _metric(self, metrics, name, tag=None):
        res = [m for m in metrics if m[0] == name]
        if tag:
            res = [m for m in res if tag in m[3]["tags"]]
        return self._sort_metrics(res)

    def _job(self):
        return json.dumps({'enqueued_at': time.time()})