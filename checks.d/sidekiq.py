'''
Sidekiq checks
'''
# stdlib
import time

# 3rd party
import redis

# project
from checks import AgentCheck

class Sidekiq(AgentCheck):
    SOURCE_TYPE_NAME = 'sidekiq'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.connections = {}

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

        # Check all sidekiq queue lengths
        for queue in conn.smembers('queues'):
            queue_tags = tags + ['queue:' + queue]
            self.gauge('sidekiq.queue.length', conn.llen('queue:%s' % queue), tags=queue_tags)

    def check(self, instance):
        if ("host" not in instance or "port" not in instance) and "unix_socket_path" not in instance:
            raise Exception("You must specify a host/port couple or a unix_socket_path")
        custom_tags = instance.get('tags', [])

        self._check_sidekiq(instance, custom_tags)
