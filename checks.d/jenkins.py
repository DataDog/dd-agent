import os
import time

try:
    from collections import defaultdict
except ImportError:
    from compat.defaultdict import defaultdict

from datetime import datetime
from glob import glob

try:
    from xml.etree.ElementTree import ElementTree
except ImportError:
    try:
        from elementtree import ElementTree
    except ImportError:
        pass

from util import get_hostname
from checks import AgentCheck


class Skip(Exception):
    """
    Raised by :class:`Jenkins` when it comes across
    a build or job that should be excluded from being checked.
    """
    def __init__(self, reason, dir_name):
        message = 'skipping build or job at %s because %s' % (dir_name, reason)
        Exception.__init__(self, message)


class Jenkins(AgentCheck):
    datetime_format = '%Y-%m-%d_%H-%M-%S'

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.high_watermarks = {}

    def _extract_timestamp(self, dir_name):
        if not os.path.isdir(dir_name):
            raise Skip('its not a build directory', dir_name)

        try:
            # Parse the timestamp from the directory name
            date_str = os.path.basename(dir_name)
            time_tuple = time.strptime(date_str, self.datetime_format)
            return time.mktime(time_tuple)
        except ValueError:
            raise Exception("Error with build directory name, not a parsable date: %s" % (dir_name))

    def _get_build_metadata(self, dir_name):
        if os.path.exists(os.path.join(dir_name, 'jenkins_build.tar.gz')):
            raise Skip('the build has already been archived', dir_name)

        # Read the build.xml metadata file that Jenkins generates
        build_metadata = os.path.join(dir_name, 'build.xml')

        if not os.access(build_metadata, os.R_OK):
            self.log.debug("Can't read build file at %s" % (build_metadata))
            raise Exception("Can't access build.xml at %s" % (build_metadata))
        else:
            tree = ElementTree()
            tree.parse(build_metadata)

            keys = ['result', 'number', 'duration']

            kv_pairs = ((k, tree.find(k)) for k in keys)
            d = dict([(k, v.text) for k, v in kv_pairs if v is not None])

            try:
                d['branch'] = tree.find('actions')\
                    .find('hudson.plugins.git.util.BuildData')\
                    .find('buildsByBranchName')\
                    .find('entry')\
                    .find('hudson.plugins.git.util.Build')\
                    .find('revision')\
                    .find('branches')\
                    .find('hudson.plugins.git.Branch')\
                    .find('name')\
                    .text
            except Exception:
                pass
            return d

    def _get_build_results(self, instance_key, job_dir):
        job_name = os.path.basename(job_dir)

        try:
            dirs = glob(os.path.join(job_dir, 'builds', '*_*'))
            if len(dirs) > 0:
                dirs = sorted(dirs, reverse=True)
                # We try to get the last valid build
                for index in xrange(0, len(dirs) - 1):
                    dir_name = dirs[index]
                    try:
                        timestamp = self._extract_timestamp(dir_name)
                    except Skip:
                        continue

                    # Check if it's a new build
                    if timestamp > self.high_watermarks[instance_key][job_name]:
                        # If we can't get build metadata, we try the previous one
                        try:
                            build_metadata = self._get_build_metadata(dir_name)
                        except Exception:
                            continue

                        output = {
                            'job_name':     job_name,
                            'timestamp':    timestamp,
                            'event_type':   'build result'
                        }
                        output.update(build_metadata)
                        self.high_watermarks[instance_key][job_name] = timestamp
                        yield output
                    # If it not a new build, stop here
                    else:
                        break
        except Exception, e:
            self.log.error("Error while working on job %s, exception: %s" % (job_name, e))

    def check(self, instance, create_event=True):
        if self.high_watermarks.get(instance.get('name'), None) is None:
            # On the first run of check(), prime the high_watermarks dict
            # so that we only send events that occured after the agent
            # started.
            # (Setting high_watermarks in the next statement prevents
            #  any kind of infinite loop (assuming nothing ever sets
            #  high_watermarks to None again!))
            self.high_watermarks[instance.get('name')] = defaultdict(lambda: 0)
            self.check(instance, create_event=False)

        jenkins_home = instance.get('jenkins_home', None)

        if not jenkins_home:
            raise Exception("No jenkins_home directory set in the config file")

        job_dirs = glob(os.path.join(jenkins_home, 'jobs', '*'))

        if not job_dirs:
            raise Exception('No jobs found in `%s`! '
                            'Check `jenkins_home` in your config' % (job_dirs))

        for job_dir in job_dirs:
            for output in self._get_build_results(instance.get('name'), job_dir):
                output['api_key'] = self.agentConfig['api_key']
                output['host'] = get_hostname(self.agentConfig)
                if create_event:
                    self.log.debug("Creating event for job: %s" % output['job_name'])
                    self.event(output)

                    tags = ['job_name:%s' % output['job_name']]
                    if 'branch' in output:
                        tags.append('branch:%s' % output['branch'])
                    self.gauge("jenkins.job.duration", float(output['duration'])/1000.0, tags=tags)

                    if output['result'] == 'SUCCESS':
                        self.increment('jenkins.job.success', tags=tags)
                    else:
                        self.increment('jenkins.job.failure', tags=tags)

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('hudson_home'):
            return False

        return {
            'instances': [{
                'name': 'default',
                'jenkins_home': agentConfig.get('hudson_home'),
            }]
        }

