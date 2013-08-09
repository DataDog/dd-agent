from os import walk, system, geteuid, popen
from os.path import exists, join
from collections import namedtuple

from checks import AgentCheck

class PostfixQueuesCheck(AgentCheck):
    def check(self, instance):
        config = self._get_config(instance)

        directory = config.directory
        queues = config.queues

        self._get_queue_count(directory, queues)

    def _get_config(self, instance):
        required = ['directory', 'queues']
        for param in required:
            if not instance.get(param):
                raise Exception("PostfixQueuesCheck: (%s) is missing from yaml config" % param)

        directory = instance.get('directory')
        queues = instance.get('queues')

        instance_config = namedtuple('instance_config', [
            'directory',
            'queues']
        )

        return instance_config(directory, queues)

    def _get_queue_count(self, directory, queues):
        for queue in queues:
            queue_path = '/'.join([directory, queue])
            if not exists(queue_path):
                raise Exception("PostfixQueuesCheck: (%s) queue directory does not exist" % queue_path)

            metric_name = '.'.join(['postfix.queues', queue])

            count = 0
            if geteuid() == 0:
                # dd-agent must be running as root user
                count = sum(len(files) for root, dirs, files in walk(queue_path))
            else:
                # only postfix or root user can access postfix queues :(
                # user 'dd-agent' must be in sudoers (w/ ALL & NOPASSWD)
                count = popen("sudo find %s -type f | wc -l" % queue_path)
                count = count.readlines()[0].strip()

            self.gauge(metric_name, count)

