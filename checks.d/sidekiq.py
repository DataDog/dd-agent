'''
Sidekiq checks
'''
# stdlib
import time
import json

# 3rd party
import redis

# project
from checks import AgentCheck

class Stats:
    def __init__(self, conn, namespace):
        self.conn = conn
        self.namespace = namespace
        self._check_stats()

    def _check_stats(self):
        # Check sidekiq stats
        pipe = self.conn.pipeline()
        pipe.get(self.key('stat:processed'))
        pipe.get(self.key('stat:failed'))
        pipe.zcard(self.key('schedule'))
        pipe.zcard(self.key('retry'))
        pipe.zcard(self.key('dead'))
        pipe.scard(self.key('processes'))
        pipe.smembers(self.key('processes'))
        pipe.smembers(self.key('queues'))
        res = pipe.execute()

        self.processed = int(res[0])
        self.failed = int(res[1])
        self.scheduled_size = res[2]
        self.retry_size = res[3]
        self.dead_size = res[4]
        self.processes_size = res[5]

        procs = res[6]
        queues = list(res[7])

        self._check_processes(procs)
        self._init_queue_stats(queues)
        self._check_queue_lengths(queues)
        self._check_queue_latencies(queues)

    def _check_processes(self, procs):
        pipe = self.conn.pipeline()

        for proc in procs:
            pipe.hget(self.key(proc), 'busy')
        res = pipe.execute()

        self.workers_size = sum([int(x) for x in res])

    def _init_queue_stats(self, queues):
        self.queues = {}
        for queue in queues:
            self.queues[queue] = {'length': 0, 'latency': 0.0}

    # Sum length of all sub queues for each queue
    def _check_queue_lengths(self, queues):
        for queue in queues:
            qname = 'queue:%s' % queue
            subqueues = [self.key(qname)] + self.conn.keys('%s_*' % self.key(qname))
            pipe = self.conn.pipeline()

            for sq_key in subqueues:
                pipe.llen(sq_key)
            res = pipe.execute()
            self.queues[queue]['length'] = sum([int(x) for x in res])

    # Find max latency of sub queues for each queue
    def _check_queue_latencies(self, queues):

        for queue in queues:
            qname = 'queue:%s' % queue
            subqueues = [self.key(qname)] + self.conn.keys('%s_*' % self.key(qname))
            pipe = self.conn.pipeline()

            for sq_key in subqueues:
                pipe.lrange(sq_key, -1, -1)
            res = pipe.execute()

            for i in range(len(res)):
                entry = res[i]
                if len(entry) > 0:
                    latency = time.time() - float(json.loads(entry[0])['enqueued_at'])
                    if latency > self.queues[queue]['latency']:
                        self.queues[queue]['latency'] = latency

    def key(self, name):
        return "%s:%s" % (self.namespace, name) if self.namespace else name


class Sidekiq(AgentCheck):
    SOURCE_TYPE_NAME = 'sidekiq'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.connections = {}

    def _key(self, instance, name):
        ns = instance.get('namespace')
        return "%s:%s" % (ns, name) if ns else name

    # Taken from redisdb.py, returns custom tags and redis tags for redis connection.
    def _get_tags(self, custom_tags, instance):
        tags = set(custom_tags or [])

        if 'unix_socket_path' in instance:
            tags_to_add = [
                "redis_host:%s" % instance.get("unix_socket_path"),
                "redis_port:unix_socket",
            ]
        else:
            tags_to_add = [
                "redis_host:%s" % instance.get('host'),
                "redis_port:%s" % instance.get('port')
            ]

        tags = sorted(tags.union(tags_to_add))

        return tags, tags_to_add

    # Taken from redisdb.py, generates a uniq key to cache redis connections.
    def _generate_instance_key(self, instance):
        if 'unix_socket_path' in instance:
            return (instance.get('unix_socket_path'), instance.get('db'))
        else:
            return (instance.get('host'), instance.get('port'), instance.get('db'))

    # Taken from redisdb.py, collects metadata from the redis server.
    def _collect_metadata(self, info):
        if info and 'redis_version' in info:
            self.service_metadata('version', info['redis_version'])

    # Taken from redisdb.py, retrieves a cached redis connection.
    def _get_conn(self, instance):
        key = self._generate_instance_key(instance)
        if key not in self.connections:
            try:

                # Only send useful parameters to the redis client constructor
                list_params = ['host', 'port', 'db', 'password', 'socket_timeout',
                               'connection_pool', 'charset', 'errors', 'unix_socket_path']

                # Set a default timeout (in seconds) if no timeout is specified in the instance config
                instance['socket_timeout'] = instance.get('socket_timeout', 5)

                connection_params = dict((k, instance[k]) for k in list_params if k in instance)

                self.connections[key] = redis.Redis(**connection_params)

            except TypeError:
                raise Exception("You need a redis library that supports authenticated connections. Try sudo easy_install redis.")

        return self.connections[key]

    def _check_sidekiq(self, instance, custom_tags):
        conn = self._get_conn(instance)

        tags, tags_to_add = self._get_tags(custom_tags, instance)

        # Ping the database for info, and track the latency.
        # Process the service check: the check passes if we can connect to Redis
        start = time.time()
        info = None
        try:
            info = conn.info()
            status = AgentCheck.OK
            self.service_check('sidekiq.redis.can_connect', status, tags=tags_to_add)
            self._collect_metadata(info)
        except ValueError, e:
            status = AgentCheck.CRITICAL
            self.service_check('sidekiq.redis.can_connect', status, tags=tags_to_add)
            raise
        except Exception, e:
            status = AgentCheck.CRITICAL
            self.service_check('sidekiq.redis.can_connect', status, tags=tags_to_add)
            raise

        latency_ms = round((time.time() - start) * 1000, 2)
        self.gauge('sidekiq.redis.info.latency_ms', latency_ms, tags=tags)

        stats = Stats(conn, instance.get('namespace'))

        # Check global sidekiq stats
        self.gauge('sidekiq.processed', stats.processed, tags=tags)
        self.gauge('sidekiq.failed', stats.failed, tags=tags)
        self.gauge('sidekiq.scheduled_size', stats.scheduled_size, tags=tags)
        self.gauge('sidekiq.retry_size', stats.retry_size, tags=tags)
        self.gauge('sidekiq.dead_size', stats.dead_size, tags=tags)
        self.gauge('sidekiq.processes_size', stats.processes_size, tags=tags)
        self.gauge('sidekiq.workers_size', stats.workers_size, tags=tags)

        # Check queue stats
        for queue, stat in stats.queues.iteritems():
            queue_tags = tags + ['queue:' + queue]
            self.gauge('sidekiq.queue.length', stat['length'], tags=queue_tags)
            self.gauge('sidekiq.queue.latency', stat['latency'], tags=queue_tags)

    def check(self, instance):
        if ("host" not in instance or "port" not in instance) and "unix_socket_path" not in instance:
            raise Exception("You must specify a host/port couple or a unix_socket_path")
        custom_tags = instance.get('tags', [])

        self._check_sidekiq(instance, custom_tags)
