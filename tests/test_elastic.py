import unittest
import logging
logging.basicConfig()
import subprocess
import time
import urllib2
import urlparse

from checks.db.elastic import ElasticSearch, ElasticSearchClusterStatus, _get_data, HEALTH_URL

PORT = 9200
MAX_WAIT = 150

class TestElastic(unittest.TestCase):

    def _wait(self, url):
        loop = 0
        while True:
            try:
                req = urllib2.Request(url, None)
                request = urllib2.urlopen(req)
                break
            except:
                time.sleep(0.5)
                loop = loop + 1
                if loop >= MAX_WAIT:
                    break              

    def setUp(self):
        self.c = ElasticSearch(logging.getLogger())
        self.d = ElasticSearchClusterStatus(logging.getLogger())
        self.process = None
        try:
            # Start elasticsearch
            self.process = subprocess.Popen(["elasticsearch","-f","elasticsearch"],
                        executable="elasticsearch",
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)

            # Wait for it to really start
            self._wait("http://localhost:%s" % PORT)
        except:
            logging.getLogger().exception("Cannot instantiate elasticsearch")

    def tearDown(self):
        if self.process is not None:
            self.process.terminate()

    def testEvent(self):
        agentConfig = { 'elasticsearch': 'http://localhost:%s/_cluster/nodes/stats?all=true' % PORT,
              'version': '0.1',
              'apiKey': 'toto' }


        url = urlparse.urljoin(agentConfig['elasticsearch'], HEALTH_URL)
        data = _get_data(agentConfig, url)
        self.assertEquals(len(data), 10,data)

        data['status'] = "green"
        events = self.d.check(logging.getLogger(), agentConfig,data)
        self.assertEquals(len(events),0,events)

        data = _get_data(agentConfig, url)
        data['status'] = "red"
        events = self.d.check(logging.getLogger,agentConfig, data)
        self.assertEquals(len(events),1,events)




    def testCheck(self):
        agentConfig = { 'elasticsearch': 'http://localhost:%s/_cluster/nodes/stats?all=true' % PORT,
                      'version': '0.1',
                      'apiKey': 'toto' }

        r = self.c.check(agentConfig)
        def _check(slf, r):
            slf.assertTrue(type(r) == type([]))
            slf.assertTrue(len(r) > 0)
            slf.assertEquals(len([t for t in r if t[0] == "elasticsearch.get.total"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "elasticsearch.search.fetch.total"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "jvm.gc.collection_time"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "jvm.mem.heap_committed"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "jvm.mem.heap_used"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "jvm.threads.count"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "jvm.threads.peak_count"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "elasticsearch.transport.rx_count"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "elasticsearch.transport.tx_size"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "elasticsearch.transport.server_open"]), 1, r)
            slf.assertEquals(len([t for t in r if t[0] == "elasticsearch.thread_pool.snapshot.queue"]), 1, r)

        _check(self, r)

        # Same check, only given hostname
        agentConfig = { 'elasticsearch': 'http://localhost:%s' % PORT,
                      'version': '0.1',
                      'apiKey': 'toto' }

        r = self.c.check(agentConfig)
        _check(self, r)

        # Same check, only given hostname
        agentConfig = { 'elasticsearch': 'http://localhost:%s/wrong_url' % PORT,
                      'version': '0.1',
                      'apiKey': 'toto' }

        r = self.c.check(agentConfig)
        self.assertFalse(r)
        

if __name__ == "__main__":
    unittest.main()

