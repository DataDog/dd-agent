'''
Sidekiq checks
'''
# stdlib
import time

# 3rd party
import redis

# project
from checks import AgentCheck

class Stats:
    def __init__(self, conn, namespace):
        self.conn = conn
        self.namespace = namespace
        self._script = self._register_script()
        self._check_stats()

    # This script collects all the sidekiq related stats in one go.
    # KEYS[1] = 'stat:processed'
    # KEYS[2] = 'stat:failed'
    # KEYS[3] = 'schedule'
    # KEYS[4] = 'retry'
    # KEYS[5] = 'dead'
    # KEYS[6] = 'processes'
    # KEYS[7] = 'queues'
    #
    # Returns an array of results. The array follows the following format:
    # [
    #   processed,
    #   failed,
    #   scheduled_size,
    #   retry_size,
    #   dead_size,
    #   processes_size,
    #   workers_size,
    #   number_of_queues,
    #   queue name 1,
    #   queue name 2,
    #   ...,
    #   queue name n,
    #   queue length 1,
    #   queue length 2,
    #   ...,
    #   queue length n,
    #   queue latency 1,
    #   queue latency 2,
    #   ...,
    #   queue latency n
    # ]
    #
    def _register_script(self):
        s = """
        local processed = redis.call("GET", KEYS[1])
        local failed = redis.call("GET", KEYS[2])
        local scheduled_size = redis.call("ZCARD", KEYS[3])
        local retry_size = redis.call("ZCARD", KEYS[4])
        local dead_size = redis.call("ZCARD", KEYS[5])
        local processes_size = redis.call("SCARD", KEYS[6])
        local processes = redis.call("SMEMBERS", KEYS[6])

        local workers_size = 0
        for i, pkey in ipairs(processes) do
            nspkey = ARGV[1] == "None" and pkey or (ARGV[1] .. ":" .. pkey)
            workers_size = workers_size + tonumber(redis.call("HGET", nspkey, "busy"))
        end

        local queues = redis.call("SMEMBERS", KEYS[7])
        local queue_lengths = {}
        local queue_latencies = {}
        for i, qkey in ipairs(queues) do
            local nsqkey = "queue:" .. qkey
            nsqkey = ARGV[1] == "None" and nsqkey or (ARGV[1] .. ":" .. nsqkey)

            queue_lengths[qkey] = redis.call("LLEN", nsqkey)
            local last = redis.call("LRANGE", nsqkey, -1, -1)[0]
            if not last == nil then
                queue_latencies[qkey] = tonumber(cjson.decode(last)["enqueued_at"])
            else
                queue_latencies[qkey] = 0.0
            end
        end

        local offset = 8
        local result = {processed,failed,scheduled_size,retry_size,dead_size,processes_size,workers_size}
        local n = table.getn(queues)
        result[offset] = n
        for i, q in ipairs(queues) do
            result[offset + i] = q
            result[offset + i + n] = queue_lengths[q]
            result[offset + i + n + n] = queue_latencies[q]
        end
        return result
        """
        return self.conn.register_script(s)

    def _run_script(self):
        return self._script(keys=[
                            self.key('stat:processed'),
                            self.key('stat:failed'),
                            self.key('schedule'),
                            self.key('retry'),
                            self.key('dead'),
                            self.key('processes'),
                            self.key('queues')],
                            args=[
                                self.namespace])

    def _check_stats(self):
        res = self._run_script()
        self.processed = int(res[0])
        self.failed = int(res[1])
        self.scheduled_size = res[2]
        self.retry_size = res[3]
        self.dead_size = res[4]
        self.processes_size = res[5]
        self.workers_size = res[6]
        num_queues = res[7]

        offset = 8
        self.queue_stats = {}
        for i in range(num_queues):
            qname = res[offset + i]
            self.queue_stats[qname] = {
                'length': res[offset + i + num_queues],
                'latency': res[offset + i + num_queues + num_queues]
            }

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
        for queue, stat in stats.queue_stats.iteritems():
            queue_tags = tags + ['queue:' + queue]
            self.gauge('sidekiq.queue.length', stat['length'], tags=queue_tags)
            self.gauge('sidekiq.queue.latency', stat['latency'], tags=queue_tags)

    def check(self, instance):
        if ("host" not in instance or "port" not in instance) and "unix_socket_path" not in instance:
            raise Exception("You must specify a host/port couple or a unix_socket_path")
        custom_tags = instance.get('tags', [])

        self._check_sidekiq(instance, custom_tags)
