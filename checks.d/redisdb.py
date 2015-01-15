'''
Redis checks
'''
# stdlib
import re
import time

# project
from checks import AgentCheck

# 3rd party
import redis

class Redis(AgentCheck):
    db_key_pattern = re.compile(r'^db\d+')
    subkeys = ['keys', 'expires']

    SOURCE_TYPE_NAME = 'redis'

    GAUGE_KEYS = {
        # Append-only metrics
        'aof_last_rewrite_time_sec':    'redis.aof.last_rewrite_time',
        'aof_rewrite_in_progress':      'redis.aof.rewrite',
        'aof_current_size':             'redis.aof.size',
        'aof_buffer_length':            'redis.aof.buffer_length',

        # Network
        'connected_clients':            'redis.net.clients',
        'connected_slaves':             'redis.net.slaves',
        'rejected_connections':         'redis.net.rejected',

        # clients
        'blocked_clients':              'redis.clients.blocked',
        'client_biggest_input_buf':     'redis.clients.biggest_input_buf',
        'client_longest_output_list':   'redis.clients.longest_output_list',

        # Keys
        'evicted_keys':                 'redis.keys.evicted',
        'expired_keys':                 'redis.keys.expired',

        # stats
        'keyspace_hits':                'redis.stats.keyspace_hits',
        'keyspace_misses':              'redis.stats.keyspace_misses',
        'latest_fork_usec':             'redis.perf.latest_fork_usec',

        # pubsub
        'pubsub_channels':              'redis.pubsub.channels',
        'pubsub_patterns':              'redis.pubsub.patterns',

        # rdb
        'rdb_bgsave_in_progress':       'redis.rdb.bgsave',
        'rdb_changes_since_last_save':  'redis.rdb.changes_since_last',
        'rdb_last_bgsave_time_sec':     'redis.rdb.last_bgsave_time',

        # memory
        'mem_fragmentation_ratio':      'redis.mem.fragmentation_ratio',
        'used_memory':                  'redis.mem.used',
        'used_memory_lua':              'redis.mem.lua',
        'used_memory_peak':             'redis.mem.peak',
        'used_memory_rss':              'redis.mem.rss',

        # replication
        'master_last_io_seconds_ago':   'redis.replication.last_io_seconds_ago',
        'master_sync_in_progress':      'redis.replication.sync',
        'master_sync_left_bytes':       'redis.replication.sync_left_bytes',

    }

    RATE_KEYS = {
        # cpu
        'used_cpu_sys':                 'redis.cpu.sys',
        'used_cpu_sys_children':        'redis.cpu.sys_children',
        'used_cpu_user':                'redis.cpu.user',
        'used_cpu_user_children':       'redis.cpu.user_children',
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.connections = {}

    def get_library_versions(self):
        return {"redis": redis.__version__}

    def _parse_dict_string(self, string, key, default):
        """Take from a more recent redis.py, parse_info"""
        try:
            for item in string.split(','):
                k, v = item.rsplit('=', 1)
                if k == key:
                    try:
                        return int(v)
                    except ValueError:
                        return v
            return default
        except Exception, e:
            self.log.exception("Cannot parse dictionary string: %s" % string)
            return default

    def _generate_instance_key(self, instance):
        if 'unix_socket_path' in instance:
            return (instance.get('unix_socket_path'), instance.get('db'))
        else:
            return (instance.get('host'), instance.get('port'), instance.get('db'))

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

    def _check_db(self, instance, custom_tags=None):
        conn = self._get_conn(instance)
        tags = set(custom_tags or [])

        if 'unix_socket_path' in instance:
            tags_to_add = ["unix_socket_path:%s" % instance.get("unix_socket_path")]
        else:
            tags_to_add =  ["redis_host:%s" % instance.get('host'), "redis_port:%s" % instance.get('port')]

        if instance.get('db') is not None:
            tags_to_add.append("db:%s" % instance.get('db'))

        tags = sorted(tags.union(tags_to_add))

        # Ping the database for info, and track the latency.
        # Process the service check: the check passes if we can connect to Redis
        start = time.time()
        try:
            info = conn.info()
            status = AgentCheck.OK
            self.service_check('redis.can_connect', status, tags=tags_to_add)
        except ValueError, e:
            status = AgentCheck.CRITICAL
            self.service_check('redis.can_connect', status, tags=tags_to_add)
            raise
        except Exception, e:
            status = AgentCheck.CRITICAL
            self.service_check('redis.can_connect', status, tags=tags_to_add)
            raise

        latency_ms = round((time.time() - start) * 1000, 2)
        self.gauge('redis.info.latency_ms', latency_ms, tags=tags)

        # Save the database statistics.
        for key in info.keys():
            if self.db_key_pattern.match(key):
                db_tags = list(tags) + ["redis_db:" + key]
                # allows tracking percentage of expired keys as DD does not
                # currently allow arithmetic on metric for monitoring
                expires_keys = info[key]["expires"]
                total_keys   = info[key]["keys"]
                persist_keys = total_keys - expires_keys
                self.gauge("redis.persist", persist_keys, tags=db_tags)
                self.gauge("redis.persist.percent", 100.0 * persist_keys / total_keys, tags=db_tags)
                self.gauge("redis.expires.percent", 100.0 * expires_keys / total_keys, tags=db_tags)

                for subkey in self.subkeys:
                    # Old redis module on ubuntu 10.04 (python-redis 0.6.1) does not
                    # returns a dict for those key but a string: keys=3,expires=0
                    # Try to parse it (see lighthouse #46)
                    val = -1
                    try:
                        val = info[key].get(subkey, -1)
                    except AttributeError:
                        val = self._parse_dict_string(info[key], subkey, -1)
                    metric = '.'.join(['redis', subkey])
                    self.gauge(metric, val, tags=db_tags)

        # Save a subset of db-wide statistics
        [self.gauge(self.GAUGE_KEYS[k], info[k], tags=tags) for k in self.GAUGE_KEYS if k in info]
        [self.rate (self.RATE_KEYS[k],  info[k], tags=tags) for k in self.RATE_KEYS  if k in info]

        # Save the number of commands.
        self.rate('redis.net.commands', info['total_commands_processed'],
                  tags=tags)

        # Check some key lengths if asked
        key_list = instance.get('keys')
        if key_list is not None:
            if not isinstance(key_list, list) or len(key_list) == 0:
                self.warning("keys in redis configuration is either not a list or empty")
            else:
                l_tags = list(tags)
                for key in key_list:
                    key_type = conn.type(key)
                    key_tags = l_tags + ['key:' + key]

                    if key_type == 'list':
                        self.gauge('redis.key.length', conn.llen(key), tags=key_tags)
                    elif key_type == 'set':
                        self.gauge('redis.key.length', conn.scard(key), tags=key_tags)
                    elif key_type == 'zset':
                        self.gauge('redis.key.length', conn.zcard(key), tags=key_tags)
                    elif key_type == 'hash':
                        self.gauge('redis.key.length', conn.hlen(key), tags=key_tags)
                    else:
                        # If the type is unknown, it might be because the key doesn't exist,
                        # which can be because the list is empty. So always send 0 in that case.
                        if instance.get("warn_on_missing_keys", True):
                            self.warning("{0} key not found in redis".format(key))
                        self.gauge('redis.key.length', 0, tags=key_tags)

    def check(self, instance):
        if (not "host" in instance or not "port" in instance) and not "unix_socket_path" in instance:
            raise Exception("You must specify a host/port couple or a unix_socket_path")
        custom_tags = instance.get('tags', [])
        self._check_db(instance,custom_tags)
