'''
Redis checks
'''
import re
from checks import AgentCheck

class Redis(AgentCheck):
    db_key_pattern = re.compile(r'^db\d+')
    subkeys = ['keys', 'expires']

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        # If we can't import the redis module, we should always skip this check
        try:
            import redis
            self.enabled = True
        except ImportError:
            self.enabled = False
            self.log.error('redisdb.yaml exists but redis module can not be imported. Skipping check.')

        self.previous_total_commands = {}
        self.connections = {}

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

    def _get_conn(self, host, port, password):
        import redis
        key = (host, port)
        if key not in self.connections:
            if password is not None and len(password) > 0:
                try:
                    self.connections[key] = redis.Redis(host=host, port=port, password=password)
                except TypeError:
                    self.log.exception("You need a redis library that supports authenticated connections. Try easy_install redis.")
            else:
                self.connections[key] = redis.Redis(host=host, port=port)

        return self.connections[key]

    def _check_db(self, host, port, password, custom_tags=None):
        conn = self._get_conn(host, port, password)
        tags = custom_tags or []
        tags += ["redis_host:%s" % host, "redis_port:%s" % port]
        info = conn.info()

        # Save the database statistics.
        for key in info.keys():
            if self.db_key_pattern.match(key):
                db_tags = list(tags) + ["redis_db:" + key]
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

        self.gauge('redis.net.clients', info['connected_clients'], tags=tags)
        self.gauge('redis.net.slaves', info['connected_slaves'], tags=tags)
        self.gauge('redis.mem.used', info['used_memory'], tags=tags)

        # Save the number of commands.
        total_commands = info['total_commands_processed'] - 1
        tuple_tags = tuple(tags)
        if tuple_tags in self.previous_total_commands:
            count = total_commands - self.previous_total_commands[tuple_tags]
            self.gauge('redis.net.commands', count, tags=tags)
        self.previous_total_commands[tuple_tags] = total_commands

        try:
            self.gauge('redis.net.blocked', info['blocked_clients'], tags=tags)
        except KeyError:
            # Redis 1.2 does not export this
            pass

    def check(self, instance):
        if not self.enabled:
            self.log.debug("Redis check is marked as disabled. Skipping")

        # Allow the default redis database to be overridden.
        host = instance.get('host', 'localhost')
        port = instance.get('port', 6379)
        password = instance.get('password', None)
        custom_tags = instance.get('tags', [])

        try:
            self._check_db(host, int(port), password, custom_tags)
        except:
            self.log.exception("Error checking redis at %s:%s" % (host, port))

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('redis_urls'):
            return False

        urls = agentConfig.get('redis_urls')
        instances = []
        for url in [u.strip() for u in urls.split(',')]:
            password = None
            if '@' in url:
                password, host_port = url.split('@')
                host, port = host_port.split(':')
            else:
                host, port = url.split(':')

            instances.append({
                'host': host,
                'port': port,
                'password': password
            })

        return {
            'instances': instances
        }