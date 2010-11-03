import os
import re
import time

from datetime import datetime
from glob import glob

class Hudson(object):
	def check(self, logger, agentConfig):
		hudson_home = agentConfig.get('hudson_home', '/Users/hudson/.hudson/')
		jobs = glob(os.path.join(hudson_home, 'jobs', '*'))
		
		for job in jobs:
			job_name = os.path.basename(job)
			for dir_name in glob(os.path.join(job, 'builds', '*')):
				try:
					date_str = os.path.basename(dir_name)
					time_tuple = time.strptime(date_str, '%Y-%m-%d_%H-%I-%S')
					timestamp = time.mktime(time_tuple)
				except ValueError:
					continue
				else:
					build_metadata = os.path.join(dir_name, 'build.xml')
				
					result_line = [
						line for line in open(build_metadata)
						if '<result>' in line
					]
				
					if len(result_line) == 1:
						match = re.match('\s*<result>(?P<result>[A-Za-z]*)</result>\s*', result_line[0])
					
						if match:
							result = match.group('result')
							print timestamp, job_name, result
						else:
							pass
					else:
						continue
				


if __name__ == '__main__':
	Hudson().check(None, {})
		