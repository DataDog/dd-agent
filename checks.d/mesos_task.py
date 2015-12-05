"""Mesos Task check

Collects metrics from mesos slave node about cpu and memory usage for
running tasks.
"""

from collections import defaultdict
from functools import partial

# 3rd party
import requests

# project
from checks import AgentCheck, CheckException


class MesosTask(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.cluster_name = None
        self.mesos_instances = defaultdict(partial(defaultdict, dict))

    def _get_json(self, url, timeout):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
        except Exception:
            raise CheckException('Error communicating with mesos-slave. '
                                 'Please check your configuration')

        return r.json()

    def _get_statistics(self, url, timeout):
        return self._get_json(url + '/monitor/statistics', timeout)

    def _get_frameworks(self, url, timeout):
        state = self._get_json(url + '/state', timeout)

        id_to_name = {}
        for framework in state['frameworks']:
            id_to_name[framework['id']] = framework['name']

        return id_to_name

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Mesos instance missing "url" value.')

        url = instance['url']
        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        mesos_instance = self.mesos_instances[url]
        instance_metrics = mesos_instance['metrics']
        instance_frameworks = mesos_instance['frameworks']

        new_metrics = {}
        new_frameworks = {}

        new_mesos_statistics = self._get_statistics(url, timeout)

        for task in new_mesos_statistics:
            executor = task['executor_id']
            metrics = task['statistics']

            new_metrics[executor] = metrics

            # first time we've seen this.
            if executor not in instance_metrics:
                continue

            framework_id = task['framework_id']
            if framework_id not in instance_frameworks:
                instance_frameworks = self._get_frameworks(url, timeout)
            framework_name = instance_frameworks.get(framework_id, 'unknown')

            task_name = executor

            if framework_name == 'marathon':
                task_name = executor[:executor.rfind('.')]
            elif framework_name.startswith('chronos'):
                # strip version
                framework_name = 'chronos'
                task_name = executor.split[":"][3]

            tags = list(instance_tags)
            tags.append('task_name:' + task_name)
            tags.append('framework_name:' + framework_name)

            self.gauge('mesos.slave.task.mem_limit',
                       metrics['mem_limit_bytes'],
                       tags=tags)
            self.gauge('mesos.slave.task.cpus_limit',
                       metrics['cpus_limit'],
                       tags=tags)

            self.histogram('mesos.slave.task.mem_used',
                           metrics['mem_rss_bytes'],
                           tags=tags)

            last_stats = instance_metrics[executor]
            delta = metrics['timestamp'] - last_stats['timestamp']

            user_cpus = (metrics['cpus_user_time_secs'] -
                         last_stats['cpus_user_time_secs']) / delta
            system_cpus = (metrics['cpus_system_time_secs'] -
                           last_stats['cpus_system_time_secs']) / delta

            cpus_used = user_cpus + system_cpus

            self.histogram('mesos.slave.task.cpus_used', cpus_used, tags=tags)

        mesos_instance['metrics'] = new_metrics
        mesos_instance['frameworks'] = new_frameworks


if __name__ == "__main__":
    check, instances = MesosTask.from_yaml('mesos_task.yaml')
    for instance in instances:
        print "\nRunning the check against url: %s" % (instance['url'])
        check.check(instance)
        check.check(instance)
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())
