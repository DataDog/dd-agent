import os
import re
import time
import traceback

from collections import defaultdict
from datetime import datetime
from glob import glob

class Hudson(object):
	datetime_format = '%Y-%m-%d_%H-%M-%S'
	result_pattern = re.compile('\s*<result>(?P<result>[A-Za-z]*)</result>\s*')
	
	def __init__(self):
		self.high_watermarks = defaultdict(lambda: 0)
	
	def _extract_timestamp(self, dir_name):
		try:
			date_str = os.path.basename(dir_name)
			time_tuple = time.strptime(date_str, self.datetime_format)
			timestamp = time.mktime(time_tuple)
		except ValueError:
			return None
		else:
			return timestamp
	
	def _is_new_build(self, job_name, timestamp):
		return timestamp > self.high_watermarks[job_name]
	
	def _get_build_metadata(self, dir_name):
		build_metadata = os.path.join(dir_name, 'build.xml')
		
		if not os.access(build_metadata, os.R_OK):
			return None
		else:
			return build_metadata
	
	def _get_result(self, build_metadata):
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

	def _get_build_results(self, job_dir):
		job_name = os.path.basename(job_dir)
		
		for dir_name in glob(os.path.join(job_dir, 'builds', '*')):
			timestamp = self._extract_timestamp(dir_name)
			
			if not timestamp:
				continue
			
			if not self._is_new_build(job_name, timestamp):
				continue

			build_metadata = self._get_build_metadata(dir_name)
			
			if not build_metadata:
				continue

			result = self._get_result(build_metadata)
			
			if not result:
				continue
			
			self._update_high_watermark(job_name, timestamp)

			yield timestamp, job_name, result	
			
					
	def check(self, logger, agentConfig):
		hudson_home = agentConfig.get('hudson_home', None)
		
		if not hudson_home:
			return False
		
		job_dirs = glob(os.path.join(hudson_home, 'jobs', '*'))
		
		for job_dir in job_dirs:
			for output in self._get_build_results(job_dir):
				print output

				


if __name__ == '__main__':
	hudson = Hudson()
	while True:
		hudson.check(None, {'hudson_home': '/Users/hudson/.hudson/'})
		time.sleep(1)
		