# (C) Datadog, Inc. 2013-2016
# (C) Stefan Mees <stefan.mees@wooga.net> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import socket

# 3rd party
from httplib2 import Http, HttpLib2Error
import simplejson as json

# project
from checks import AgentCheck


class Riak(AgentCheck):
    SERVICE_CHECK_NAME = 'riak.can_connect'

    keys = [
        #KV Throughput Statistics
        "node_gets",
        "node_gets_total",
        "node_puts",
        "node_puts_total",
        #CRDT Throughput Statistics
        "node_gets_counter",
        "node_gets_counter_total",
        "node_gets_set",
        "node_gets_set_total",
        "node_gets_map",
        "node_gets_map_total",
        "node_puts_counter",
        "node_puts_counter_total",
        "node_puts_set",
        "node_puts_set_total",
        "node_puts_map",
        "node_puts_map_total",
        "object_merge",
        "object_merge_total",
        "object_counter_merge",
        "object_counter_merge_total",
        "object_set_merge",
        "object_set_merge_total",
        "object_map_merge",
        "object_map_merge_total",
        #Protocol Buffers Statistics
        "pbc_active",
        "pbc_connects",
        "pbc_connects_total",
        #Read Repair Statistics
        "read_repairs",
        "read_repairs_total",
        "skipped_read_repairs",
        "skipped_read_repairs_total",
        "read_repairs_counter",
        "read_repairs_counter_total",
        "read_repairs_set",
        "read_repairs_set_total",
        "read_repairs_map",
        "read_repairs_map_total",
        "read_repairs_primary_notfound_one",
        "read_repairs_primary_notfound_count",
        "read_repairs_primary_outofdate_one",
        "read_repairs_primary_outofdate_count",
        "read_repairs_fallback_notfound_one",
        "read_repairs_fallback_notfound_count",
        "read_repairs_fallback_outofdate_one",
        "read_repairs_fallback_outofdate_count",
        #Overload Protection Statistics
        "node_get_fsm_active",
        "node_get_fsm_active_60s",
        "node_get_fsm_in_rate",
        "node_get_fsm_out_rate",
        "node_get_fsm_rejected",
        "node_get_fsm_rejected_60s",
        "node_get_fsm_rejected_total",
        "node_get_fsm_errors",
        "node_get_fsm_errors_total",
        "node_put_fsm_active",
        "node_put_fsm_active_60s",
        "node_put_fsm_in_rate",
        "node_put_fsm_out_rate",
        "node_put_fsm_rejected",
        "node_put_fsm_rejected_60s",
        "node_put_fsm_rejected_total",
        #VNode Statistics
        "riak_kv_vnodes_running",
        "vnode_gets",
        "vnode_gets_total",
        "vnode_puts",
        "vnode_puts_total",
        "vnode_counter_update",
        "vnode_counter_update_total",
        "vnode_set_update",
        "vnode_set_update_total",
        "vnode_map_update",
        "vnode_map_update_total",
        "vnode_index_deletes",
        "vnode_index_deletes_postings",
        "vnode_index_deletes_postings_total",
        "vnode_index_deletes_total",
        "vnode_index_reads",
        "vnode_index_reads_total",
        "vnode_index_refreshes",
        "vnode_index_refreshes_total",
        "vnode_index_writes",
        "vnode_index_writes_postings",
        "vnode_index_writes_postings_total",
        "vnode_index_writes_total",
        "dropped_vnode_requests_total",
        #Search Statistics
        "search_index_fail_one",
        "search_index_fail_count",
        "search_index_throughput_one",
        "search_index_throughput_count",
        "search_query_fail_one",
        "search_query_fail_count",
        "search_query_throughput_one",
        "search_query_throughput_count",
        #Keylisting Statistics
        "list_fsm_active",
        "list_fsm_create",
        "list_fsm_create_total",
        "list_fsm_create_error",
        "list_fsm_create_error_total",
        #Secondary Indexing Statistics
        "index_fsm_active",
        "index_fsm_create",
        "index_fsm_create_error",
        #MapReduce Statistics
        "riak_pipe_vnodes_running",
        "executing_mappers",
        "pipeline_active",
        "pipeline_create_count",
        "pipeline_create_error_count",
        "pipeline_create_error_one",
        "pipeline_create_one",
        #Ring Statistics
        "rings_reconciled",
        "rings_reconciled_total",
        "converge_delay_last",
        "converge_delay_max",
        "converge_delay_mean",
        "converge_delay_min",
        "rebalance_delay_last",
        "rebalance_delay_max",
        "rebalance_delay_mean",
        "rebalance_delay_min",
        "rejected_handoffs",
        "handoff_timeouts",
        "coord_redirs_total",
        "gossip_received",
        "ignored_gossip_total",
        #System Statistics
        "mem_allocated",
        "mem_total",
        "memory_atom",
        "memory_atom_used",
        "memory_binary",
        "memory_code",
        "memory_ets",
        "memory_processes",
        "memory_processes_used",
        "memory_system",
        "memory_total",
        "sys_monitor_count",
        "sys_port_count",
        "sys_process_count",
        #Misc. Statistics
        "late_put_fsm_coordinator_ack",
        "postcommit_fail",
        "precommit_fail",
        "leveldb_read_block_error"
    ]

    stat_keys = [
        #KV Latency and Object Statistics
        "node_get_fsm_objsize",
        "node_get_fsm_siblings",
        "node_get_fsm_time",
        "node_put_fsm_time",
        #CRDT Latency and Object Statistics
        "node_get_fsm_counter_time",
        "node_get_fsm_set_time",
        "node_get_fsm_map_time",
        "node_put_fsm_counter_time",
        "node_put_fsm_set_time",
        "node_put_fsm_map_time",
        "node_get_fsm_counter_objsize",
        "node_get_fsm_counter_siblings",
        "node_get_fsm_set_objsize",
        "node_get_fsm_set_siblings",
        "node_get_fsm_map_objsize",
        "node_get_fsm_map_siblings",
        "object_merge_time",
        "object_counter_merge_time",
        "object_set_merge_time",
        "object_map_merge_time",
        "counter_actor_counts",
        "set_actor_counts",
        "map_actor_counts",
        #VNode Latency and Object Statistics
        "vnode_get_fsm_time",
        "vnode_put_fsm_time",
        "vnode_counter_update_time",
        "vnode_set_update_time",
        "vnode_map_update_time"
    ]

    search_latency_keys = [
        "search_query_latency",
        "search_index_latency"
    ]

    vnodeq_keys = [
        "riak_kv_vnodeq",
        "riak_pipe_vnodeq"
    ]

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        for k in ["mean", "median", "95", "99", "100"]:
            for m in self.stat_keys:
                self.keys.append(m + "_" + k)

        for k in ["min", "max", "mean", "median", "95", "99", "999"]:
            for m in self.search_latency_keys:
                self.keys.append(m + "_" + k)

        for k in ["min", "max", "mean", "median", "total"]:
            for m in self.vnodeq_keys:
                self.keys.append(m + "_" + k)

        self.prev_coord_redirs_total = -1

    def check(self, instance):
        url = instance['url']
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))
        cacert = instance.get('cacert', None)
        disable_cert_verify = instance.get('disable_cert_verify', False)
        tags = instance.get('tags', [])
        service_check_tags = tags + ['url:%s' % url]

        try:
            h = Http(timeout=timeout,
                     ca_certs=cacert,
                     disable_ssl_certificate_validation=disable_cert_verify)
            resp, content = h.request(url, "GET")
        except (socket.timeout, socket.error, HttpLib2Error) as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               message="Unable to fetch Riak stats: %s" % str(e),
                               tags=service_check_tags)
            raise

        if resp.status != 200:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags,
                               message="Unexpected status of %s when fetching Riak stats, "
                               "response: %s" % (resp.status, content))

        stats = json.loads(content)
        self.service_check(
            self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

        for k in self.keys:
            if k in stats:
                self.gauge("riak." + k, stats[k], tags=tags)

        coord_redirs_total = stats["coord_redirs_total"]
        if self.prev_coord_redirs_total > -1:
            count = coord_redirs_total - self.prev_coord_redirs_total
            self.gauge('riak.coord_redirs', count)

        self.prev_coord_redirs_total = coord_redirs_total
