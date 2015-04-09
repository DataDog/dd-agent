from tests.common import AgentCheckTest, get_check_class

from nose.plugins.attrib import attr
from mock import patch
from checks import AgentCheck
import time

state = {
  "version": "0.22.0",
  "started_tasks": 0,
  "start_time": 1428673344.06054,
  "staged_tasks": 1,
  "cluster": "test",
  "resources": {
    "ports": "[31000-32000]",
    "mem": 244,
    "disk": 35164,
    "cpus": 1
  },
  "pid": "slave(1)@127.0.0.1:5051",
  "master_hostname": "localhost",
  "flags": {
    "work_dir": "/tmp/mesos",
    "version": "false",
    "switch_user": "true",
    "strict": "true",
    "resource_monitoring_interval": "1secs",
    "registration_backoff_factor": "1secs",
    "recovery_timeout": "15mins",
    "recover": "reconnect",
    "executor_shutdown_grace_period": "5secs",
    "executor_registration_timeout": "1mins",
    "enforce_container_disk_quota": "false",
    "docker_stop_timeout": "0ns",
    "docker_sandbox_directory": "/mnt/mesos/sandbox",
    "docker_remove_delay": "6hrs",
    "docker": "docker",
    "disk_watch_interval": "1mins",
    "authenticatee": "crammd5",
    "cgroups_enable_cfs": "false",
    "cgroups_hierarchy": "/sys/fs/cgroup",
    "cgroups_limit_swap": "false",
    "cgroups_root": "mesos",
    "container_disk_watch_interval": "15secs",
    "containerizers": "mesos",
    "default_role": "*",
    "frameworks_home": "",
    "gc_delay": "1weeks",
    "gc_disk_headroom": "0.1",
    "hadoop_home": "",
    "help": "false",
    "initialize_driver_logging": "true",
    "isolation": "posix/cpu,posix/mem",
    "launcher_dir": "/usr/libexec/mesos",
    "log_dir": "/var/log/mesos",
    "logbufsecs": "0",
    "logging_level": "INFO",
    "master": "zk://localhost:2181/mesos",
    "perf_duration": "10secs",
    "perf_interval": "1mins",
    "port": "5051",
    "quiet": "false"
  },
  "finished_tasks": 0,
  "failed_tasks": 0,
  "completed_frameworks": [],
  "build_user": "root",
  "build_time": 1427376927,
  "build_date": "2015-03-26 13:35:27",
  "attributes": {},
  "frameworks": [
    {
      "user": "root",
      "checkpoint": 'true',
      "completed_executors": [],
      "executors": [
        {
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
          "completed_tasks": [],
          "container": "f67a5e0b-91f9-474a-94a0-e2c6a3b28ea4",
          "directory": "/tmp/mesos/slaves/20150410-134224-16777343-5050-1778-S0/frameworks/20150403-140128-251789322-5050-6047-0000/executors/hello.dc130e23-df88-11e4-b9ec-080027fc1312/runs/f67a5e0b-91f9-474a-94a0-e2c6a3b28ea4",
          "id": "hello.dc130e23-df88-11e4-b9ec-080027fc1312",
          "name": "Command Executor (Task: hello.dc130e23-df88-11e4-b9ec-080027fc1312) (Command: sh -c 'cd hello && ...')",
          "queued_tasks": [],
          "resources": {
            "ports": "[31915-31915]",
            "mem": 132,
            "disk": 0,
            "cpus": 1.1
          },
          "source": "hello.dc130e23-df88-11e4-b9ec-080027fc1312"
        }
      ],
      "failover_timeout": 604800,
      "hostname": "vagrant-ubuntu-trusty-64",
      "id": "20150403-140128-251789322-5050-6047-0000",
      "name": "marathon",
      "role": "*"
    }
  ],
  "git_sha": "e890e2414903bb69cab730d5204f10b10d2e91bb",
  "git_tag": "0.22.0",
  "hostname": "localhost",
  "id": "20150410-134224-16777343-5050-1778-S0",
  "killed_tasks": 0,
  "log_dir": "/var/log/mesos",
  "lost_tasks": 0
}

stats = {
  "valid_status_updates": 1,
  "uptime": 280965.77977984,
  "total_frameworks": 1,
  "system/mem_total_bytes": 513798144,
  "system/mem_free_bytes": 34271232,
  "system/load_5min": 0.08,
  "system/load_1min": 0.1,
  "system/load_15min": 0.06,
  "system/cpus_total": 1,
  "started_tasks": 0,
  "staged_tasks": 1,
  "slave/valid_status_updates": 1,
  "slave/valid_framework_messages": 0,
  "slave/uptime_secs": 280965.78028288,
  "slave/tasks_starting": 0,
  "slave/tasks_staging": 0,
  "slave/executors_registering": 0,
  "slave/disk_used": 0,
  "slave/disk_total": 35164,
  "slave/disk_percent": 0,
  "slave/cpus_used": 1.1,
  "slave/cpus_total": 1,
  "slave/cpus_percent": 1.1,
  "registered": 1,
  "failed_tasks": 0,
  "finished_tasks": 0,
  "invalid_status_updates": 0,
  "killed_tasks": 0,
  "launched_tasks_gauge": 1,
  "lost_tasks": 0,
  "queued_tasks_gauge": 0,
  "recovery_errors": 0,
  "slave/executors_running": 1,
  "slave/executors_terminated": 0,
  "slave/executors_terminating": 0,
  "slave/frameworks_active": 1,
  "slave/invalid_framework_messages": 0,
  "slave/invalid_status_updates": 0,
  "slave/mem_percent": 0.540983606557377,
  "slave/mem_total": 244,
  "slave/mem_used": 132,
  "slave/recovery_errors": 0,
  "slave/registered": 1,
  "slave/tasks_failed": 0,
  "slave/tasks_finished": 0,
  "slave/tasks_killed": 0,
  "slave/tasks_lost": 0,
  "slave/tasks_running": 1
}

def _mocked_get_state(*args, **kwargs):
    return state
def _mocked_get_stats(*args, **kwargs):
    return stats

@attr(requires='mesos_slave')
class TestMesosSlave(AgentCheckTest):
    CHECK_NAME = 'mesos_slave'

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050',
                    'tasks': ['hello']
                }
            ]
        }

        klass = get_check_class('mesos_slave')
        with patch.object(klass, '_get_state', _mocked_get_state):
            with patch.object(klass, '_get_stats', _mocked_get_stats):
                check = klass('mesos_slave', {}, {})
                self.run_check(config)
                time.sleep(1)
                self.run_check(config)
                metrics = {}
                for d in (check.SLAVE_TASKS_METRICS, check.SYSTEM_METRICS, check.SLAVE_RESOURCE_METRICS,
                          check.SLAVE_EXECUTORS_METRICS, check.STATS_METRICS):
                    metrics.update(d)
                [self.assertMetric(v[0]) for k, v in check.TASK_METRICS.iteritems()]
                [self.assertMetric(v[0]) for k, v in metrics.iteritems()]
                self.assertServiceCheck('hello.ok',
                    count=1, status=AgentCheck.OK
                )
