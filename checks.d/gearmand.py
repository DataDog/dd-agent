# (C) Datadog, Inc. 2013-2016
# (C) Patrick Galbraith <patg@patg.net> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# 3rd party
import gearman

# project
from checks import AgentCheck


MAX_NUM_TASKS = 200

class Gearman(AgentCheck):
    SERVICE_CHECK_NAME = 'gearman.can_connect'

    def get_library_versions(self):
        return {"gearman": gearman.__version__}

    def _get_client(self,host,port):
        self.log.debug("Connecting to gearman at address %s:%s" % (host, port))
        return gearman.GearmanAdminClient(["%s:%s" %
            (host, port)])

    def _get_aggregate_metrics(self, tasks, tags):
        running = 0
        queued = 0
        workers = 0

        for stat in tasks:
            running += stat['running']
            queued += stat['queued']
            workers += stat['workers']

        unique_tasks = len(tasks)

        self.gauge("gearman.unique_tasks", unique_tasks, tags=tags)
        self.gauge("gearman.running", running, tags=tags)
        self.gauge("gearman.queued", queued, tags=tags)
        self.gauge("gearman.workers", workers, tags=tags)

        self.log.debug("running %d, queued %d, unique tasks %d, workers: %d"
        % (running, queued, unique_tasks, workers))

    def _get_per_task_metrics(self, tasks, task_filter, tags):
        if len(task_filter) > MAX_NUM_TASKS:
            self.warning(
                "The maximum number of tasks you can specify is {}.".format(MAX_NUM_TASKS))

        if not len(task_filter) == 0:
            tasks = [t for t in tasks if t['task'] in task_filter]

        if len(tasks) > MAX_NUM_TASKS:
            # Display a warning in the info page
            self.warning(
                "Too many tasks to fetch. You must choose the tasks you are interested in by editing the gearmand.yaml configuration file or get in touch with Datadog Support")

        for stat in tasks[:MAX_NUM_TASKS]:
            running = stat['running']
            queued = stat['queued']
            workers = stat['workers']

            task_tags = tags[:]
            task_tags.append("task:{}".format(stat['task']))
            self.gauge("gearman.running_by_task", running, tags=task_tags)
            self.gauge("gearman.queued_by_task", queued, tags=task_tags)
            self.gauge("gearman.workers_by_task", workers, tags=task_tags)

    def _get_conf(self, instance):
        host = instance.get('server', None)
        port = instance.get('port', None)
        tasks = instance.get('tasks', [])

        if host is None:
            self.warning("Host not set, assuming 127.0.0.1")
            host = "127.0.0.1"

        if port is None:
            self.warning("Port is not set, assuming 4730")
            port = 4730

        tags = instance.get('tags', [])

        return host, port, tasks, tags

    def check(self, instance):
        self.log.debug("Gearman check start")

        host, port, task_filter, tags = self._get_conf(instance)
        service_check_tags = ["server:{0}".format(host),
            "port:{0}".format(port)]

        client = self._get_client(host, port)
        self.log.debug("Connected to gearman")

        tags += service_check_tags

        try:
            tasks = client.get_status()
            self._get_aggregate_metrics(tasks, tags)
            self._get_per_task_metrics(tasks, task_filter, tags)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                message="Connection to %s:%s succeeded." % (host, port),
                tags=service_check_tags)
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                message=str(e), tags=service_check_tags)
            raise
