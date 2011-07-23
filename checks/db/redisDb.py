import re

from checks import *

class Redis(Check):
    db_key_pattern = re.compile(r'^db\d+')
    subkeys = ['keys', 'expires']
    
    def __init__(self, logger):
        Check.__init__(self, logger)
        try:
            import redis
        except ImportError, e:
            self.client = None
        else:
            self.client = redis.Redis()
        
        self.prev_total_commands = None
        
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
            self.logger.exception("Cannot parse dictionnary string: %s" % string)
            return default

    def check(self, agentConfig):
        if self.client is not None:
            try:
                info = self.client.info()
                output = {
                    'redis.net.clients':  info['connected_clients'],
                    'redis.net.slaves':   info['connected_slaves'],
                    'redis.net.blocked':  info['blocked_clients'],
                    'redis.mem.used':     info['used_memory'],
                }
            
                # Subtract 1 to correct for the agent's INFO command to 
                totall_commands = info['total_commands_processed'] - 1 
            
                if self.prev_total_commands is not None:
                    output['redis.net.commands'] = info['total_commands_processed'] - self.prev_total_commands
            
                self.prev_total_commands = info['total_commands_processed']
            
                for key in info.keys():
                    if self.db_key_pattern.match(key):
                        for subkey in self.subkeys:
                            # Old redis module on ubuntu 10.04 (python-redis 0.6.1) does not
                            # returns a dict for those key but a string: keys=3,expires=0
                            # Try to parse it (see lighthouse #46)            
                            val = - 1
                            try:
                                val = info[key].get(subkey, -1)
                            except AttributeError:
                                val = self._parse_dict_string(info[key], subkey, -1)

                            output['.'.join([key, subkey])] = val
                return output
            except:
                self.logger.exception("Cannot get Redis stats")
                return False
        else:
            return False
