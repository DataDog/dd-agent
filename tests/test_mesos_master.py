from tests.common import AgentCheckTest, get_check_class

from nose.plugins.attrib import attr
from mock import patch
from checks import AgentCheck
import time

state = {
  "version": "0.22.0",
  "unregistered_frameworks": [],
  "started_tasks": 0,
  "start_time": 1428951954.34111,
  "staged_tasks": 0,
  "slaves": [
    {
      "resources": {
        "ports": "[31000-32000]",
        "mem": 244,
        "disk": 35164,
        "cpus": 1
      },
      "reregistered_time": 1428951983.53731,
      "registered_time": 1428951983.53725,
      "pid": "slave(1)@127.0.0.1:5051",
      "id": "20150410-134224-16777343-5050-1778-S0",
      "hostname": "localhost",
      "attributes": {},
      "active": 'true'
    }
  ],
  "pid": "master@127.0.0.1:5050",
  "orphan_tasks": [],
  "lost_tasks": 0,
  "log_dir": "/var/log/mesos",
  "leader": "master@127.0.0.1:5050",
  "killed_tasks": 0,
  "elected_time": 1428951954.3774,
  "deactivated_slaves": 0,
  "completed_frameworks": [],
  "cluster": "datadog-test",
  "build_user": "root",
  "build_time": 1427376927,
  "build_date": "2015-03-26 13:35:27",
  "activated_slaves": 1,
  "failed_tasks": 0,
  "finished_tasks": 0,
  "flags": {
    "zk_session_timeout": "10secs",
    "zk": "zk://localhost:2181/mesos",
    "work_dir": "/var/lib/mesos",
    "webui_dir": "/usr/share/mesos/webui",
    "version": "false",
    "user_sorter": "drf",
    "slave_reregister_timeout": "10mins",
    "root_submissions": "true",
    "registry_strict": "false",
    "registry_store_timeout": "5secs",
    "registry_fetch_timeout": "1mins",
    "registry": "replicated_log",
    "initialize_driver_logging": "true",
    "help": "false",
    "framework_sorter": "drf",
    "cluster": "datadog-test",
    "authenticators": "crammd5",
    "authenticate_slaves": "false",
    "authenticate": "false",
    "allocation_interval": "1secs",
    "log_auto_initialize": "true",
    "log_dir": "/var/log/mesos",
    "logbufsecs": "0",
    "logging_level": "INFO",
    "port": "5050",
    "quiet": "false",
    "quorum": "1",
    "recovery_slave_removal_limit": "100%"
  },
  "frameworks": [
    {
      "webui_url": "http://192.168.33.20:8080",
      "user": "root",
      "offered_resources": {
        "mem": 0,
        "disk": 0,
        "cpus": 0
      },
      "name": "marathon",
      "id": "20150403-140128-251789322-5050-6047-0000",
      "hostname": "vagrant-ubuntu-trusty-64",
      "failover_timeout": 604800,
      "completed_tasks": [],
      "checkpoint": 'true',
      "active": 'true',
      "offers": [],
      "registered_time": 1428951955.38871,
      "reregistered_time": 1428951955.38872,
      "resources": {
        "ports": "[31915-31915]",
        "mem": 100,
        "disk": 0,
        "cpus": 1
      },
      "role": "*",
      "tasks": [
        {
          "statuses": [
            {
              "timestamp": 1428673971.61592,
              "state": "TASK_RUNNING"
            }
          ],
          "executor_id": "",
          "framework_id": "20150403-140128-251789322-5050-6047-0000",
          "id": "hello.dc130e23-df88-11e4-b9ec-080027fc1312",
          "labels": [],
          "name": "hello",
          "resources": {
            "ports": "[31915-31915]",
            "mem": 100,
            "disk": 0,
            "cpus": 1
          },
          "slave_id": "20150410-134224-16777343-5050-1778-S0",
          "state": "TASK_RUNNING"
        }
      ],
      "unregistered_time": 0,
      "used_resources": {
        "ports": "[31915-31915]",
        "mem": 100,
        "disk": 0,
        "cpus": 1
      }
    }
  ],
  "git_sha": "e890e2414903bb69cab730d5204f10b10d2e91bb",
  "git_tag": "0.22.0",
  "hostname": "localhost",
  "id": "20150413-190554-16777343-5050-16324"
}

