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

# For Membase it gets worse
# http://www.couchbase.org/wiki/display/membase/Membase+Statistics
# https://github.com/membase/ep-engine/blob/master/docs/stats.org

class Memcache(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.gauge("memcache.total_items")
        self.gauge("memcache.curr_items")
        self.gauge("memcache.limit_maxbytes")
        self.gauge("memcache.uptime")
        self.gauge("memcache.bytes")
        self.gauge("memcache.curr_connections")
        self.gauge("memcache.connection_structures")
        self.gauge("memcache.threads")
        self.gauge("memcache.pointer_size")

        self.counter("memcache.rusage_user_rate")
        self.counter("memcache.rusage_system_rate")
        self.counter("memcache.cmd_get_rate")
        self.counter("memcache.cmd_set_rate")
        self.counter("memcache.cmd_flush_rate")
        self.counter("memcache.get_hits_rate")
        self.counter("memcache.get_misses_rate")
        self.counter("memcache.evictions_rate")
        self.counter("memcache.bytes_read_rate")
        self.counter("memcache.bytes_written_rate")
        self.counter("memcache.total_connections_rate")
        
    def _load_conf(self, agentConfig):
        memcache_url = agentConfig.get("memcache_server", None)
        memcache_port = agentConfig.get("memcache_port", None)
        memcache_urls = []
        memcache_ports = []
        tags = []
        if memcache_url is not None:
            memcache_urls.append(memcache_url)
            memcache_ports.append(memcache_port)
            tags.append(None)


        def load_conf(index=1):
            instance = agentConfig.get("memcache_instance_%s" % index, None)
            if instance is not None:
                instance = instance.split(":")
                if len(instance)==3:
                    tags.append(instance[2])
                    memcache_urls.append(instance[0])
                    memcache_ports.append(instance[1])
                load_conf(index+1)

        load_conf()

        return (memcache_urls, memcache_ports, tags)

    def _get_metrics(self, server, port, tags, memcache):
        self.logger.debug("Connecting to %s:%s tags:%s" % (server, port, tags))
        mc = memcache.Client(["%s:%d" % (server, port)])
        raw_stats = mc.get_stats()

        assert len(raw_stats) == 1 and len(raw_stats[0]) == 2, "Malformed response: %s" % raw_stats
        # Access the dict
        stats = raw_stats[0][1]
        for metric in stats:
            self.logger.debug("Processing %s: %s" % (metric, stats[metric]))

            our_metric = "memcache." + metric
            # Tweak the name if it's a counter so that we don't use the exact
            # same metric name as the memcache documentation
            if self.is_counter(metric + "_rate"):
                our_metric = metric + "_rate"

            if self.is_metric(our_metric):
                self.save_sample(our_metric, float(stats[metric]), tags=tags)
                self.logger.debug("Saved %s: %s" % (our_metric, stats[metric]))

    def check(self, agentConfig):
        (memcache_urls, memcache_ports, tags) = self._load_conf(agentConfig)
        if len(memcache_urls) == 0:
            return False
        try:        
            import memcache
        except ImportError:
            self.logger.exception("Cannot import python-based memcache driver")

        for i in range(len(memcache_urls)):
            mc = None # client
            server = memcache_urls[i]
            if server is None:
                continue
            if memcache_ports[i] is None:
                memcache_ports[i] = 11211
            port = int(memcache_ports[i])

            tag = None

            if tags[i] is not None:
                tag = ["instance:%s" % tags[i]]

            try:
                self._get_metrics(server, port, tag, memcache)                   
                
            except ValueError:
                self.logger.exception("Cannot convert port value; check your configuration")
                continue
            except CheckException:
                self.logger.exception("Cannot save sampled data")
                continue
            except:
                self.logger.exception("Cannot get data from memcache")
                continue
            finally:
                if mc is not None:
                    mc.disconnect_all()
                    self.logger.debug("Disconnected from memcached")
                del mc
        metrics = self.get_metrics()
        self.logger.debug("Memcache samples: %s" % metrics)
        return metrics

        