"""{
    "cluster_name": "elasticsearch_alq",
    "nodes": {
        "fRsCY6YGRIKbAWnhEh_LIw": {
            "fs": {
                "data": [
                    {
                        "available": "31.1gb",
                        "available_in_bytes": 33434996736,
                        "free": "31.3gb",
                        "free_in_bytes": 33697140736,
                        "path": "/usr/local/var/elasticsearch/elasticsearch_alq/nodes/0",
                        "total": "232.6gb",
                        "total_in_bytes": 249821663232
                    }
                ],
                "timestamp": 1342734630016
            },
            "hostname": "Seneca.local",
            "http": {
                "current_open": 1,
                "total_opened": 4
            },
            "indices": {
                "cache": {
                    "field_evictions": 0,
                    "field_size": "0b",
                    "field_size_in_bytes": 0,
                    "filter_count": 0,
                    "filter_evictions": 0,
                    "filter_size": "0b",
                    "filter_size_in_bytes": 0
                },
                "docs": {
                    "count": 0,
                    "deleted": 0
                },
                "flush": {
                    "total": 0,
                    "total_time": "0s",
                    "total_time_in_millis": 0
                },
                "get": {
                    "current": 0,
                    "exists_time": "0s",
                    "exists_time_in_millis": 0,
                    "exists_total": 0,
                    "missing_time": "0s",
                    "missing_time_in_millis": 0,
                    "missing_total": 0,
                    "time": "0s",
                    "time_in_millis": 0,
                    "total": 0
                },
                "indexing": {
                    "delete_current": 0,
                    "delete_time": "0s",
                    "delete_time_in_millis": 0,
                    "delete_total": 0,
                    "index_current": 0,
                    "index_time": "0s",
                    "index_time_in_millis": 0,
                    "index_total": 0
                },
                "merges": {
                    "current": 0,
                    "current_docs": 0,
                    "current_size": "0b",
                    "current_size_in_bytes": 0,
                    "total": 0,
                    "total_docs": 0,
                    "total_size": "0b",
                    "total_size_in_bytes": 0,
                    "total_time": "0s",
                    "total_time_in_millis": 0
                },
                "refresh": {
                    "total": 0,
                    "total_time": "0s",
                    "total_time_in_millis": 0
                },
                "search": {
                    "fetch_current": 0,
                    "fetch_time": "0s",
                    "fetch_time_in_millis": 0,
                    "fetch_total": 0,
                    "query_current": 0,
                    "query_time": "0s",
                    "query_time_in_millis": 0,
                    "query_total": 0
                },
                "store": {
                    "size": "0b",
                    "size_in_bytes": 0,
                    "throttle_time": "0s",
                    "throttle_time_in_millis": 0
                }
            },
            "jvm": {
                "gc": {
                    "collection_count": 5,
                    "collection_time": "39 milliseconds",
                    "collection_time_in_millis": 39,
                    "collectors": {
                        "ConcurrentMarkSweep": {
                            "collection_count": 0,
                            "collection_time": "0 milliseconds",
                            "collection_time_in_millis": 0
                        },
                        "ParNew": {
                            "collection_count": 5,
                            "collection_time": "39 milliseconds",
                            "collection_time_in_millis": 39
                        }
                    }
                },
                "mem": {
                    "heap_committed": "253.9mb",
                    "heap_committed_in_bytes": 266272768,
                    "heap_used": "19.3mb",
                    "heap_used_in_bytes": 20326888,
                    "non_heap_committed": "32.1mb",
                    "non_heap_committed_in_bytes": 33755136,
                    "non_heap_used": "30.4mb",
                    "non_heap_used_in_bytes": 31922208,
                    "pools": {
                        "CMS Old Gen": {
                            "max": "940.8mb",
                            "max_in_bytes": 986513408,
                            "peak_max": "940.8mb",
                            "peak_max_in_bytes": 986513408,
                            "peak_used": "2.5mb",
                            "peak_used_in_bytes": 2683688,
                            "used": "2.5mb",
                            "used_in_bytes": 2683688
                        },
                        "CMS Perm Gen": {
                            "max": "82mb",
                            "max_in_bytes": 85983232,
                            "peak_max": "82mb",
                            "peak_max_in_bytes": 85983232,
                            "peak_used": "29.5mb",
                            "peak_used_in_bytes": 31015008,
                            "used": "29.5mb",
                            "used_in_bytes": 31015008
                        },
                        "Code Cache": {
                            "max": "48mb",
                            "max_in_bytes": 50331648,
                            "peak_max": "48mb",
                            "peak_max_in_bytes": 50331648,
                            "peak_used": "903.5kb",
                            "peak_used_in_bytes": 925248,
                            "used": "885.9kb",
                            "used_in_bytes": 907200
                        },
                        "Par Eden Space": {
                            "max": "66.5mb",
                            "max_in_bytes": 69795840,
                            "peak_max": "66.5mb",
                            "peak_max_in_bytes": 69795840,
                            "peak_used": "16.6mb",
                            "peak_used_in_bytes": 17432576,
                            "used": "15.6mb",
                            "used_in_bytes": 16431056
                        },
                        "Par Survivor Space": {
                            "max": "8.3mb",
                            "max_in_bytes": 8716288,
                            "peak_max": "8.3mb",
                            "peak_max_in_bytes": 8716288,
                            "peak_used": "2mb",
                            "peak_used_in_bytes": 2162688,
                            "used": "1.1mb",
                            "used_in_bytes": 1212144
                        }
                    }
                },
                "threads": {
                    "count": 33,
                    "peak_count": 35
                },
                "timestamp": 1342734630016,
                "uptime": "1 minute, 30 seconds and 941 milliseconds",
                "uptime_in_millis": 90941
            },
            "name": "Machinesmith",
            "network": {},
            "os": {
                "timestamp": 1342734630015
            },
            "process": {
                "open_file_descriptors": 122,
                "timestamp": 1342734630015
            },
            "thread_pool": {
                "bulk": {
                    "active": 0,
                    "queue": 0,
                    "threads": 0
                },
                "cache": {
                    "active": 0,
                    "queue": 0,
                    "threads": 0
                },
                "flush": {
                    "active": 0,
                    "queue": 0,
                    "threads": 0
                },
                "generic": {
                    "active": 0,
                    "queue": 0,
                    "threads": 1
                },
                "get": {
                    "active": 0,
                    "queue": 0,
                    "threads": 0
                },
                "index": {
                    "active": 0,
                    "queue": 0,
                    "threads": 0
                },
                "management": {
                    "active": 1,
                    "queue": 0,
                    "threads": 1
                },
                "merge": {
                    "active": 0,
                    "queue": 0,
                    "threads": 0
                },
                "percolate": {
                    "active": 0,
                    "queue": 0,
                    "threads": 0
                },
                "refresh": {
                    "active": 0,
                    "queue": 0,
                    "threads": 0
                },
                "search": {
                    "active": 0,
                    "queue": 0,
                    "threads": 0
                },
                "snapshot": {
                    "active": 0,
                    "queue": 0,
                    "threads": 0
                }
            },
            "timestamp": 1342734630015,
            "transport": {
                "rx_count": 0,
                "rx_size": "0b",
                "rx_size_in_bytes": 0,
                "server_open": 9,
                "tx_count": 0,
                "tx_size": "0b",
                "tx_size_in_bytes": 0
            },
            "transport_address": "inet[/127.0.0.1:9300]"
        }
    }
}
"""
