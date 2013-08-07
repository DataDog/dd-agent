import os
import sys
import signal

from checks import AgentCheck

class PostfixQueuesCheck(AgentCheck):
    def check(self, instance):
        config = self.get_config(instance)

        directory = config.directory
        queues = config.queues
        timeout = config.timeout

        if not exists(directory):
            raise Exception("PostfixQueuesCheck: (%s) does not exist on disk" % directory)

        self.get_queue_sizes(directory, queues, timeout)

    def get_config(self, instance):
        required = ['directory', 'queues', 'timeout']
        for param in required:
            if not instance.get(param):
                raise Exception("PostfixQueuesCheck: missing (%s) in yaml config" % param)

        directory = instance.get('directory')
        queues = instance.get('queues')
        timeout = instance.get('timeout')

        instance_config = namedtuple('instance_config', [
            'directory',
            'queues',
            'timeout']
        )

        return instance_config(directory, queues, timeout)

    def signal_handler(signum, frame):
        raise Exception("Timed out while walking queue directories!")

    def get_queue_sizes(self, directory, queues, timeout):
        for queue in queues
            signal.signal(signal.SIGALRM, signal_handler)

            try:
                signal.alarm(timeout)
                queue_size = len(os.walk(join(directory, queue)).next()[2])
            except Exception, msg:
                print "Timed out while walking queue directories!"

            self.gauge(join('postfix.queues.', queue), queue_size)