stats = {
  "valid_status_updates": 0,
  "uptime": 706.524240128,
  "total_schedulers": 1,
  "system/mem_total_bytes": 513798144,
  "system/mem_free_bytes": 13815808,
  "system/load_5min": 0.02,
  "system/load_1min": 0,
  "system/load_15min": 0.07,
  "system/cpus_total": 1,
  "started_tasks": 0,
  "staged_tasks": 0,
  "registrar/state_store_ms/p9999": 9.90120192,
  "registrar/state_store_ms/p999": 9.8956032,
  "registrar/state_store_ms/p99": 9.839616,
  "registrar/state_store_ms/p95": 9.590784,
  "registrar/state_store_ms/p90": 9.279744,
  "registrar/state_store_ms/p50": 6.791424,
  "registrar/state_store_ms/min": 3.681024,
  "registrar/state_store_ms/max": 9.901824,
  "registrar/state_store_ms/count": 2,
  "registrar/state_store_ms": 9.901824,
  "registrar/state_fetch_ms": 3.717888,
  "registrar/registry_size_bytes": 246,
  "registrar/queued_operations": 0,
  "outstanding_offers": 0,
  "mem_used": 100,
  "mem_total": 244,
  "mem_percent": 0.409836065573771,
  "master/valid_status_updates": 0,
  "master/valid_status_update_acknowledgements": 0,
  "master/valid_framework_to_executor_messages": 0,
  "master/uptime_secs": 706.52485632,
  "master/tasks_starting": 0,
  "master/tasks_staging": 0,
  "master/tasks_running": 1,
  "master/tasks_lost": 0,
  "master/tasks_killed": 0,
  "master/tasks_finished": 0,
  "master/tasks_failed": 0,
  "master/tasks_error": 0,
  "master/slaves_inactive": 0,
  "master/slaves_disconnected": 0,
  "master/invalid_framework_to_executor_messages": 0,
  "master/frameworks_inactive": 0,
  "master/frameworks_disconnected": 0,
  "master/frameworks_connected": 1,
  "master/frameworks_active": 1,
  "master/event_queue_messages": 0,
  "master/event_queue_http_requests": 0,
  "master/event_queue_dispatches": 17,
  "master/elected": 1,
  "master/dropped_messages": 1,
  "master/disk_used": 0,
  "master/disk_total": 35164,
  "master/disk_percent": 0,
  "master/cpus_used": 1,
  "master/cpus_total": 1,
  "master/cpus_percent": 1,
  "disk_percent": 0,
  "deactivated_slaves": 0,
  "cpus_used": 1,
  "cpus_total": 1,
  "cpus_percent": 1,
  "active_tasks_gauge": 1,
  "active_schedulers": 1,
  "activated_slaves": 1,
  "disk_total": 35164,
  "disk_used": 0,
  "elected": 1,
  "failed_tasks": 0,
  "finished_tasks": 0,
  "invalid_status_updates": 0,
  "killed_tasks": 0,
  "lost_tasks": 0,
  "master/invalid_status_update_acknowledgements": 0,
  "master/invalid_status_updates": 0,
  "master/mem_percent": 0.409836065573771,
  "master/mem_total": 244,
  "master/mem_used": 100,
  "master/messages_authenticate": 0,
  "master/messages_deactivate_framework": 0,
  "master/messages_decline_offers": 123,
  "master/messages_exited_executor": 0,
  "master/messages_framework_to_executor": 0,
  "master/messages_kill_task": 0,
  "master/messages_launch_tasks": 0,
  "master/messages_reconcile_tasks": 6,
  "master/messages_register_framework": 0,
  "master/messages_register_slave": 0,
  "master/messages_reregister_framework": 1,
  "master/messages_reregister_slave": 2,
  "master/messages_resource_request": 0,
  "master/messages_revive_offers": 0,
  "master/messages_status_update": 0,
  "master/messages_status_update_acknowledgement": 0,
  "master/messages_unregister_framework": 0,
  "master/messages_unregister_slave": 0,
  "master/outstanding_offers": 0,
  "master/recovery_slave_removals": 0,
  "master/slave_registrations": 0,
  "master/slave_removals": 0,
  "master/slave_reregistrations": 1,
  "master/slave_shutdowns_canceled": 0,
  "master/slave_shutdowns_scheduled": 0,
  "master/slaves_active": 1,
  "master/slaves_connected": 1
}

roles = {
  "roles": [
    {
      "weight": 1,
      "resources": {
        "ports": "[31915-31915]",
        "mem": 100,
        "disk": 0,
        "cpus": 1
      },
      "name": "*",
      "frameworks": [
        "20150403-140128-251789322-5050-6047-0000"
      ]
    }
  ]
}

def _mocked_get_master_state(*args, **kwargs):
    return state
def _mocked_get_master_stats(*args, **kwargs):
    return stats
def _mocked_get_master_roles(*args, **kwargs):
    return roles


@attr(requires='mesos_master')
class TestMesosMaster(AgentCheckTest):
    CHECK_NAME = 'mesos_master'

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050'
                }
            ]
        }

        klass = get_check_class('mesos_master')
        with patch.object(klass, '_get_master_state', _mocked_get_master_state):
            with patch.object(klass, '_get_master_stats', _mocked_get_master_stats):
                with patch.object(klass, '_get_master_roles', _mocked_get_master_roles):
                    check = klass('mesos_master', {}, {})
                    self.run_check(config)
                    time.sleep(1)
                    self.run_check(config)
                    metrics = {}
                    for d in (check.CLUSTER_TASKS_METRICS, check.CLUSTER_SLAVES_METRICS,
                              check.CLUSTER_RESOURCES_METRICS, check.CLUSTER_REGISTRAR_METRICS,
                              check.CLUSTER_FRAMEWORK_METRICS, check.SYSTEM_METRICS, check.STATS_METRICS):
                        metrics.update(d)
                    [self.assertMetric(v[0]) for k, v in check.FRAMEWORK_METRICS.iteritems()]
                    [self.assertMetric(v[0]) for k, v in metrics.iteritems()]
                    [self.assertMetric(v[0]) for k, v in check.ROLE_RESOURCES_METRICS.iteritems()]
                    self.assertMetric('mesos.cluster.total_frameworks')
                    self.assertMetric('mesos.framework.total_tasks')
                    self.assertMetric('mesos.role.frameworks')
                    self.assertMetric('mesos.role.weight')
