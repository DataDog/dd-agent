# stdlib
import re
import time
import json
# 3p
from subprocess import check_output, call

# project
from checks import AgentCheck
from urlparse import urlsplit

DEFAULT_TIMEOUT = 30
GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate


class Aerospike(AgentCheck):
    """
    Aerospike agent check.
    """
    # Source
    SOURCE_TYPE_NAME = 'aerospike'

    # Service check
    SERVICE_CHECK_NAME = 'aerospike.can_connect'

    # Metrics
    """
    Core metrics collected by default.
    """
    SERVICE_METRICS = {
        "cluster_size": GAUGE,
        "cluster_key": GAUGE,
        "cluster_integrity": GAUGE,
        "objects": GAUGE,
        "sub-records": GAUGE,
        "total-bytes-disk": GAUGE,
        "used-bytes-disk": GAUGE,
        "free-pct-disk": GAUGE,
        "total-bytes-memory": GAUGE,
        "used-bytes-memory": GAUGE,
        "data-used-bytes-memory": GAUGE,
        "index-used-bytes-memory": GAUGE,
        "sindex-used-bytes-memory": GAUGE,
        "free-pct-memory": GAUGE,
        "stat_read_reqs": GAUGE,
        "stat_read_reqs_xdr": GAUGE,
        "stat_read_success": GAUGE,
        "stat_read_errs_notfound": GAUGE,
        "stat_read_errs_other": GAUGE,
        "stat_write_reqs": GAUGE,
        "stat_write_reqs_xdr": GAUGE,
        "stat_write_success": GAUGE,
        "stat_write_errs": GAUGE,
        "stat_delete_success": GAUGE,
        "stat_rw_timeout": GAUGE,
        "udf_read_reqs": GAUGE,
        "udf_read_success": GAUGE,
        "udf_read_errs_other": GAUGE,
        "udf_write_reqs": GAUGE,
        "udf_write_success": GAUGE,
        "udf_write_err_others": GAUGE,
        "udf_delete_reqs": GAUGE,
        "udf_delete_success": GAUGE,
        "udf_delete_err_others": GAUGE,
        "udf_lua_errs": GAUGE,
        "udf_scan_rec_reqs": GAUGE,
        "udf_query_rec_reqs": GAUGE,
        "udf_replica_writes": GAUGE,
        "stat_proxy_reqs": GAUGE,
        "stat_proxy_reqs_xdr": GAUGE,
        "stat_proxy_success": GAUGE,
        "stat_proxy_errs": GAUGE,
        "stat_ldt_proxy": GAUGE,
        "stat_cluster_key_err_ack_dup_trans_reenqueue": GAUGE,
        "stat_expired_objects": GAUGE,
        "stat_evicted_objects": GAUGE,
        "stat_deleted_set_objects": GAUGE,
        "stat_evicted_objects_time": GAUGE,
        "stat_zero_bin_records": GAUGE,
        "stat_nsup_deletes_not_shipped": GAUGE,
        "stat_compressed_pkts_received": GAUGE,
        "err_tsvc_requests": GAUGE,
        "err_tsvc_requests_timeout": GAUGE,
        "err_out_of_space": GAUGE,
        "err_duplicate_proxy_request": GAUGE,
        "err_rw_request_not_found": GAUGE,
        "err_rw_pending_limit": GAUGE,
        "err_rw_cant_put_unique": GAUGE,
        "geo_region_query_count": GAUGE,
        "geo_region_query_cells": GAUGE,
        "geo_region_query_points": GAUGE,
        "geo_region_query_falsepos": GAUGE,
        "fabric_msgs_sent": GAUGE,
        "fabric_msgs_rcvd": GAUGE,
        "paxos_principal": GAUGE,
        "migrate_allowed": GAUGE,
        "migrate_progress_send": GAUGE,
        "migrate_progress_recv": GAUGE,
        "migrate_partitions_remaining": GAUGE,
        "queue": GAUGE,
        "transactions": GAUGE,
        "reaped_fds": GAUGE,
        "scans_active": GAUGE,
        "basic_scans_succeeded": GAUGE,
        "basic_scans_failed": GAUGE,
        "aggr_scans_succeeded": GAUGE,
        "aggr_scans_failed": GAUGE,
        "udf_bg_scans_succeeded": GAUGE,
        "udf_bg_scans_failed": GAUGE,
        "batch_index_initiate": GAUGE,
        "batch_index_queue": GAUGE,
        "batch_index_complete": GAUGE,
        "batch_index_timeout": GAUGE,
        "batch_index_errors": GAUGE,
        "batch_index_unused_buffers": GAUGE,
        "batch_index_huge_buffers": GAUGE,
        "batch_index_created_buffers": GAUGE,
        "batch_index_destroyed_buffers": GAUGE,
        "batch_initiate": GAUGE,
        "batch_queue": GAUGE,
        "batch_tree_count": GAUGE,
        "batch_timeout": GAUGE,
        "batch_errors": GAUGE,
        "info_queue": GAUGE,
        "delete_queue": GAUGE,
        "proxy_in_progress": GAUGE,
        "proxy_initiate": GAUGE,
        "proxy_action": GAUGE,
        "proxy_retry": GAUGE,
        "proxy_retry_q_full": GAUGE,
        "proxy_unproxy": GAUGE,
        "proxy_retry_same_dest": GAUGE,
        "proxy_retry_new_dest": GAUGE,
        "write_master": GAUGE,
        "write_prole": GAUGE,
        "read_dup_prole": GAUGE,
        "rw_err_dup_internal": GAUGE,
        "rw_err_dup_cluster_key": GAUGE,
        "rw_err_dup_send": GAUGE,
        "rw_err_write_internal": GAUGE,
        "rw_err_write_cluster_key": GAUGE,
        "rw_err_write_send": GAUGE,
        "rw_err_ack_internal": GAUGE,
        "rw_err_ack_nomatch": GAUGE,
        "rw_err_ack_badnode": GAUGE,
        "client_connections": GAUGE,
        "waiting_transactions": GAUGE,
        "tree_count": GAUGE,
        "record_refs": GAUGE,
        "record_locks": GAUGE,
        "ongoing_write_reqs": GAUGE,
        "err_storage_queue_full": GAUGE,
        "partition_actual": GAUGE,
        "partition_replica": GAUGE,
        "partition_desync": GAUGE,
        "partition_absent": GAUGE,
        "partition_zombie": GAUGE,
        "partition_object_count": GAUGE,
        "partition_ref_count": GAUGE,
        "system_free_mem_pct": GAUGE,
        "sindex_ucgarbage_found": GAUGE,
        "sindex_gc_locktimedout": GAUGE,
        "sindex_gc_inactivity_dur": GAUGE,
        "sindex_gc_activity_dur": GAUGE,
        "sindex_gc_list_creation_time": GAUGE,
        "sindex_gc_list_deletion_time": GAUGE,
        "sindex_gc_objects_validated": GAUGE,
        "sindex_gc_garbage_found": GAUGE,
        "sindex_gc_garbage_cleaned": GAUGE,
        "system_swapping": GAUGE,
        "err_replica_null_node": GAUGE,
        "err_replica_non_null_node": GAUGE,
        "err_sync_copy_null_master": GAUGE,
        "storage_defrag_corrupt_record": GAUGE,
        "err_write_fail_prole_unknown": GAUGE,
        "err_write_fail_prole_generation": GAUGE,
        "err_write_fail_unknown": GAUGE,
        "err_write_fail_key_exists": GAUGE,
        "err_write_fail_generation": GAUGE,
        "err_write_fail_bin_exists": GAUGE,
        "err_write_fail_parameter": GAUGE,
        "err_write_fail_incompatible_type": GAUGE,
        "err_write_fail_prole_delete": GAUGE,
        "err_write_fail_not_found": GAUGE,
        "err_write_fail_key_mismatch": GAUGE,
        "err_write_fail_record_too_big": GAUGE,
        "err_write_fail_bin_name": GAUGE,
        "err_write_fail_bin_not_found": GAUGE,
        "err_write_fail_forbidden": GAUGE,
        "stat_duplicate_operation": GAUGE,
        "uptime": GAUGE,
        "stat_write_errs_notfound": GAUGE,
        "stat_write_errs_other": GAUGE,
        "heartbeat_received_self": GAUGE,
        "heartbeat_received_foreign": GAUGE,
        "query_reqs": GAUGE,
        "query_success": GAUGE,
        "query_fail": GAUGE,
        "query_abort": GAUGE,
        "query_avg_rec_count": GAUGE,
        "query_short_running": GAUGE,
        "query_long_running": GAUGE,
        "query_short_queue_full": GAUGE,
        "query_long_queue_full": GAUGE,
        "query_short_reqs": GAUGE,
        "query_long_reqs": GAUGE,
        "query_agg": GAUGE,
        "query_agg_success": GAUGE,
        "query_agg_err": GAUGE,
        "query_agg_abort": GAUGE,
        "query_agg_avg_rec_count": GAUGE,
        "query_lookups": GAUGE,
        "query_lookup_success": GAUGE,
        "query_lookup_err": GAUGE,
        "query_lookup_abort": GAUGE,
        "query_lookup_avg_rec_count": GAUGE,
    }

    FREQUENCYCAP_METRICS = {
        "objects": GAUGE,
        "sub-objects": GAUGE,
        "master-objects": GAUGE,
        "master-sub-objects": GAUGE,
        "prole-objects": GAUGE,
        "prole-sub-objects": GAUGE,
        "expired-objects": GAUGE,
        "evicted-objects": GAUGE,
        "set-deleted-objects": GAUGE,
        "nsup-cycle-duration": GAUGE,
        "nsup-cycle-sleep-pct": GAUGE,
        "used-bytes-memory": GAUGE,
        "data-used-bytes-memory": GAUGE,
        "index-used-bytes-memory": GAUGE,
        "sindex-used-bytes-memory": GAUGE,
        "free-pct-memory": GAUGE,
        "max-void-time": GAUGE,
        "non-expirable-objects": GAUGE,
        "current-time": GAUGE,
        "stop-writes": GAUGE,
        "hwm-breached": GAUGE,
        "available-bin-names": GAUGE,
        "migrate-tx-partitions-imbalance": GAUGE,
        "migrate-tx-instance-count": GAUGE,
        "migrate-rx-instance-count": GAUGE,
        "migrate-tx-partitions-active": GAUGE,
        "migrate-rx-partitions-active": GAUGE,
        "migrate-tx-partitions-initial": GAUGE,
        "migrate-tx-partitions-remaining": GAUGE,
        "migrate-rx-partitions-initial": GAUGE,
        "migrate-rx-partitions-remaining": GAUGE,
        "migrate-records-skipped": GAUGE,
        "migrate-records-transmitted": GAUGE,
        "migrate-record-retransmits": GAUGE,
        "migrate-record-receives": GAUGE,
        "used-bytes-disk": GAUGE,
        "free-pct-disk": GAUGE,
        "available_pct": GAUGE,
        "cache-read-pct": GAUGE,
        "memory-size": GAUGE,
        "high-water-disk-pct": GAUGE,
        "high-water-memory-pct": GAUGE,
        "evict-tenths-pct": GAUGE,
        "evict-hist-buckets": GAUGE,
        "stop-writes-pct": GAUGE,
        "cold-start-evict-ttl": GAUGE,
        "repl-factor": GAUGE,
        "default-ttl": GAUGE,
        "max-ttl": GAUGE,
        "conflict-resolution-policy": GAUGE,
        "single-bin": GAUGE,
        "ldt-enabled": GAUGE,
        "ldt-page-size": GAUGE,
        "enable-xdr": GAUGE,
        "sets-enable-xdr": GAUGE,
        "ns-forward-xdr-writes": GAUGE,
        "allow-nonxdr-writes": GAUGE,
        "allow-xdr-writes": GAUGE,
        "disallow-null-setname": GAUGE,
        "total-bytes-memory": GAUGE,
        "read-consistency-level-override": GAUGE,
        "write-commit-level-override": GAUGE,
        "migrate-order": GAUGE,
        "migrate-sleep": GAUGE,
        "total-bytes-disk": GAUGE,
        "defrag-lwm-pct": GAUGE,
        "defrag-queue-min": GAUGE,
        "defrag-sleep": GAUGE,
        "defrag-startup-minimum": GAUGE,
        "flush-max-ms": GAUGE,
        "fsync-max-sec": GAUGE,
        "max-write-cache": GAUGE,
        "min-avail-pct": GAUGE,
        "post-write-queue": GAUGE,
        "data-in-memory": GAUGE,
        "dev": GAUGE,
        "filesize": GAUGE,
        "writethreads": GAUGE,
        "writecache": GAUGE,
        "obj-size-hist-max": GAUGE,
    }

    HOLDOFF_METRICS = {

        "objects": GAUGE,
        "sub-objects": GAUGE,
        "master-objects": GAUGE,
        "master-sub-objects": GAUGE,
        "prole-objects": GAUGE,
        "prole-sub-objects": GAUGE,
        "expired-objects": GAUGE,
        "evicted-objects": GAUGE,
        "set-deleted-objects": GAUGE,
        "nsup-cycle-duration": GAUGE,
        "nsup-cycle-sleep-pct": GAUGE,
        "used-bytes-memory": GAUGE,
        "data-used-bytes-memory": GAUGE,
        "index-used-bytes-memory": GAUGE,
        "sindex-used-bytes-memory": GAUGE,
        "free-pct-memory": GAUGE,
        "max-void-time": GAUGE,
        "non-expirable-objects": GAUGE,
        "current-time": GAUGE,
        "stop-writes": GAUGE,
        "hwm-breached": GAUGE,
        "available-bin-names": GAUGE,
        "migrate-tx-partitions-imbalance": GAUGE,
        "migrate-tx-instance-count": GAUGE,
        "migrate-rx-instance-count": GAUGE,
        "migrate-tx-partitions-active": GAUGE,
        "migrate-rx-partitions-active": GAUGE,
        "migrate-tx-partitions-initial": GAUGE,
        "migrate-tx-partitions-remaining": GAUGE,
        "migrate-rx-partitions-initial": GAUGE,
        "migrate-rx-partitions-remaining": GAUGE,
        "migrate-records-skipped": GAUGE,
        "migrate-records-transmitted": GAUGE,
        "migrate-record-retransmits": GAUGE,
        "migrate-record-receives": GAUGE,
        "used-bytes-disk": GAUGE,
        "free-pct-disk": GAUGE,
        "available_pct": GAUGE,
        "cache-read-pct": GAUGE,
        "memory-size": GAUGE,
        "high-water-disk-pct": GAUGE,
        "high-water-memory-pct": GAUGE,
        "evict-tenths-pct": GAUGE,
        "evict-hist-buckets": GAUGE,
        "stop-writes-pct": GAUGE,
        "cold-start-evict-ttl": GAUGE,
        "repl-factor": GAUGE,
        "default-ttl": GAUGE,
        "max-ttl": GAUGE,
        "conflict-resolution-policy": GAUGE,
        "single-bin": GAUGE,
        "ldt-enabled": GAUGE,
        "ldt-page-size": GAUGE,
        "enable-xdr": GAUGE,
        "sets-enable-xdr": GAUGE,
        "ns-forward-xdr-writes": GAUGE,
        "allow-nonxdr-writes": GAUGE,
        "allow-xdr-writes": GAUGE,
        "disallow-null-setname": GAUGE,
        "total-bytes-memory": GAUGE,
        "read-consistency-level-override": GAUGE,
        "write-commit-level-override": GAUGE,
        "migrate-order": GAUGE,
        "migrate-sleep": GAUGE,
        "total-bytes-disk": GAUGE,
        "defrag-lwm-pct": GAUGE,
        "defrag-queue-min": GAUGE,
        "defrag-sleep": GAUGE,
        "defrag-startup-minimum": GAUGE,
        "flush-max-ms": GAUGE,
        "fsync-max-sec": GAUGE,
        "max-write-cache": GAUGE,
        "min-avail-pct": GAUGE,
        "post-write-queue": GAUGE,
        "data-in-memory": GAUGE,
        "dev": GAUGE,
        "filesize": GAUGE,
        "writethreads": GAUGE,
        "writecache": GAUGE,
        "obj-size-hist-max": GAUGE,
    }

    SEGMENT_METRICS = {
        "objects": GAUGE,
        "sub-objects": GAUGE,
        "master-objects": GAUGE,
        "master-sub-objects": GAUGE,
        "prole-objects": GAUGE,
        "prole-sub-objects": GAUGE,
        "expired-objects": GAUGE,
        "evicted-objects": GAUGE,
        "set-deleted-objects": GAUGE,
        "nsup-cycle-duration": GAUGE,
        "nsup-cycle-sleep-pct": GAUGE,
        "used-bytes-memory": GAUGE,
        "data-used-bytes-memory": GAUGE,
        "index-used-bytes-memory": GAUGE,
        "sindex-used-bytes-memory": GAUGE,
        "free-pct-memory": GAUGE,
        "max-void-time": GAUGE,
        "non-expirable-objects": GAUGE,
        "current-time": GAUGE,
        "stop-writes": GAUGE,
        "hwm-breached": GAUGE,
        "available-bin-names": GAUGE,
        "migrate-tx-partitions-imbalance": GAUGE,
        "migrate-tx-instance-count": GAUGE,
        "migrate-rx-instance-count": GAUGE,
        "migrate-tx-partitions-active": GAUGE,
        "migrate-rx-partitions-active": GAUGE,
        "migrate-tx-partitions-initial": GAUGE,
        "migrate-tx-partitions-remaining": GAUGE,
        "migrate-rx-partitions-initial": GAUGE,
        "migrate-rx-partitions-remaining": GAUGE,
        "migrate-records-skipped": GAUGE,
        "migrate-records-transmitted": GAUGE,
        "migrate-record-retransmits": GAUGE,
        "migrate-record-receives": GAUGE,
        "used-bytes-disk": GAUGE,
        "free-pct-disk": GAUGE,
        "available_pct": GAUGE,
        "cache-read-pct": GAUGE,
        "memory-size": GAUGE,
        "high-water-disk-pct": GAUGE,
        "high-water-memory-pct": GAUGE,
        "evict-tenths-pct": GAUGE,
        "evict-hist-buckets": GAUGE,
        "stop-writes-pct": GAUGE,
        "cold-start-evict-ttl": GAUGE,
        "repl-factor": GAUGE,
        "default-ttl": GAUGE,
        "max-ttl": GAUGE,
        "conflict-resolution-policy": GAUGE,
        "single-bin": GAUGE,
        "ldt-enabled": GAUGE,
        "ldt-page-size": GAUGE,
        "enable-xdr": GAUGE,
        "sets-enable-xdr": GAUGE,
        "ns-forward-xdr-writes": GAUGE,
        "allow-nonxdr-writes": GAUGE,
        "allow-xdr-writes": GAUGE,
        "disallow-null-setname": GAUGE,
        "total-bytes-memory": GAUGE,
        "read-consistency-level-override": GAUGE,
        "write-commit-level-override": GAUGE,
        "migrate-order": GAUGE,
        "migrate-sleep": GAUGE,
        "total-bytes-disk": GAUGE,
        "defrag-lwm-pct": GAUGE,
        "defrag-queue-min": GAUGE,
        "defrag-sleep": GAUGE,
        "defrag-startup-minimum": GAUGE,
        "flush-max-ms": GAUGE,
        "fsync-max-sec": GAUGE,
        "max-write-cache": GAUGE,
        "min-avail-pct": GAUGE,
        "post-write-queue": GAUGE,
        "data-in-memory": GAUGE,
        "dev": GAUGE,
        "filesize": GAUGE,
        "writethreads": GAUGE,
        "writecache": GAUGE,
        "obj-size-hist-max": GAUGE,
    }

    SESSION_METRICS = {
        "objects": GAUGE,
        "sub-objects": GAUGE,
        "master-objects": GAUGE,
        "master-sub-objects": GAUGE,
        "prole-objects": GAUGE,
        "prole-sub-objects": GAUGE,
        "expired-objects": GAUGE,
        "evicted-objects": GAUGE,
        "set-deleted-objects": GAUGE,
        "nsup-cycle-duration": GAUGE,
        "nsup-cycle-sleep-pct": GAUGE,
        "used-bytes-memory": GAUGE,
        "data-used-bytes-memory": GAUGE,
        "index-used-bytes-memory": GAUGE,
        "sindex-used-bytes-memory": GAUGE,
        "free-pct-memory": GAUGE,
        "max-void-time": GAUGE,
        "non-expirable-objects": GAUGE,
        "current-time": GAUGE,
        "stop-writes": GAUGE,
        "hwm-breached": GAUGE,
        "available-bin-names": GAUGE,
        "migrate-tx-partitions-imbalance": GAUGE,
        "migrate-tx-instance-count": GAUGE,
        "migrate-rx-instance-count": GAUGE,
        "migrate-tx-partitions-active": GAUGE,
        "migrate-rx-partitions-active": GAUGE,
        "migrate-tx-partitions-initial": GAUGE,
        "migrate-tx-partitions-remaining": GAUGE,
        "migrate-rx-partitions-initial": GAUGE,
        "migrate-rx-partitions-remaining": GAUGE,
        "migrate-records-skipped": GAUGE,
        "migrate-records-transmitted": GAUGE,
        "migrate-record-retransmits": GAUGE,
        "migrate-record-receives": GAUGE,
        "used-bytes-disk": GAUGE,
        "free-pct-disk": GAUGE,
        "available_pct": GAUGE,
        "cache-read-pct": GAUGE,
        "memory-size": GAUGE,
        "high-water-disk-pct": GAUGE,
        "high-water-memory-pct": GAUGE,
        "evict-tenths-pct": GAUGE,
        "evict-hist-buckets": GAUGE,
        "stop-writes-pct": GAUGE,
        "cold-start-evict-ttl": GAUGE,
        "repl-factor": GAUGE,
        "default-ttl": GAUGE,
        "max-ttl": GAUGE,
        "conflict-resolution-policy": GAUGE,
        "single-bin": GAUGE,
        "ldt-enabled": GAUGE,
        "ldt-page-size": GAUGE,
        "enable-xdr": GAUGE,
        "sets-enable-xdr": GAUGE,
        "ns-forward-xdr-writes": GAUGE,
        "allow-nonxdr-writes": GAUGE,
        "allow-xdr-writes": GAUGE,
        "disallow-null-setname": GAUGE,
        "total-bytes-memory": GAUGE,
        "read-consistency-level-override": GAUGE,
        "write-commit-level-override": GAUGE,
        "migrate-order": GAUGE,
        "migrate-sleep": GAUGE,
        "total-bytes-disk": GAUGE,
        "defrag-lwm-pct": GAUGE,
        "defrag-queue-min": GAUGE,
        "defrag-sleep": GAUGE,
        "defrag-startup-minimum": GAUGE,
        "flush-max-ms": GAUGE,
        "fsync-max-sec": GAUGE,
        "max-write-cache": GAUGE,
        "min-avail-pct": GAUGE,
        "post-write-queue": GAUGE,
        "data-in-memory": GAUGE,
        "dev": GAUGE,
        "filesize": GAUGE,
        "writethreads": GAUGE,
        "writecache": GAUGE,
        "obj-size-hist-max": GAUGE,
    }

    """
    Metrics collected by default.
    """
    DEFAULT_METRICS = {
        'service': SERVICE_METRICS,
        'session': SESSION_METRICS,
        'frequencycap': FREQUENCYCAP_METRICS

    }
    ADDITIONAL_METRICS = {
        'holdoff': HOLDOFF_METRICS,
        'segment': SEGMENT_METRICS,
    }

    METRIC_COMMANDS_INFO = {
        'service': 'statistics',
        'session': 'namespace/session',
        'frequencycap': 'namespace/frequencycap',
        'holdoff':'namespace/holdoff',
        'segment':'namespace/segment'
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Members' last replica set states
        self._last_state_by_server = {}

        # List of metrics to collect per instance
        self.metrics_to_collect_by_instance = {}

    def _build_metric_list_to_collect(self, additional_metrics):
        """
        Build the metric list to collect based on the instance preferences.
        """
        metrics_to_collect = {}

        # Create Metrics Listx
        for default_metric_key in self.DEFAULT_METRICS.iterkeys():
            default_metrics = self.DEFAULT_METRICS[default_metric_key]
            for metric in default_metrics.iterkeys():
                metrics_to_collect["%s.%s" % (default_metric_key, metric)] = default_metrics[metric]

        for option in additional_metrics:
            additional_metrics = self.ADDITIONAL_METRICS.get(option)
            if not additional_metrics:
                if option in self.DEFAULT_METRICS:
                    self.log.warning(
                        u"`%s` option is deprecated."
                        u" The corresponding metrics are collected by default.", option
                    )
                else:
                    self.log.warning(
                        u"Failed to extend the list of metrics to collect:"
                        u" unrecognized `%s` option", option
                    )
                continue

            self.log.debug(
                u"Adding `%s` corresponding metrics to the list"
                u" of metrics to collect.", option
            )
            for metric in additional_metrics.iterkeys():
                metrics_to_collect["%s.%s" % (option, metric)] = additional_metrics[metric]

        return metrics_to_collect

    def _get_metrics_to_collect(self, instance_key, additional_metrics):
        """
        Return and cache the list of metrics to collect.
        """
        if instance_key not in self.metrics_to_collect_by_instance:
            self.metrics_to_collect_by_instance[instance_key] = \
                self._build_metric_list_to_collect(additional_metrics)
        return self.metrics_to_collect_by_instance[instance_key]

    def _resolve_metric(self, original_metric_name, metrics_to_collect, prefix=""):
        """
        Return the submit method and the metric name to use.
        The metric name is defined as follow:
        * If available, the normalized metric name alias
        * (Or) the normalized original metric name
        """

        submit_method = metrics_to_collect[original_metric_name][0] \
            if isinstance(metrics_to_collect[original_metric_name], tuple) \
            else metrics_to_collect[original_metric_name]

        metric_name = metrics_to_collect[original_metric_name][1] \
            if isinstance(metrics_to_collect[original_metric_name], tuple) \
            else original_metric_name

        return submit_method, self._normalize(metric_name, submit_method, prefix)

    def _normalize(self, metric_name, submit_method, prefix):
        """
        Replace case-sensitive metric name characters, normalize the metric name,
        prefix and suffix according to its type.
        """
        metric_prefix = "aerospike." if not prefix else "aerospike.{0}.".format(prefix)
        metric_suffix = "ps" if submit_method == RATE else ""

        # Normalize, and wrap
        return u"{metric_prefix}{normalized_metric_name}{metric_suffix}".format(
            normalized_metric_name=self.normalize(metric_name.lower()),
            metric_prefix=metric_prefix, metric_suffix=metric_suffix
        )

    def fetch_metrics(self, hostname, command, namespace):
        """
        Added Parse output to parse metrics And create dictionary
        {
            'hostname':
            {
                'component.metric_name' : 'metric_value'
            }
        }
        :param output:
        :param hostname:
        :return:
        """
        metric_data = {}
        node_info = {}
        output = check_output("sudo /opt/aerospike/bin/asinfo -h %s -v '%s'" % (hostname, command), shell=True)

        metric_list = output.split(";")
        for metric in metric_list:
            if "=" in metric:
                metric_name, metric_value = metric.split("=")
                metric_key = '%s.%s' % (namespace, metric_name)
                metric_data[metric_key] = metric_value
        return metric_data


    def check(self, instance):
        """
        Check and Send Metrics
        """

        if 'host' not in instance:
            raise Exception("Missing 'host' in aerospike config")

        host = str(instance['host']).strip()
        # Added this to deal with localhost configuration.
        if host == 'localhost' or host == '127.0.0.1':
            # get actual host name if its localhost.
            host = check_output('sudo hostname', shell=True)
            host = host.strip()

        additional_metrics = instance.get('additional_metrics', [])

        tags = instance.get('tags', [])
        tags.append('host:%s' % host)

        metrics_to_collect = self._get_metrics_to_collect(
            host,
            additional_metrics
        )
        # de-dupe tags to avoid a memory leak
        tags = list(set(tags))
        metrics_stats = {}
        metrics_data = {}
        try:
            for namespace, command in self.METRIC_COMMANDS_INFO.iteritems():
                metrics_data.update(self.fetch_metrics(host, command, namespace))
            metrics_stats[host] = metrics_data
        except Exception:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=tags)
            raise

        for metric_name in metrics_to_collect:
            if metrics_stats:
                if metric_name in metrics_stats[host]:
                    try:
                        if value.is_digit():
                            value = long(metrics_stats[host][metric_name])
                        else:
                            value = metrics_stats[host][metric_name]
                    except:
                        value = metrics_stats[host][metric_name]

                    # Submit the metric
                    submit_method, metric_name_alias = self._resolve_metric(metric_name, metrics_to_collect, "")
                    submit_method(self, metric_name_alias, value, tags=tags)
