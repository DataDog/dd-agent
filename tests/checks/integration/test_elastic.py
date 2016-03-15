# stdlib
import os
import time
import socket

# 3p
from nose.plugins.attrib import attr
import requests

# project
from config import get_version
from tests.checks.common import AgentCheckTest, load_check

# Clusterwise metrics, pre aggregated on ES, compatible with all ES versions
PRIMARY_SHARD_METRICS = {
    "elasticsearch.primaries.docs.count": ("gauge", "_all.primaries.docs.count"),
    "elasticsearch.primaries.docs.deleted": ("gauge", "_all.primaries.docs.deleted"),
    "elasticsearch.primaries.store.size": ("gauge", "_all.primaries.store.size_in_bytes"),
    "elasticsearch.primaries.indexing.index.total": ("gauge", "_all.primaries.indexing.index_total"),
    "elasticsearch.primaries.indexing.index.time": ("gauge", "_all.primaries.indexing.index_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.primaries.indexing.index.current": ("gauge", "_all.primaries.indexing.index_current"),
    "elasticsearch.primaries.indexing.delete.total": ("gauge", "_all.primaries.indexing.delete_total"),
    "elasticsearch.primaries.indexing.delete.time": ("gauge", "_all.primaries.indexing.delete_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.primaries.indexing.delete.current": ("gauge", "_all.primaries.indexing.delete_current"),
    "elasticsearch.primaries.get.total": ("gauge", "_all.primaries.get.total"),
    "elasticsearch.primaries.get.time": ("gauge", "_all.primaries.get.time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.primaries.get.current": ("gauge", "_all.primaries.get.current"),
    "elasticsearch.primaries.get.exists.total": ("gauge", "_all.primaries.get.exists_total"),
    "elasticsearch.primaries.get.exists.time": ("gauge", "_all.primaries.get.exists_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.primaries.get.missing.total": ("gauge", "_all.primaries.get.missing_total"),
    "elasticsearch.primaries.get.missing.time": ("gauge", "_all.primaries.get.missing_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.primaries.search.query.total": ("gauge", "_all.primaries.search.query_total"),
    "elasticsearch.primaries.search.query.time": ("gauge", "_all.primaries.search.query_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.primaries.search.query.current": ("gauge", "_all.primaries.search.query_current"),
    "elasticsearch.primaries.search.fetch.total": ("gauge", "_all.primaries.search.fetch_total"),
    "elasticsearch.primaries.search.fetch.time": ("gauge", "_all.primaries.search.fetch_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.primaries.search.fetch.current": ("gauge", "_all.primaries.search.fetch_current")
}

PRIMARY_SHARD_METRICS_POST_1_0 = {
    "elasticsearch.primaries.merges.current": ("gauge", "_all.primaries.merges.current"),
    "elasticsearch.primaries.merges.current.docs": ("gauge", "_all.primaries.merges.current_docs"),
    "elasticsearch.primaries.merges.current.size": ("gauge", "_all.primaries.merges.current_size_in_bytes"),
    "elasticsearch.primaries.merges.total": ("gauge", "_all.primaries.merges.total"),
    "elasticsearch.primaries.merges.total.time": ("gauge", "_all.primaries.merges.total_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.primaries.merges.total.docs": ("gauge", "_all.primaries.merges.total_docs"),
    "elasticsearch.primaries.merges.total.size": ("gauge", "_all.primaries.merges.total_size_in_bytes"),
    "elasticsearch.primaries.refresh.total": ("gauge", "_all.primaries.refresh.total"),
    "elasticsearch.primaries.refresh.total.time": ("gauge", "_all.primaries.refresh.total_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.primaries.flush.total": ("gauge", "_all.primaries.flush.total"),
    "elasticsearch.primaries.flush.total.time": ("gauge", "_all.primaries.flush.total_time_in_millis", lambda v: float(v)/1000)
}

STATS_METRICS = {  # Metrics that are common to all Elasticsearch versions
    "elasticsearch.docs.count": ("gauge", "indices.docs.count"),
    "elasticsearch.docs.deleted": ("gauge", "indices.docs.deleted"),
    "elasticsearch.store.size": ("gauge", "indices.store.size_in_bytes"),
    "elasticsearch.indexing.index.total": ("gauge", "indices.indexing.index_total"),
    "elasticsearch.indexing.index.time": ("gauge", "indices.indexing.index_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.indexing.index.current": ("gauge", "indices.indexing.index_current"),
    "elasticsearch.indexing.delete.total": ("gauge", "indices.indexing.delete_total"),
    "elasticsearch.indexing.delete.time": ("gauge", "indices.indexing.delete_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.indexing.delete.current": ("gauge", "indices.indexing.delete_current"),
    "elasticsearch.get.total": ("gauge", "indices.get.total"),
    "elasticsearch.get.time": ("gauge", "indices.get.time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.get.current": ("gauge", "indices.get.current"),
    "elasticsearch.get.exists.total": ("gauge", "indices.get.exists_total"),
    "elasticsearch.get.exists.time": ("gauge", "indices.get.exists_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.get.missing.total": ("gauge", "indices.get.missing_total"),
    "elasticsearch.get.missing.time": ("gauge", "indices.get.missing_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.search.query.total": ("gauge", "indices.search.query_total"),
    "elasticsearch.search.query.time": ("gauge", "indices.search.query_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.search.query.current": ("gauge", "indices.search.query_current"),
    "elasticsearch.search.fetch.total": ("gauge", "indices.search.fetch_total"),
    "elasticsearch.search.fetch.time": ("gauge", "indices.search.fetch_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.search.fetch.current": ("gauge", "indices.search.fetch_current"),
    "elasticsearch.indices.segments.count": ("gauge", "indices.segments.count"),
    "elasticsearch.indices.segments.memory_in_bytes": ("gauge", "indices.segments.memory_in_bytes"),
    "elasticsearch.merges.current": ("gauge", "indices.merges.current"),
    "elasticsearch.merges.current.docs": ("gauge", "indices.merges.current_docs"),
    "elasticsearch.merges.current.size": ("gauge", "indices.merges.current_size_in_bytes"),
    "elasticsearch.merges.total": ("gauge", "indices.merges.total"),
    "elasticsearch.merges.total.time": ("gauge", "indices.merges.total_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.merges.total.docs": ("gauge", "indices.merges.total_docs"),
    "elasticsearch.merges.total.size": ("gauge", "indices.merges.total_size_in_bytes"),
    "elasticsearch.refresh.total": ("gauge", "indices.refresh.total"),
    "elasticsearch.refresh.total.time": ("gauge", "indices.refresh.total_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.flush.total": ("gauge", "indices.flush.total"),
    "elasticsearch.flush.total.time": ("gauge", "indices.flush.total_time_in_millis", lambda v: float(v)/1000),
    "elasticsearch.process.open_fd": ("gauge", "process.open_file_descriptors"),
    "elasticsearch.transport.rx_count": ("gauge", "transport.rx_count"),
    "elasticsearch.transport.tx_count": ("gauge", "transport.tx_count"),
    "elasticsearch.transport.rx_size": ("gauge", "transport.rx_size_in_bytes"),
    "elasticsearch.transport.tx_size": ("gauge", "transport.tx_size_in_bytes"),
    "elasticsearch.transport.server_open": ("gauge", "transport.server_open"),
    "elasticsearch.thread_pool.bulk.active": ("gauge", "thread_pool.bulk.active"),
    "elasticsearch.thread_pool.bulk.threads": ("gauge", "thread_pool.bulk.threads"),
    "elasticsearch.thread_pool.bulk.queue": ("gauge", "thread_pool.bulk.queue"),
    "elasticsearch.thread_pool.flush.active": ("gauge", "thread_pool.flush.active"),
    "elasticsearch.thread_pool.flush.threads": ("gauge", "thread_pool.flush.threads"),
    "elasticsearch.thread_pool.flush.queue": ("gauge", "thread_pool.flush.queue"),
    "elasticsearch.thread_pool.generic.active": ("gauge", "thread_pool.generic.active"),
    "elasticsearch.thread_pool.generic.threads": ("gauge", "thread_pool.generic.threads"),
    "elasticsearch.thread_pool.generic.queue": ("gauge", "thread_pool.generic.queue"),
    "elasticsearch.thread_pool.get.active": ("gauge", "thread_pool.get.active"),
    "elasticsearch.thread_pool.get.threads": ("gauge", "thread_pool.get.threads"),
    "elasticsearch.thread_pool.get.queue": ("gauge", "thread_pool.get.queue"),
    "elasticsearch.thread_pool.index.active": ("gauge", "thread_pool.index.active"),
    "elasticsearch.thread_pool.index.threads": ("gauge", "thread_pool.index.threads"),
    "elasticsearch.thread_pool.index.queue": ("gauge", "thread_pool.index.queue"),
    "elasticsearch.thread_pool.management.active": ("gauge", "thread_pool.management.active"),
    "elasticsearch.thread_pool.management.threads": ("gauge", "thread_pool.management.threads"),
    "elasticsearch.thread_pool.management.queue": ("gauge", "thread_pool.management.queue"),
    "elasticsearch.thread_pool.merge.active": ("gauge", "thread_pool.merge.active"),
    "elasticsearch.thread_pool.merge.threads": ("gauge", "thread_pool.merge.threads"),
    "elasticsearch.thread_pool.merge.queue": ("gauge", "thread_pool.merge.queue"),
    "elasticsearch.thread_pool.percolate.active": ("gauge", "thread_pool.percolate.active"),
    "elasticsearch.thread_pool.percolate.threads": ("gauge", "thread_pool.percolate.threads"),
    "elasticsearch.thread_pool.percolate.queue": ("gauge", "thread_pool.percolate.queue"),
    "elasticsearch.thread_pool.refresh.active": ("gauge", "thread_pool.refresh.active"),
    "elasticsearch.thread_pool.refresh.threads": ("gauge", "thread_pool.refresh.threads"),
    "elasticsearch.thread_pool.refresh.queue": ("gauge", "thread_pool.refresh.queue"),
    "elasticsearch.thread_pool.search.active": ("gauge", "thread_pool.search.active"),
    "elasticsearch.thread_pool.search.threads": ("gauge", "thread_pool.search.threads"),
    "elasticsearch.thread_pool.search.queue": ("gauge", "thread_pool.search.queue"),
    "elasticsearch.thread_pool.snapshot.active": ("gauge", "thread_pool.snapshot.active"),
    "elasticsearch.thread_pool.snapshot.threads": ("gauge", "thread_pool.snapshot.threads"),
    "elasticsearch.thread_pool.snapshot.queue": ("gauge", "thread_pool.snapshot.queue"),
    "elasticsearch.http.current_open": ("gauge", "http.current_open"),
    "elasticsearch.http.total_opened": ("gauge", "http.total_opened"),
    "jvm.mem.heap_committed": ("gauge", "jvm.mem.heap_committed_in_bytes"),
    "jvm.mem.heap_used": ("gauge", "jvm.mem.heap_used_in_bytes"),
    "jvm.mem.heap_in_use": ("gauge", "jvm.mem.heap_used_percent"),
    "jvm.mem.heap_max": ("gauge", "jvm.mem.heap_max_in_bytes"),
    "jvm.mem.non_heap_committed": ("gauge", "jvm.mem.non_heap_committed_in_bytes"),
    "jvm.mem.non_heap_used": ("gauge", "jvm.mem.non_heap_used_in_bytes"),
    "jvm.threads.count": ("gauge", "jvm.threads.count"),
    "jvm.threads.peak_count": ("gauge", "jvm.threads.peak_count"),
    "elasticsearch.fs.total.total_in_bytes": ("gauge", "fs.total.total_in_bytes"),
    "elasticsearch.fs.total.free_in_bytes": ("gauge", "fs.total.free_in_bytes"),
    "elasticsearch.fs.total.available_in_bytes": ("gauge", "fs.total.available_in_bytes"),
}

JVM_METRICS_POST_0_90_10 = {
    "jvm.gc.collectors.young.count": ("gauge", "jvm.gc.collectors.young.collection_count"),
    "jvm.gc.collectors.young.collection_time": ("gauge", "jvm.gc.collectors.young.collection_time_in_millis", lambda v: float(v)/1000),
    "jvm.gc.collectors.old.count": ("gauge", "jvm.gc.collectors.old.collection_count"),
    "jvm.gc.collectors.old.collection_time": ("gauge", "jvm.gc.collectors.old.collection_time_in_millis", lambda v: float(v)/1000)
}

JVM_METRICS_PRE_0_90_10 = {
    "jvm.gc.concurrent_mark_sweep.count": ("gauge", "jvm.gc.collectors.ConcurrentMarkSweep.collection_count"),
    "jvm.gc.concurrent_mark_sweep.collection_time": ("gauge", "jvm.gc.collectors.ConcurrentMarkSweep.collection_time_in_millis", lambda v: float(v)/1000),
    "jvm.gc.par_new.count": ("gauge", "jvm.gc.collectors.ParNew.collection_count"),
    "jvm.gc.par_new.collection_time": ("gauge", "jvm.gc.collectors.ParNew.collection_time_in_millis", lambda v: float(v)/1000),
    "jvm.gc.collection_count": ("gauge", "jvm.gc.collection_count"),
    "jvm.gc.collection_time": ("gauge", "jvm.gc.collection_time_in_millis", lambda v: float(v)/1000),
}

ADDITIONAL_METRICS_POST_0_90_5 = {
    "elasticsearch.search.fetch.open_contexts": ("gauge", "indices.search.open_contexts"),
    "elasticsearch.cache.filter.evictions": ("gauge", "indices.filter_cache.evictions"),
    "elasticsearch.cache.filter.size": ("gauge", "indices.filter_cache.memory_size_in_bytes"),
    "elasticsearch.id_cache.size": ("gauge", "indices.id_cache.memory_size_in_bytes"),
    "elasticsearch.fielddata.size": ("gauge", "indices.fielddata.memory_size_in_bytes"),
    "elasticsearch.fielddata.evictions": ("gauge", "indices.fielddata.evictions"),
}

ADDITIONAL_METRICS_PRE_0_90_5 = {
    "elasticsearch.cache.field.evictions": ("gauge", "indices.cache.field_evictions"),
    "elasticsearch.cache.field.size": ("gauge", "indices.cache.field_size_in_bytes"),
    "elasticsearch.cache.filter.count": ("gauge", "indices.cache.filter_count"),
    "elasticsearch.cache.filter.evictions": ("gauge", "indices.cache.filter_evictions"),
    "elasticsearch.cache.filter.size": ("gauge", "indices.cache.filter_size_in_bytes"),
}

ADDITIONAL_METRICS_POST_1_0_0 = {
    "elasticsearch.indices.translog.size_in_bytes": ("gauge", "indices.translog.size_in_bytes"),
    "elasticsearch.indices.translog.operations": ("gauge", "indices.translog.operations"),
    # Currently has issues in test framework:
    # "elasticsearch.fs.total.disk_reads": ("rate", "fs.total.disk_reads"),
    # "elasticsearch.fs.total.disk_writes": ("rate", "fs.total.disk_writes"),
    # "elasticsearch.fs.total.disk_io_op": ("rate", "fs.total.disk_io_op"),
    # "elasticsearch.fs.total.disk_read_size_in_bytes": ("gauge", "fs.total.disk_read_size_in_bytes"),
    # "elasticsearch.fs.total.disk_write_size_in_bytes": ("gauge", "fs.total.disk_write_size_in_bytes"),
    # "elasticsearch.fs.total.disk_io_size_in_bytes": ("gauge", "fs.total.disk_io_size_in_bytes"),
}

ADDITIONAL_METRICS_POST_1_3_0 = {
    "elasticsearch.indices.segments.index_writer_memory_in_bytes": ("gauge", "indices.segments.index_writer_memory_in_bytes"),
    "elasticsearch.indices.segments.version_map_memory_in_bytes": ("gauge", "indices.segments.version_map_memory_in_bytes"),
}

ADDITIONAL_METRICS_POST_1_4_0 = {
    "elasticsearch.indices.segments.index_writer_max_memory_in_bytes": ("gauge", "indices.segments.index_writer_max_memory_in_bytes"),
    "elasticsearch.indices.segments.fixed_bit_set_memory_in_bytes": ("gauge", "indices.segments.fixed_bit_set_memory_in_bytes"),
}

CLUSTER_HEALTH_METRICS = {
    "elasticsearch.number_of_nodes": ("gauge", "number_of_nodes"),
    "elasticsearch.number_of_data_nodes": ("gauge", "number_of_data_nodes"),
    "elasticsearch.active_primary_shards": ("gauge", "active_primary_shards"),
    "elasticsearch.active_shards": ("gauge", "active_shards"),
    "elasticsearch.relocating_shards": ("gauge", "relocating_shards"),
    "elasticsearch.initializing_shards": ("gauge", "initializing_shards"),
    "elasticsearch.unassigned_shards": ("gauge", "unassigned_shards"),
    "elasticsearch.cluster_status": ("gauge", "status", lambda v: {"red": 0, "yellow": 1, "green": 2}.get(v, -1)),
}

CLUSTER_PENDING_TASKS = {
    "elasticsearch.pending_tasks_total": ("gauge", "pending_task_total"),
    "elasticsearch.pending_tasks_priority_high": ("gauge", "pending_tasks_priority_high"),
    "elasticsearch.pending_tasks_priority_urgent": ("gauge", "pending_tasks_priority_urgent")
}


def get_es_version():
    version = os.environ.get("FLAVOR_VERSION")
    if version is None:
        return [1, 6, 0]
    return [int(k) for k in version.split(".")]


@attr(requires='elasticsearch')
class TestElastic(AgentCheckTest):
    CHECK_NAME = "elastic"

    def test_check(self):
        conf_hostname = "foo"
        port = 9200
        bad_port = 9405
        agent_config = {
            "hostname": conf_hostname, "version": get_version(),
            "api_key": "bar"
        }

        tags = ['foo:bar', 'baz']
        url = 'http://localhost:{0}'.format(port)
        bad_url = 'http://localhost:{0}'.format(bad_port)

        config = {
            'instances': [
                {'url': url, 'tags': tags},  # One with tags not external
                {'url': url, 'cluster_stats': True},  # One without tags, external
                {'url': bad_url},  # One bad url
            ]
        }

        self.assertRaises(
            requests.exceptions.ConnectionError,
            self.run_check, config=config, agent_config=agent_config)

        default_tags = ["url:http://localhost:{0}".format(port)]

        expected_metrics = STATS_METRICS
        CLUSTER_HEALTH_METRICS.update(CLUSTER_PENDING_TASKS)
        expected_metrics.update(CLUSTER_HEALTH_METRICS)

        instance_config = self.check.get_instance_config(config['instances'][0])
        es_version = self.check._get_es_version(instance_config)

        self.assertEquals(es_version, get_es_version())

        if es_version >= [0, 90, 5]:
            expected_metrics.update(ADDITIONAL_METRICS_POST_0_90_5)
            if es_version >= [0, 90, 10]:
                expected_metrics.update(JVM_METRICS_POST_0_90_10)
            else:
                expected_metrics.update(JVM_METRICS_PRE_0_90_10)
        else:
            expected_metrics.update(ADDITIONAL_METRICS_PRE_0_90_5)
            expected_metrics.update(JVM_METRICS_PRE_0_90_10)

        if es_version >= [1, 0, 0]:
            expected_metrics.update(ADDITIONAL_METRICS_POST_1_0_0)

        if es_version >= [1, 3, 0]:
            expected_metrics.update(ADDITIONAL_METRICS_POST_1_3_0)

        if es_version >= [1, 4, 0]:
            expected_metrics.update(ADDITIONAL_METRICS_POST_1_4_0)

        contexts = [
            (conf_hostname, default_tags + tags),
            (socket.gethostname(), default_tags)
        ]

        for m_name, desc in expected_metrics.iteritems():
            for hostname, m_tags in contexts:
                if (m_name in CLUSTER_HEALTH_METRICS
                        and hostname == socket.gethostname()):
                    hostname = conf_hostname

                if desc[0] == "gauge":
                    self.assertMetric(
                        m_name, tags=m_tags, count=1, hostname=hostname)

        good_sc_tags = ['host:localhost', 'port:{0}'.format(port)]
        bad_sc_tags = ['host:localhost', 'port:{0}'.format(bad_port)]

        self.assertServiceCheckOK('elasticsearch.can_connect',
                                  tags=good_sc_tags + tags,
                                  count=1)
        self.assertServiceCheckOK('elasticsearch.can_connect',
                                  tags=good_sc_tags,
                                  count=1)
        self.assertServiceCheckCritical('elasticsearch.can_connect',
                                        tags=bad_sc_tags,
                                        count=1)

        # Assert service metadata
        self.assertServiceMetadata(['version'], count=3)

        # FIXME: 0.90.13 returns randomly a red status instead of yellow,
        # so we don't do a coverage test for it
        # Remove me when we stop supporting 0.90.x (not supported anymore by ES)
        if get_es_version() != [0, 90, 13]:
            # Warning because elasticsearch status should be yellow, according to
            # http://chrissimpson.co.uk/elasticsearch-yellow-cluster-status-explained.html
            self.assertServiceCheckWarning('elasticsearch.cluster_health',
                                           tags=good_sc_tags + tags,
                                           count=1)
            self.assertServiceCheckWarning('elasticsearch.cluster_health',
                                           tags=good_sc_tags,
                                           count=1)
            # Assert event
            self.assertEvent('ElasticSearch: foo just reported as yellow', count=1,
                             tags=default_tags+tags, msg_title='foo is yellow',
                             event_type='elasticsearch', alert_type='warning',
                             source_type_name='elasticsearch')

            self.coverage_report()

    def test_config_parser(self):
        check = load_check(self.CHECK_NAME, {}, {})
        instance = {
            "username": "user",
            "password": "pass",
            "is_external": "yes",
            "url": "http://foo.bar",
            "tags": ["a", "b:c"],
        }

        c = check.get_instance_config(instance)
        self.assertEquals(c.username, "user")
        self.assertEquals(c.password, "pass")
        self.assertEquals(c.cluster_stats, True)
        self.assertEquals(c.url, "http://foo.bar")
        self.assertEquals(c.tags, ["url:http://foo.bar", "a", "b:c"])
        self.assertEquals(c.timeout, check.DEFAULT_TIMEOUT)
        self.assertEquals(c.service_check_tags, ["host:foo.bar", "port:None", "a", "b:c"])

        instance = {
            "url": "http://192.168.42.42:12999",
            "timeout": 15
        }

        c = check.get_instance_config(instance)
        self.assertEquals(c.username, None)
        self.assertEquals(c.password, None)
        self.assertEquals(c.cluster_stats, False)
        self.assertEquals(c.url, "http://192.168.42.42:12999")
        self.assertEquals(c.tags, ["url:http://192.168.42.42:12999"])
        self.assertEquals(c.timeout, 15)
        self.assertEquals(c.service_check_tags,
                          ["host:192.168.42.42", "port:12999"])

    def test_health_event(self):
        dummy_tags = ['foo:bar', 'elastique:recherche']
        config = {'instances': [
            {'url': 'http://localhost:9200', 'tags': dummy_tags}
        ]}

        # Should be yellow at first
        requests.put('http://localhost:9200/_settings', data='{"index": {"number_of_replicas": 1}}')
        self.run_check(config)

        self.assertEquals(len(self.events), 1)
        self.assertIn('yellow', self.events[0]['msg_title'])
        self.assertEquals(
            ['url:http://localhost:9200'] + dummy_tags,
            self.events[0]['tags']
        )
        self.assertServiceCheckWarning(
            'elasticsearch.cluster_health',
            tags=['host:localhost', 'port:9200'] + dummy_tags,
            count=1
        )

        # Set number of replicas to 0 for all indices
        requests.put('http://localhost:9200/_settings', data='{"index": {"number_of_replicas": 0}}')
        time.sleep(5)
        # Now shards should be green
        self.run_check(config)

        self.assertEquals(len(self.events), 1)
        self.assertIn('green', self.events[0]['msg_title'])
        self.assertEquals(
            ['url:http://localhost:9200'] + dummy_tags,
            self.events[0]['tags']
        )
        self.assertServiceCheckOK(
            'elasticsearch.cluster_health',
            tags=['host:localhost', 'port:9200'] + dummy_tags,
            count=1
        )

    def test_pshard_metrics(self):
        """ Tests that the pshard related metrics are forwarded and that the
        document count for primary indexes is twice smaller as the global
        document count when "number_of_replicas" is set to 1 """
        elastic_latency = 10

        config = {'instances': [
            {'url': 'http://localhost:9200', 'pshard_stats': True}
        ]}
        # Cleaning up everything won't hurt.
        req = requests.get('http://localhost:9200/_cat/indices?v')
        indices_info = req.text.split('\n')[1::-1]
        for index_info in indices_info:
            index_name = index_info.split()[1]
            requests.delete('http://localhost:9200/' + index_name)

        requests.put('http://localhost:9200/_settings', data='{"index": {"number_of_replicas": 1}}')
        requests.put('http://localhost:9200/testindex/testtype/2', data='{"name": "Jane Doe", "age": 27}')
        requests.put('http://localhost:9200/testindex/testtype/1', data='{"name": "John Doe", "age": 42}')

        time.sleep(elastic_latency)

        self.run_check(config)

        pshard_stats_metrics = dict(PRIMARY_SHARD_METRICS)
        if get_es_version() >= [1, 0, 0]:
            pshard_stats_metrics.update(PRIMARY_SHARD_METRICS_POST_1_0)

        for m_name, desc in pshard_stats_metrics.iteritems():
            if desc[0] == "gauge":
                self.assertMetric(m_name, count=1)

        # Our pshard metrics are getting sent, let's check that they're accurate
        # Note: please make sure you don't install Maven on the CI for future
        # elastic search CI integrations. It would make the line below fail :/
        self.assertMetric('elasticsearch.primaries.docs.count', value=2)
