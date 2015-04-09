"""Mesos Master check

Collects metrics from mesos master node, only the leader is sending metrics.
"""
# stdlib
from hashlib import md5
import time

# project
from checks import AgentCheck

# 3rd party
import requests


class MesosMaster(AgentCheck):
    GAUGE = AgentCheck.gauge
    RATE = AgentCheck.rate
    SERVICE_CHECK_NAME = "mesos_master.can_connect"
    SERVICE_CHECK_NEEDED = True


    FRAMEWORK_METRICS = {
        'cpus'                                              : ('mesos.framework.cpu', GAUGE),
        'mem'                                               : ('mesos.framework.mem', GAUGE),
        'disk'                                              : ('mesos.framework.disk', GAUGE),
    }

    ROLE_RESOURCES_METRICS = {
        'cpus'                                              : ('mesos.role.cpu', GAUGE),
        'mem'                                               : ('mesos.role.mem', GAUGE),
        'disk'                                              : ('mesos.role.disk', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    CLUSTER_TASKS_METRICS = {
        'staged_tasks'                                      : ('mesos.cluster.staged_tasks', GAUGE),
        'started_tasks'                                     : ('mesos.cluster.started_tasks', GAUGE),
        'finished_tasks'                                    : ('mesos.cluster.finished_tasks', GAUGE),
        'killed_tasks'                                      : ('mesos.cluster.killed_tasks', GAUGE),
        'failed_tasks'                                      : ('mesos.cluster.failed_tasks', GAUGE),
        'lost_tasks'                                        : ('mesos.cluster.lost_tasks', GAUGE),
        'active_tasks_gauge'                                : ('mesos.cluster.active_tasks_gauge', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    CLUSTER_SLAVES_METRICS = {
        'master/slave_registrations'                        : ('mesos.cluster.slave_registrations', GAUGE),
        'master/slave_removals'                             : ('mesos.cluster.slave_removals', GAUGE),
        'master/slave_reregistrations'                      : ('mesos.cluster.slave_reregistrations', GAUGE),
        'master/slave_shutdowns_canceled'                   : ('mesos.cluster.slave_shutdowns_canceled', GAUGE),
        'master/slave_shutdowns_scheduled'                  : ('mesos.cluster.slave_shutdowns_scheduled', GAUGE),
        'master/slaves_active'                              : ('mesos.cluster.slaves_active', GAUGE),
        'master/slaves_connected'                           : ('mesos.cluster.slaves_connected', GAUGE),
        'master/slaves_disconnected'                        : ('mesos.cluster.slaves_disconnected', GAUGE),
        'master/slaves_inactive'                            : ('mesos.cluster.slaves_inactive', GAUGE),
        'master/recovery_slave_removals'                    : ('mesos.cluster.recovery_slave_removals', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    CLUSTER_RESOURCES_METRICS = {
        'master/cpus_percent'                               : ('mesos.cluster.cpus_percent', GAUGE),
        'master/cpus_total'                                 : ('mesos.cluster.cpus_total', GAUGE),
        'master/cpus_used'                                  : ('mesos.cluster.cpus_used', GAUGE),
        'master/disk_percent'                               : ('mesos.cluster.disk_percent', GAUGE),
        'master/disk_total'                                 : ('mesos.cluster.disk_total', GAUGE),
        'master/disk_used'                                  : ('mesos.cluster.disk_used', GAUGE),
        'master/mem_percent'                                : ('mesos.cluster.mem_percent', GAUGE),
        'master/mem_total'                                  : ('mesos.cluster.mem_total', GAUGE),
        'master/mem_used'                                   : ('mesos.cluster.mem_used', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    CLUSTER_REGISTRAR_METRICS = {
        'registrar/queued_operations'                       : ('mesos.registrar.queued_operations', GAUGE),
        'registrar/registry_size_bytes'                     : ('mesos.registrar.registry_size_bytes', GAUGE),
        'registrar/state_fetch_ms'                          : ('mesos.registrar.state_fetch_ms', GAUGE),
        'registrar/state_store_ms'                          : ('mesos.registrar.state_store_ms', GAUGE),
        'registrar/state_store_ms/count'                    : ('mesos.registrar.state_store_ms.count', GAUGE),
        'registrar/state_store_ms/max'                      : ('mesos.registrar.state_store_ms.max', GAUGE),
        'registrar/state_store_ms/min'                      : ('mesos.registrar.state_store_ms.min', GAUGE),
        'registrar/state_store_ms/p50'                      : ('mesos.registrar.state_store_ms.p50', GAUGE),
        'registrar/state_store_ms/p90'                      : ('mesos.registrar.state_store_ms.p90', GAUGE),
        'registrar/state_store_ms/p95'                      : ('mesos.registrar.state_store_ms.p95', GAUGE),
        'registrar/state_store_ms/p99'                      : ('mesos.registrar.state_store_ms.p99', GAUGE),
        'registrar/state_store_ms/p999'                     : ('mesos.registrar.state_store_ms.p999', GAUGE),
        'registrar/state_store_ms/p9999'                    : ('mesos.registrar.state_store_ms.p9999', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    CLUSTER_FRAMEWORK_METRICS = {
        'master/frameworks_active'                          : ('mesos.cluster.frameworks_active', GAUGE),
        'master/frameworks_connected'                       : ('mesos.cluster.frameworks_connected', GAUGE),
        'master/frameworks_disconnected'                    : ('mesos.cluster.frameworks_disconnected', GAUGE),
        'master/frameworks_inactive'                        : ('mesos.cluster.frameworks_inactive', GAUGE),
    }

    # These metrics are aggregated on all nodes in the cluster
    SYSTEM_METRICS = {
        'system/cpus_total'                                 : ('mesos.stats.system.cpus_total', GAUGE),
        'system/load_15min'                                 : ('mesos.stats.system.load_15min', RATE),
        'system/load_1min'                                  : ('mesos.stats.system.load_1min', RATE),
        'system/load_5min'                                  : ('mesos.stats.system.load_5min', RATE),
        'system/mem_free_bytes'                             : ('mesos.stats.system.mem_free_bytes', GAUGE),
        'system/mem_total_bytes'                            : ('mesos.stats.system.mem_total_bytes', GAUGE),
        'master/elected'                                    : ('mesos.stats.elected', GAUGE),
        'master/uptime_secs'                                : ('mesos.stats.uptime_secs', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    STATS_METRICS = {
        'active_schedulers'                                 : ('mesos.cluster.active_schedulers', GAUGE),
        'total_schedulers'                                  : ('mesos.cluster.total_schedulers', GAUGE),
        'outstanding_offers'                                : ('mesos.cluster.outstanding_offers', GAUGE),
        'master/dropped_messages'                           : ('mesos.cluster.dropped_messages', GAUGE),
        'master/outstanding_offers'                         : ('mesos.cluster.outstanding_offers', GAUGE),
        'master/event_queue_dispatches'                     : ('mesos.cluster.event_queue_dispatches', GAUGE),
        'master/event_queue_http_requests'                  : ('mesos.cluster.event_queue_http_requests', GAUGE),
        'master/event_queue_messages'                       : ('mesos.cluster.event_queue_messages', GAUGE),
        'master/invalid_framework_to_executor_messages'     : ('mesos.cluster.invalid_framework_to_executor_messages', GAUGE),
        'master/invalid_status_update_acknowledgements'     : ('mesos.cluster.invalid_status_update_acknowledgements', GAUGE),
        'master/invalid_status_updates'                     : ('mesos.cluster.invalid_status_updates', GAUGE),
        'master/valid_framework_to_executor_messages'       : ('mesos.cluster.valid_framework_to_executor_messages', GAUGE),
        'master/valid_status_update_acknowledgements'       : ('mesos.cluster.valid_status_update_acknowledgements', GAUGE),
        'master/valid_status_updates'                       : ('mesos.cluster.valid_status_updates', GAUGE),
    }

    def _timeout_event(self, url, timeout, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'http_check',
            'msg_title': 'URL timeout',
            'msg_text': '%s timed out after %s seconds.' % (url, timeout),
            'aggregation_key': aggregation_key
        })

    def _status_code_event(self, url, r, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'http_check',
            'msg_title': 'Invalid reponse code for %s' % url,
            'msg_text': '%s returned a status of %s' % (url, r.status_code),
            'aggregation_key': aggregation_key
        })

    def _get_json(self, url, timeout):
        # Use a hash of the URL as an aggregation key
        aggregation_key = md5(url).hexdigest()
        tags = ["url:%s" % url]
        msg = None
        status = None
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code != 200:
                self._status_code_event(url, r, aggregation_key)
                status = AgentCheck.CRITICAL
                msg = "Got %s when hitting %s" % (r.status_code, url)
            else:
                status = AgentCheck.OK
                msg = "Mesos master instance detected at %s " % url
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            self._timeout_event(url, timeout, aggregation_key)
            msg = "%s seconds timeout when hitting %s" % (timeout, url)
            status = AgentCheck.CRITICAL
        except Exception as e:
            msg = e.message
            status = AgentCheck.CRITICAL
        finally:
            if self.SERVICE_CHECK_NEEDED:
                self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags,
                                   message=msg)
                self.SERVICE_CHECK_NEEDED = False
            if status is AgentCheck.CRITICAL:
                self.warning(msg)
                return None

        return r.json()

    def _get_master_state(self, url, timeout):
        return self._get_json(url + '/state.json', timeout)

    def _get_master_stats(self, url, timeout):
        return self._get_json(url + '/stats.json', timeout)

    def _get_master_roles(self, url, timeout):
        return self._get_json(url + '/roles.json', timeout)

    def _check_leadership(self, url, timeout):
        json = self._get_master_state(url, timeout)

        if json is not None and json['leader'] == json['pid']:
            self.leader = True
        else:
            self.leader = False
        return json

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Mesos instance missing "url" value.')

        url = instance['url']
        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        json = self._check_leadership(url, timeout)
        if json:
            tags = ['mesos_cluster:' + json['cluster'], 'mesos_pid:' + json['pid'], 'mesos_id:' + json['id'], 'mesos_node:master'] + instance_tags

            if self.leader:
                self.GAUGE('mesos.cluster.total_frameworks', len(json['frameworks']), tags=tags)

                for framework in json['frameworks']:
                    framework_tags = ['framework:' + framework['id'], 'framework_name:' + framework['name']] + tags
                    self.GAUGE('mesos.framework.total_tasks', len(framework['tasks']), tags=framework_tags)
                    resources = framework['used_resources']
                    [v[1](self, v[0], resources[k], tags=framework_tags) for k, v in self.FRAMEWORK_METRICS.iteritems()]

                json = self._get_master_roles(url, timeout)
                if json is not None:
                    for role in json['roles']:
                        role_tags = ['mesos_role:' + role['name']] + tags
                        self.GAUGE('mesos.role.frameworks', len(role['frameworks']), tags=role_tags)
                        self.GAUGE('mesos.role.weight', role['weight'], tags=role_tags)
                        [v[1](self, v[0], role['resources'][k], tags=role_tags) for k, v in self.ROLE_RESOURCES_METRICS.iteritems()]

            json = self._get_master_stats(url, timeout)
            if json is not None:
                if self.leader:
                    metrics = {}
                    for d in (self.CLUSTER_TASKS_METRICS, self.CLUSTER_SLAVES_METRICS,
                              self.CLUSTER_RESOURCES_METRICS, self.CLUSTER_REGISTRAR_METRICS,
                              self.CLUSTER_FRAMEWORK_METRICS, self.SYSTEM_METRICS, self.STATS_METRICS):
                        metrics.update(d)
                else:
                    metrics = self.SYSTEM_METRICS
                [v[1](self, v[0], json[k], tags=tags) for k, v in metrics.iteritems()]


        self.SERVICE_CHECK_NEEDED = True
