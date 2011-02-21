class Redis(object):
    db_key_pattern = re.compile(r'^db\d+')
    subkeys = ['keys', 'expires']
    
    def __init__(self):
        try:
            import redis
        except ImportError, e:
            logger.debug('Unable to import redis')
            self.client = None
        else:
            self.client = redis.Redis()
        
        self.prev_total_commands = None
        
    def check(self, logger, agentConfig):
        if self.client:
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
                        output['.'.join(['redis', key, subkey])] = info[key].get(subkey, 0)
                
            
            return output
        else:
            return False
