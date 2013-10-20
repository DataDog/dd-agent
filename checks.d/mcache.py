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

class Memcache(AgentCheck):
    DEFAULT_PORT = 11211

    GAUGES = [
        "total_items",
        "curr_items",
        "limit_maxbytes",
        "uptime",
        "bytes",
        "curr_connections",
        "connection_structures",
        "threads",
        "pointer_size"
    ]

    RATES = [
        "rusage_user",
        "rusage_system",
        "cmd_get",
        "cmd_set",
        "cmd_flush",
        "get_hits",
        "get_misses",
        "evictions",
        "bytes_read",
        "bytes_written",
        "total_connections"
    ]

    def get_library_versions(self):
        try:
            import memcache
            version = memcache.__version__
        except ImportError:
            version = "Not Found"
        except AttributeError:
            version = "Unknown"

        return {"memcache": version}

    def _get_metrics(self, server, port, tags, memcache):
        mc = None  # client
        try:
            self.log.debug("Connecting to %s:%s tags:%s", server, port, tags)
            mc = memcache.Client(["%s:%d" % (server, port)])
            raw_stats = mc.get_stats()

            assert len(raw_stats) == 1 and len(raw_stats[0]) == 2, "Malformed response: %s" % raw_stats
            # Access the dict
            stats = raw_stats[0][1]
            for metric in stats:
                # Check if metric is a gauge or rate
                if metric in self.GAUGES:
                    our_metric = self.normalize(metric.lower(), 'memcache')
                    self.gauge(our_metric, float(stats[metric]), tags=tags)

                # Tweak the name if it's a rate so that we don't use the exact
                # same metric name as the memcache documentation
                if metric in self.RATES:
                    our_metric = self.normalize(metric.lower() + "_rate", 'memcache')
                    self.rate(our_metric, float(stats[metric]), tags=tags)

            # calculate some metrics based on other metrics.
            # stats should be present, but wrap in try/except
            # and log an exception just in case.
            try:
                self.gauge(
                    "memcache.get_hit_percent",
                    100.0 * float(stats["get_hits"]) / float(stats["cmd_get"]),
                    tags=tags,
                )
            except ZeroDivisionError:
                pass

            try:
                self.gauge(
                    "memcache.fill_percent",
                    100.0 * float(stats["bytes"]) / float(stats["limit_maxbytes"]),
                    tags=tags,
                )
            except ZeroDivisionError:
                pass

            try:
                self.gauge(
                    "memcache.avg_item_size",
                    float(stats["bytes"]) / float(stats["curr_items"]),
                    tags=tags,
                )
            except ZeroDivisionError:
                pass
        except AssertionError:
            raise Exception("Unable to retrieve stats from memcache instance: " + server + ":" + str(port) + ". Please check your configuration")

        if mc is not None:
            mc.disconnect_all()
            self.log.debug("Disconnected from memcached")
        del mc

    def check(self, instance):
        server = instance.get('url', None)
        if not server:
            raise Exception("Missing or null 'url' in mcache config")

        try:
            import memcache
        except ImportError:
            raise Exception("Cannot import memcache module. Check the instructions to install this module at https://app.datadoghq.com/account/settings#integrations/mcache")

        # Hacky monkeypatch to fix a memory leak in the memcache library.
        # See https://github.com/DataDog/dd-agent/issues/278 for details.
        try:
            memcache.Client.debuglog = None
        except:
            pass

        port = int(instance.get('port', self.DEFAULT_PORT))
        tags = instance.get('tags', None)

        self._get_metrics(server, port, tags, memcache)

    @staticmethod
    def parse_agent_config(agentConfig):
        all_instances = []

        # Load the conf according to the old schema
        memcache_url = agentConfig.get("memcache_server", None)
        memcache_port = agentConfig.get("memcache_port", Memcache.DEFAULT_PORT)
        if memcache_url is not None:
            instance = {
                'url': memcache_url,
                'port': memcache_port,
                'tags': ["instance:%s_%s" % (memcache_url, memcache_port)]
            }
            all_instances.append(instance)

        # Load the conf according to the new schema
        #memcache_instance_1: first_host:first_port:first_tag
        #memcache_instance_2: second_host:second_port:second_tag
        #memcache_instance_3: third_host:third_port:third_tag
        index = 1
        instance = agentConfig.get("memcache_instance_%s" % index, None)
        while instance:
            instance = instance.split(":")

            url = instance[0]
            port = Memcache.DEFAULT_PORT
            tags = None

            if len(instance) > 1:
                port = instance[1]

            if len(instance) == 3:
                tags = ["instance:%s" % instance[2]]

            if not tags:
                tags = ["instance:%s_%s" % (server, port)]

            all_instances.append({
                'url': url,
                'port': port,
                'tags': tags
            })

            index = index + 1
            instance = agentConfig.get("memcache_instance_%s" % index, None)

        if len(all_instances) == 0:
            return False

        return {
            'instances': all_instances
        }
