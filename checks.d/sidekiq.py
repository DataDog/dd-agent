# For the sake of one-file packaging of this check, this file plays a kludegy
# dual role as both a python module invoked by the top-level dd-agent and
# a ruby script invoked by the python's _get_json method
#
# When read as a ruby file, these comments are comments, the longstring start
# (""") and extra quote (") are two empty string literals, the __END__ is an
# instruction to the parser to stop looking for ruby and the rest is (unused)
# DATA
#
# When (first) read as python, these comments are comments, the ruby is all a
# docstring and the rest is normal python.
#
# This is odd, but for me, it was ultimately easier than dealing with shell
# quoting the ruby source to pass it on the command line to rails runner via
# subprocess.Popen; (and indeed for alternative runners that might not be an
# option)
#
# one could put the ruby in a separate file, but I don't know where in the agent
# that file should live; @donaldguy, 1 Oct 2014
#
# anyway DON'T DELETE THIS RUBY OR PUT ANY PYTHON ABOVE IT!!!
""""
require 'sidekiq/api'
sidekiq_stats = Sidekiq::Stats.new
puts Sidekiq.dump_json({
  for_datadog: {
    processed:  sidekiq_stats.processed,
    failed:     sidekiq_stats.failed,
    busy:       Sidekiq::Workers.new.size,
    enqueued:   sidekiq_stats.enqueued,
    scheduled:  sidekiq_stats.scheduled_size,
    retries:    sidekiq_stats.retry_size,
    queues: sidekiq_stats.queues
  }
})
__END__
"""
#and now back to your regularly scheduled python...

import os
import re
import subprocess
import json

# project
from checks import AgentCheck, CheckException

# 3rd party
import psutil

class Sidekiq(AgentCheck):
    def _procs_by_app(self):
        """
        Search for running sidekiq processes and group them by app tag
        (i.e. `pgrep -fa '^sidekiq' | cut -d' ' -f 4`)
        """
        all_sidekiq_procs = [p for p in psutil.process_iter()
                             if p.name() == 'ruby'
                             and p.cmdline()[0].startswith('sidekiq')]

        sidekiq_procs_by_app = {}

        for sidekiq_proc in all_sidekiq_procs:
            # sidekiq overwrites command line to be e.g.
            #'sidekiq 2.14.0 myapp [2 of 10 busy]'
            # see: http://git.io/57ktWQ
            sk_cmdline = sidekiq_proc.cmdline()[0]
            app_tag = sk_cmdline.split()[2]

            # sometimes there is no tag....
            if re.search(r'^\[\d', app_tag):
                app_tag = '__none__'

            sidekiq_procs_by_app.setdefault(app_tag, []).append(sidekiq_proc)

        return sidekiq_procs_by_app

    def _get_check_config(self, instance, running_proc):
        """
        Read config as defined in instance in conf.d/sidekiq.yaml; See
        conf.d/sidekiq.yaml.example for descriptions of the various options.
        """
        config = {'env': os.environ.copy()}
        config['env']['RAILS_ENV'] = instance.get('rails_env', 'production')


        config['wd'] = instance.get('wd') or running_proc.cwd()
        runner = instance.get('runner')
        if type(runner) == str:
            runner = runner.split()
        elif not runner:
            runner = [os.path.join('.', 'bin', 'rails'), 'runner']
        config['runner'] = runner
        config['script'] = [instance.get('script',
                                        # else use ruby from top of this file
                                        __file__.replace('.pyc', '.py'))]

        # account for relative paths
        for key in ['runner', 'script']:
            if not os.path.isabs(config[key][0]):
                full_path = os.path.join(config['wd'], config[key][0])
                config[key][0] = os.path.normpath(full_path)

        config['sudo'] = instance.get('sudo')
        if config['sudo']:
            sudo_user = instance.get('sudo_user') or running_proc.username()
            config['runner'] = ['sudo', '-u', sudo_user] + config['runner']

        config['runner_args'] = instance.get('runner_args', [])
        config['script_args'] = instance.get('script_args', [])

        return config

    def _get_json(self, config):
        """
        Given an instance and a sidekiq process, invoke a ruby script in its
        working directory, parse the output, and return the last line containing
        'for_datadog' as json
        """


        cmd = config['runner'] + config['runner_args'] + config['script'] + config['script_args']

        output, error = subprocess.Popen(cmd,
                                         cwd=config['wd'],
                                         env=config['env'],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE).communicate()

        if len(error) != 0:
            raise CheckException("Errors from runner: " + error + """
            Tips:
               - Make sure the dd-agent user has read permissions on the parts of the
                 source that need to be invoked to load app.
               - May also need write permissions on some log files to load
                 succesfully.
               - Consider allowing passwordless sudo from dd-agent to sidekiq
                 user, e.g.
                   Defaults   env_keep += RAILS_ENV
                   dd-agent ALL = (sidekiq_user) NOPASSWD:ALL
                 and then set sudo: true in conf.d/sidekiq.yaml
               - In any case, be aware of the less-than-amazing security implications
                 of this action
            """)

        # there may be log messages before the line we care about. Read from end
        # until we see our tag, then parse the JSON
        return next(json.loads(line) for line
                    in reversed(output.split("\n"))
                    if line.find("for_datadog") > 0)


    def check(self, instance):
        """
        For each instance consisting of an app/working directory pair, verify
        the existence of running sidekiq workers with that 'tag', then report
        metrics offered by `sidekiq/api.rb` by invoking rails runner relative
        to that working directory. If working directory is not given, will use
        pwd of the running process (if process table permissions allow).
        """
        for app, procs in self._procs_by_app().iteritems():
            if instance.has_key('app') and app != instance.get('app'):
                continue

            app_tags = []
            if  app != '__none__':
                app_tags.append('sidekiq_app:%s' % app)

            #check for a running process matching this app
            running_proc = next((p for p in procs if p.is_running()), None)
            if not running_proc:
                self.warning("No running sidekiq workers matching app '%s'"
                             % instance.get('app'))
                self.service_check('sidekiq.workers_running', AgentCheck.CRITICAL, tags=app_tags)
            else:
                self.service_check('sidekiq.workers_running', AgentCheck.OK, tags=app_tags)
                config = self._get_check_config(instance, running_proc)
                sk_json = self._get_json(config)


                for key, value in sk_json['for_datadog'].iteritems():
                    if key == 'queues':
                        for queue, messages in value.iteritems():
                            self.gauge('sidekiq.queue.messages',
                                       float(messages),
                                       app_tags+['sidekiq_queue:'+queue])
                    else:
                        metric_name = 'sidekiq.app.%s' % (key)
                        self.gauge(metric_name, float(value), app_tags)

