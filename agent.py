'''
	Server Density
	www.serverdensity.com
	----
	A web based server resource monitoring application

	Licensed under Simplified BSD License (see LICENSE)
	(C) Boxed Ice 2009 all rights reserved
'''

# General config
agentConfig = {}
agentConfig['debugMode'] = 0
agentConfig['checkFreq'] = 60

agentConfig['version'] = '1.0.0b5'

# Core modules
import ConfigParser
import logging
import sched
import time
import sys

# Check we're not using an old version of Python. We need 2.4 above because some modules (like subprocess)
# were only introduced in 2.4.
if int(sys.version_info[1]) <= 3:
	print 'You are using an outdated version of Python. Please update to v2.4 or above (v3 is not supported).'
	sys.exit(2)
	
# Custom modules
from checks import checks
from daemon import Daemon

# Config handling
try:
	config = ConfigParser.ConfigParser()
	config.read('config.cfg')
	
	# Core config
	agentConfig['sdUrl'] = config.get('Main', 'sd_url')
	agentConfig['agentKey'] = config.get('Main', 'agent_key')
	
	# Optional config
	agentConfig['apacheStatusUrl'] = config.get('Main', 'apache_status_url')
	
except ConfigParser.NoSectionError, e:
	print 'Config file not found or incorrectly formatted'
	sys.exit(2)
	
except ConfigParser.ParsingError, e:
	print 'Config file not found or incorrectly formatted'
	sys.exit(2)
	
# Check to make sure the default config values have been changed (only core config values)
if agentConfig['sdUrl'] == 'http://www.example.com' or agentConfig['agentKey'] == 'keyHere':
	print 'You have not modified config.cfg for your server'
	sys.exit(2)

# Override the generic daemon class to run our checks
class agent(Daemon):	
	
	def run(self):	
		agentLogger = logging.getLogger('agent')		
		agentLogger.debug('Creating checks instance')
		
		# Checks instance
		c = checks(agentConfig)
		
		# Schedule the checks
		agentLogger.debug('Scheduling checks every ' + str(agentConfig['checkFreq']) + ' seconds')
		s = sched.scheduler(time.time, time.sleep)
		s.enter(agentConfig['checkFreq'], 1, c.doChecks, (s,))
		s.run()

# Control of daemon		
if __name__ == '__main__':	
	# Logging
	if agentConfig['debugMode']:
		logging.basicConfig(filename='/tmp/sd-agent.log', filemode='w', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	
	mainLogger = logging.getLogger('main')		
	mainLogger.debug('Agent called')
	
	# Daemon instance from agent class
	daemon = agent('/tmp/sd-agent.pid')
	
	# Control options
	if len(sys.argv) == 2:		
		if 'start' == sys.argv[1]:
			mainLogger.debug('Start daemon')
			daemon.start()
			
		elif 'stop' == sys.argv[1]:
			mainLogger.debug('Stop daemon')
			daemon.stop()
			
		elif 'restart' == sys.argv[1]:
			mainLogger.debug('Restart daemon')
			daemon.restart()
			
		elif 'update' == sys.argv[1]:
			mainLogger.debug('Updating agent')
			
			import httplib
			import platform
			import urllib2
			
			print 'Checking if there is a new version';
			
			# Get the latest version info
			try: 
				mainLogger.debug('Update: checking for update')
				
				request = urllib2.urlopen('http://www.serverdensity.com/agentupdate/')
				response = request.read()
				
			except urllib2.HTTPError, e:
				print 'Unable to get latest version info - HTTPError = ' + str(e.reason)
				sys.exit(2)
				
			except urllib2.URLError, e:
				print 'Unable to get latest version info - URLError = ' + str(e.reason)
				sys.exit(2)
				
			except httplib.HTTPException, e:
				print 'Unable to get latest version info - HTTPException'
				sys.exit(2)
				
			except Exception, e:
				import traceback
				print 'Unable to get latest version info - Exception = ' + traceback.format_exc()
				sys.exit(2)
			
			mainLogger.debug('Update: importing json/minjson')
			
			# We need to return the data using JSON. As of Python 2.6+, there is a core JSON
			# module. We have a 2.4/2.5 compatible lib included with the agent but if we're
			# on 2.6 or above, we should use the core module which will be faster
			pythonVersion = platform.python_version_tuple()
			
			# Decode the JSON
			if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
				import json
				
				mainLogger.debug('Update: decoding JSON (json)')
				
				try:
					updateInfo = json.loads(response)
				except Exception, e:
					print 'Unable to get latest version info. Try again later.'
					sys.exit(2)
				
			else:
				import minjson
				
				mainLogger.debug('Update: decoding JSON (minjson)')
				
				try:
					updateInfo = minjson.safeRead(response)
				except Exception, e:
					print 'Unable to get latest version info. Try again later.'
					sys.exit(2)
			
			# Do the version check	
			if updateInfo['version'] != agentConfig['version']:			
				import md5
				import urllib
				
				print 'A new version is available.'
				
				def downloadFile(agentFile, recursed = False):
					mainLogger.debug('Update: downloading ' + agentFile['name'])					
					print 'Downloading ' + agentFile['name']
					
					downloadedFile = urllib.urlretrieve('http://www.serverdensity.com/downloads/sd-agent/' + agentFile['name'])
					
					# Do md5 check to make sure the file downloaded properly
					checksum = md5.new()
					f = file(downloadedFile[0], 'rb')
					
					# Although the files are small, we can't guarantee the available memory nor that there
					# won't be large files in the future, so read the file in small parts (1kb at time)
					while True:
						part = f.read(1024)
						
						if not part: 
							break # end of file
					
						checksum.update(part)
						
					f.close()
					
					# Do we have a match?
					if checksum.hexdigest() == agentFile['md5']:
						return downloadedFile[0]
						
					else:
						# Try once more
						if recursed == False:
							downloadFile(agentFile, True)
						
						else:
							print agentFile['name'] + ' did not match its checksum - it is corrupted. This may be caused by network issues so please try again in a moment.'
							sys.exit(2)
				
				# Loop through the new files and call the download function
				for agentFile in updateInfo['files']:
					agentFile['tempFile'] = downloadFile(agentFile)			
				
				# If we got to here then everything worked out fine. However, all the files are still in temporary locations so we need to move them
				# This is to stop an update breaking a working agent if the update fails halfway through
				import os
				
				for agentFile in updateInfo['files']:
					mainLogger.debug('Update: updating ' + agentFile['name'])
					print 'Updating ' + agentFile['name']
					
					if os.path.exists(agentFile['name']):
						os.remove(agentFile['name'])
						
					os.rename(agentFile['tempFile'], agentFile['name'])
				
				mainLogger.debug('Update: done')
				
				print 'Update completed. Please restart the agent (python agent.py restart).'
				
			else:
				print 'The agent is already up to date'
		
		else:
			print 'Unknown command'
			sys.exit(2)
			
		sys.exit(0)
		
	else:
		print 'usage: %s start|stop|restart|update' % sys.argv[0]
		sys.exit(2)