"""
Redis checks.
"""

import re


from checks import *

class Redis(Check):
    db_key_pattern = re.compile(r'^db\d+')
    subkeys = ['keys', 'expires']
    
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.enabled = True
        try:
            import redis
        except ImportError:
            self.enabled = False

        logger.info("[REDIS] check enabled: %s" % self.enabled)
            
        self.total_commands = {}
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
            self.logger.exception("[REDIS] Cannot parse dictionary string: %s" % string)
            return default

    def _get_conn(self, host, port):
        import redis
        key = (host, port)
        if key not in self.connections:
            self.connections[key] = redis.Redis(host=host, port=port)
        return self.connections[key]

    def _check_db(self, host, port):
        conn = self._get_conn(host, port)
        tags = ("redis_host:%s" % host, "redis_port:%s" % port)
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
                    self.save_gauge(metric, val, tags=db_tags)

        self.save_gauge('redis.net.clients', info['connected_clients'], tags=tags)
        self.save_gauge('redis.net.slaves', info['connected_slaves'], tags=tags)
        self.save_gauge('redis.mem.used', info['used_memory'], tags=tags)

        # Save the number of commands.
        total_commands = info['total_commands_processed'] - 1
        if tags in self.total_commands:
            count = self.total_commands[tags] - total_commands
            self.save_gauge('redis.net.commands', count, tags=tags)
        self.total_commands[tags] = total_commands

        try:
            self.save_gauge('redis.net.blocked', info['blocked_clients'], tags=tags)
        except KeyError:
            # Redis 1.2 does not export this
            pass
 

    def check(self, agentConfig):
        if not self.enabled:
            return False

        # Allow the default redis database to be overridden.
        urls = agentConfig.get('redis_urls', 'localhost:6379')
        for url in [u.strip() for u in urls.split(',')]:
            try:
                self.logger.info("[REDIS] Checking instance: %s" % url)
                host, port = url.split(":")
                self._check_db(host, int(port))
            except:
                self.logger.exception("[REDIS] Error checking redis at %s" % url)
        return self.get_metrics()

if __name__ == '__main__':
    import logging
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logger = logging.getLogger()
    logger.addHandler(console)
    
    print Redis(logger).check({})
