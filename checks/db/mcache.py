import logging
logger = logging.getLogger(__file__)

from checks import *

# Reference: http://code.sixapart.com/svn/memcached/trunk/server/doc/protocol.txt
# Name              Type     Meaning
# ----------------------------------
# pid               32u      Process id of this server process
# uptime            32u      Number of seconds this server has been running
# time              32u      current UNIX time according to the server
# version           string   Version string of this server
# pointer_size      32       Default size of pointers on the host OS
#                            (generally 32 or 64)
# rusage_user       32u:32u  Accumulated user time for this process 
#                            (seconds:microseconds)
# rusage_system     32u:32u  Accumulated system time for this process 
#                            (seconds:microseconds)
# curr_items        32u      Current number of items stored by the server
# total_items       32u      Total number of items stored by this server 
#                            ever since it started
# bytes             64u      Current number of bytes used by this server 
#                            to store items
# curr_connections  32u      Number of open connections
# total_connections 32u      Total number of connections opened since 
#                            the server started running
# connection_structures 32u  Number of connection structures allocated 
#                            by the server
# cmd_get           64u      Cumulative number of retrieval requests
# cmd_set           64u      Cumulative number of storage requests
# get_hits          64u      Number of keys that have been requested and 
#                            found present
# get_misses        64u      Number of items that have been requested 
#                            and not found
# evictions         64u      Number of valid items removed from cache
#                            to free memory for new items
# bytes_read        64u      Total number of bytes read by this server 
#                            from network
# bytes_written     64u      Total number of bytes sent by this server to 
#                            network
# limit_maxbytes    32u      Number of bytes this server is allowed to
#                            use for storage. 
# threads           32u      Number of worker threads requested.
#                            (see doc/threads.txt)
#     >>> mc.get_stats()
# [('127.0.0.1:11211 (1)', {'pid': '2301', 'total_items': '2',
# 'uptime': '80', 'listen_disabled_num': '0', 'version': '1.2.8',
# 'limit_maxbytes': '67108864', 'rusage_user': '0.002532',
# 'bytes_read': '51', 'accepting_conns': '1', 'rusage_system':
# '0.007445', 'cmd_get': '0', 'curr_connections': '4', 'threads': '2',
# 'total_connections': '5', 'cmd_set': '2', 'curr_items': '0',
# 'get_misses': '0', 'cmd_flush': '0', 'evictions': '0', 'bytes': '0',
# 'connection_structures': '5', 'bytes_written': '25', 'time':
# '1306364220', 'pointer_size': '64', 'get_hits': '0'})]

class Memcache(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.gauge("total_items")
        self.gauge("curr_items")
        self.gauge("limit_maxbytes")
        self.gauge("uptime")
        self.gauge("bytes")
        self.gauge("curr_connections")
        self.gauge("connection_structures")
        self.gauge("threads")
        self.gauge("pointer_size")

        self.counter("rusage_user")
        self.counter("rusage_system")
        self.counter("cmd_get")
        self.counter("cmd_set")
        self.counter("cmd_flush")
        self.counter("get_hits")
        self.counter("get_misses")
        self.counter("evictions")
        self.counter("bytes_read")
        self.counter("bytes_written")
        self.counter("total_connections")
    
    def check(self, agentConfig):
        try:
            import memcache

            server = agentConfig["memcache_server"]
            port = int(agentConfig.get("memcache_port", 11211))
            logger.debug("Connecting to %s:%s" % (server, port))
            
            mc = memcache.Client(["%s:%d" % (server, port)])
            raw_stats = mc.get_stats()
            assert len(raw_stats) == 1 and len(raw_stats[0]) == 2, "Malformed response: %s" % raw_stats
            # Access the dict
            stats = raw_stats[0][1]
            for metric in stats:
                logger.debug("Processing %s: %s" % (metric, stats[metric]))
                if self.is_gauge(metric):
                    self.save_sample(metric, float(stats[metric]))
                elif self.is_counter(metric):
                    self.save_sample(metric + "_rate", float(stats[metric]))

            samples = self.get_samples()
            logger.debug("Memcache samples: %s" % samples)
            return samples
        except ImportError:
            logger.exception("Cannot import python-memcache. Try easy_install python-memcached")
        except ValueError:
            logger.exception("Cannot convert port value; check your configuration")
        except CheckException:
            logger.exception("Cannot save sampled data")
        except:
            logger.exception("Cannot get data from memcache")
        
        return None
