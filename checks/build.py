import os
import re
import socket
import time
import traceback

try:
    from collections import defaultdict
except ImportError:
    from compat.defaultdict import defaultdict

from datetime import datetime
from glob import glob

try:
    from xml.etree.ElementTree import ElementTree
except ImportError:
    from elementtree import ElementTree

from util import get_hostname

class Continue(Exception):
    pass

class Hudson(object):
    key = 'Hudson'
    datetime_format = '%Y-%m-%d_%H-%M-%S'

    def __init__(self):
        self.high_watermarks = None

    def _extract_timestamp(self, dir_name):
        try:
            # Parse the timestamp from the directory name
            date_str = os.path.basename(dir_name)
            time_tuple = time.strptime(date_str, self.datetime_format)
            return time.mktime(time_tuple)
        except ValueError:
            raise Exception("Error with build directory name, not a parsable date: %s" % (dir_name))

    def _get_build_metadata(self, dir_name):
        # Read the build.xml metadata file that Hudson generates
        build_metadata = os.path.join(dir_name, 'build.xml')

        if not os.access(build_metadata, os.R_OK):
            raise Continue("Can't read build file at %s" % (build_metadata))
        else:
            tree = ElementTree()
            tree.parse(build_metadata)

            keys = ['result', 'number', 'duration']

            kv_pairs = ((k, tree.find(k)) for k in keys)
            d = dict([(k, v.text)
                        for k, v in kv_pairs
                        if v is not None])
            return d

    def _get_build_results(self, logger, job_dir):
        job_name = os.path.basename(job_dir)

        try:
            dirs = glob(os.path.join(job_dir, 'builds', '*_*'))
            if len(dirs) > 0:
                dirs = sorted(dirs, reverse=True)
                # We try to get the last valid build
                for index in xrange(0, len(dirs) - 1):
                    dir_name = dirs[index]
                    timestamp = self._extract_timestamp(dir_name)
                    # Check if it's a new build
                    if timestamp > self.high_watermarks[job_name]:
                        # If we can't get build metadata, we try the previous one
                        try:
                            build_metadata = self._get_build_metadata(dir_name)
                        except:
                            continue

                        output = {
                                'job_name':     job_name,
                                'timestamp':    timestamp,
                                'event_type':   'build result'
                            }
                        output.update(build_metadata)
                        self.high_watermarks[job_name] = timestamp
                        yield output
                    # If it not a new build, stop here
                    else:
                        break
        except Exception, e:
            logger.error("Error while working on job %s, exception: %s" % (job_name, e))

    def check(self, logger, agentConfig):
        if self.high_watermarks is None:
            # On the first run of check(), prime the high_watermarks dict
            # so that we only send events that occured after the agent
            # started.
            # (Setting high_watermarks in the next statement prevents
            #  any kind of infinite loop (assuming nothing ever sets
            #  high_watermarks to None again!))
            self.high_watermarks = defaultdict(lambda: 0)
            self.check(logger, agentConfig)

        hudson_home = agentConfig.get('hudson_home', None)

        if not hudson_home:
            return False

        job_dirs = glob(os.path.join(hudson_home, 'jobs', '*'))

        build_events = []

        for job_dir in job_dirs:
            for output in self._get_build_results(logger, job_dir):
                output['api_key'] = agentConfig['api_key']
                output['host'] = get_hostname(agentConfig)
                build_events.append(output)

        return build_events

if __name__ == '__main__':
    import logging
    import sys

    hudson_home, apiKey = sys.argv[1:3]

    logger = logging.getLogger('ddagent.checks.hudson')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    hudson = Hudson()
    while True:
        print hudson.check(logger,
                           {'hudson_home': hudson_home,
                            'api_key': apiKey})
        time.sleep(5)
