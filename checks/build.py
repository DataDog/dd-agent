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

class Continue(Exception):
    pass

class Hudson(object):
    key = 'Hudson'
    datetime_format = '%Y-%m-%d_%H-%M-%S'
    
    def __init__(self):
        self.high_watermarks = None
    
    def _extract_timestamp(self, job_name, dir_name):
        try:
            # Parse the timestamp from the directory name
            date_str = os.path.basename(dir_name)
            time_tuple = time.strptime(date_str, self.datetime_format)
            timestamp = time.mktime(time_tuple)
        except ValueError:
            raise Continue("Skipping non-timestamp dir: {0}".format(dir_name))
        else:
            # Check if it's a build we've seen already
            if timestamp <= self.high_watermarks[job_name]:
                raise Continue("Skipping old build: {0} at {1}".format(job_name, timestamp))
            else:
                return timestamp
    
    def _get_build_metadata(self, dir_name):
        # Read the build.xml metadata file that Hudson generates
        build_metadata = os.path.join(dir_name, 'build.xml')
        
        if not os.access(build_metadata, os.R_OK):
            raise Continue("Can't read build file at {0}".format(build_metadata))
        else:
            tree = ElementTree()
            tree.parse(build_metadata)
            
            keys = ['result', 'number', 'duration']
            
            kv_pairs = ((k, tree.find(k)) for k in keys)
            d = dict([(k, v.text) 
                        for k, v in kv_pairs 
                        if v is not None])
            return d
    
    def _update_high_watermark(self, job_name, timestamp):
        self.high_watermarks[job_name] = max(timestamp, self.high_watermarks[job_name])
    
    def _get_build_results(self, logger, job_dir):
        job_name = os.path.basename(job_dir)
        
        for dir_name in glob(os.path.join(job_dir, 'builds', '*')):
            
            try:
                timestamp = self._extract_timestamp(job_name, dir_name)
                build_metadata = self._get_build_metadata(dir_name)
                self._update_high_watermark(job_name, timestamp)
            
            except Continue, e:
                logger.debug(str(e))
            
            except Exception:
                # Catchall so that the agent loop doesn't die
                # if there are unexpected errors.
                logger.error(traceback.format_exc())
            
            else:
                output = {
                    'job_name':     job_name,
                    'timestamp':    timestamp,
                    'event_type':   'build result'
                }
                output.update(build_metadata)
                yield output
    
    
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
        
        # Copied from main check loop. Probably bad,
        # but the ETL needs host on each event dict
        
        try:
            host = socket.gethostname()
        except socket.error, e:
            pass
        
        for job_dir in job_dirs:
            for output in self._get_build_results(logger, job_dir):
                output['api_key'] = agentConfig['apiKey']
                output['host'] = host
                build_events.append(output)
        
        return build_events




if __name__ == '__main__':
    import logging
    import sys
    
    hudson_home, apiKey = sys.argv[1:3]
    
    logger = logging.getLogger('hudson')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    hudson = Hudson()
    while True:
        print hudson.check(logger, {'hudson_home': hudson_home,
                              'apiKey':      apiKey})
        time.sleep(1)
        
