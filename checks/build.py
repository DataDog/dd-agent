import os
import re
import time
import traceback

from collections import defaultdict
from datetime import datetime
from glob import glob

class Continue(Exception):
	pass

class Hudson(object):
	key = 'Hudson'
	datetime_format = '%Y-%m-%d_%H-%M-%S'
	result_pattern = re.compile('\s*<result>(?P<result>[A-Za-z]*)</result>\s*')
	
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
	
	def _get_result(self, dir_name):
		# Read the build.xml metadata file that Hudson generates
		build_metadata = os.path.join(dir_name, 'build.xml')
		
		if not os.access(build_metadata, os.R_OK):
			raise Continue("Can't read build file at {0}".format(build_metadata))
		else:
			# Lazy xml parsing. Since each element is on a newline,
			# run a regexp on each line to find the result.
			matches = (
				self.result_pattern.match(line) 
				for line in open(build_metadata)
			)
			
			matched = [match for match in matches if match]

			if len(matched) != 1:
				result = None
			else:
				result = matched[0].group('result')
		
			return result
	
	def _update_high_watermark(self, job_name, timestamp):
		self.high_watermarks[job_name] = max(timestamp, self.high_watermarks[job_name])

	def _get_build_results(self, logger, job_dir):
		job_name = os.path.basename(job_dir)
		
		for dir_name in glob(os.path.join(job_dir, 'builds', '*')):

			try:
				timestamp = self._extract_timestamp(job_name, dir_name)
				result = self._get_result(dir_name)
				self._update_high_watermark(job_name, timestamp)

			except Continue, e:
				logger.debug(str(e))
				
			except Exception:
				# Catchall so that the agent loop doesn't die
				# if there are unexpected errors.
				logger.error(traceback.format_exc())
				
			else:
				yield {
					'job_name': job_name,
					'timestamp': timestamp,
					'result': result,
					'event_type': 'build result'
				}
			
					
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
				build_events.append(output)
		
		return build_events

				


if __name__ == '__main__':
	import logging
	logger = logging.getLogger('hudson')
	logger.setLevel(logging.INFO)
	logger.addHandler(logging.StreamHandler())
	hudson = Hudson()
	while True:
		hudson.check(logger, {'hudson_home': '/Users/hudson/.hudson/'})
		time.sleep(1)
		