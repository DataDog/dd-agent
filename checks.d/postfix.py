import os

from checks import AgentCheck

class PostfixCheck(AgentCheck):
    """This check provides metrics on the number of messages in a given postfix queue

    WARNING: the user that dd-agent runs as must have sudo access for the 'find' command
             sudo access is not required when running dd-agent as root (not recommended)

    example /etc/sudoers entry:
             dd-agent ALL=(ALL) NOPASSWD:/usr/bin/find

    YAML config options:
        "directories" - the root of your postfix queue directories (ex: /var/spool/postfix, etc..)
        "queues" - the postfix mail queues you would like to get message count totals for
    """
    def check(self, instance):
        config = self._get_config(instance)

        directories = config['directories']
        queues = config['queues']

        self._get_queue_count(directories, queues)

    def _get_config(self, instance):
        directories = instance.get('directories', None)
        queues = instance.get('queues', None)
        if not queues or not directories:
            raise Exception('missing required yaml config entry')

        instance_config = {
            'directories': directories,
            'queues': queues
        }

        return instance_config

    def _get_queue_count(self, directories, queues):
        for directory in directories:
            for queue in queues:
                queue_path = os.path.join(directory, queue)
                if not os.path.exists(queue_path):
                    raise Exception('%s does not exist' % queue_path)

                count = 0
                if os.geteuid() == 0:
                    # dd-agent is running as root (not recommended)
                    count = sum(len(files) for root, dirs, files in os.walk(queue_path))
                else:
                    # can dd-agent user run sudo?
                    test_sudo = os.system('setsid sudo -l < /dev/null')
                    if test_sudo == 0:
                        count = os.popen('sudo find %s -type f | wc -l' % queue_path)
                        count = count.readlines()[0].strip()
                    else:
                        self.log.warning('the dd-agent user does not have sudo access')

                # emit individually tagged metric
                instance = os.path.basename(directory)
                self.gauge('postfix.queue.size', count, tags=['queue:%s' % queue, 'instance:%s' % instance])

                # these can be retrieved in a single graph statement
                # example: sum:postfix.queue.size{role:mta} by {queue}

