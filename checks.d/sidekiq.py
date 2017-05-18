import re
from collections import namedtuple

# project
from checks import AgentCheck, CheckException

# 3rd party
import psutil
import redis

Stat = namedtuple("SidekiqStat", "name command key")

class Sidekiq(AgentCheck):
    APP_STATS = [
        Stat('processed', 'get', 'stat:processed'),
        Stat('failed', 'get', 'stat:failed'),
        Stat('scheduled', 'zcard', 'schedule'),
        Stat('retries', 'zcard', 'retry'),
        Stat('dead', 'zcard', 'dead')
    ]

    APP_PREFIX = 'sidekiq.app.'

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.connections = {}

    def _procs_by_tag(self):
        """
        Search for running sidekiq processes and group them by app tag
        (i.e. `pgrep -fa '^sidekiq' | cut -d' ' -f 4`)
        """
        all_sidekiq_procs = [p for p in psutil.process_iter()
                             if p.name() == 'ruby'
                             and p.cmdline()[0].startswith('sidekiq')]

        sidekiq_procs_by_tag = {}

        for sidekiq_proc in all_sidekiq_procs:
            # sidekiq overwrites command line to be e.g.
            #'sidekiq 2.14.0 myapp [2 of 10 busy]'
            # see: http://git.io/57ktWQ
            sk_cmdline = sidekiq_proc.cmdline()[0]
            app_tag = sk_cmdline.split()[2]

            # sometimes there is no tag....
            if re.search(r'^\[\d', app_tag):
                app_tag = '__none__'

            sidekiq_procs_by_tag.setdefault(app_tag, []).append(sidekiq_proc)

        return sidekiq_procs_by_tag

    def _namespaced_key(self, namespace, key):
        if not namespace:
            return key
        else:
            return ":".join([namespace, key])

    def check(self, instance):
        """
        Reports stats as defined in Sidekiq::Stats (in http://git.io/e-QGLw ) as
        well as busy (as returned by sidekiq_web /dashboard/stats endpoint)
        """
        procs_by_tag = self._procs_by_tag()

        tag = instance.get('tag')
        if tag == None and len(procs_by_tag.keys()) == 1:
            tag = procs_by_tag.keys()[0]

        app_tags = []
        if  tag != '__none__':
            app_tags.append('sidekiq_app:%s' % tag)

        worker_procs = procs_by_tag.get(tag, [])
        running_proc = next((p for p in worker_procs if p.is_running()), None)
        if tag and not running_proc:
            self.warning("No running sidekiq workers matching tag '%s'" % tag)
            self.service_check('sidekiq.workers_running',
                               AgentCheck.CRITICAL, tags=app_tags)
        else:
            self.service_check('sidekiq.workers_running',
                               AgentCheck.OK, tags=app_tags)

        redis_url = instance.get('redis_url')
        conn = self.connections.get(redis_url) or redis.from_url(redis_url)
        self.connections[redis_url] = conn

        namespace = instance.get('redis_namespace')

        #per-app stats
        for stat in self.APP_STATS:
            stat_name = self.APP_PREFIX + stat.name
            redis_command = getattr(conn, stat.command)
            key_name = self._namespaced_key(namespace, stat.key)

            self.gauge(stat_name, float(redis_command(key_name)), tags=app_tags)

        #calculate and report number of busy workers
        processes_key = self._namespaced_key(namespace, 'processes')
        processes = conn.smembers(processes_key)
        pipe = conn.pipeline()
        for process in processes:
            pipe.hget(self._namespaced_key(namespace, process), 'busy')
        busy = sum([int(num) for num in pipe.execute()])

        self.gauge(self.APP_PREFIX + 'busy', float(busy), tags=app_tags)

        #individual queue stats and sum thereof
        enqueued = 0
        queues = conn.smembers(self._namespaced_key(namespace, 'queues'))
        for queue in queues:
            key_name = 'queue:%s' % queue
            queue_tags = app_tags + ['sidekiq_' + key_name]

            msgs = conn.llen(self._namespaced_key(namespace, key_name))
            self.gauge('sidekiq.queue.messages', float(msgs), tags=queue_tags)

            enqueued += msgs

        self.gauge(self.APP_PREFIX + 'enqueued', float(enqueued), tags=app_tags)
