'''
	Server Density
	www.serverdensity.com
	----
	A web based server resource monitoring application

	Licensed under Simplified BSD License (see LICENSE)
	(C) Boxed Ice 2009 all rights reserved
'''

# General config
DEBUG_MODE = 0
CHECK_FREQUENCY = 60

VERSION = '1.0.0b4'

# Core modules
import ConfigParser
import logging
import sched
import time
import sys

# Check we're not using an old version of Python. We need 2.4 above because some modules (like subprocess)
# were only introduced in 2.4.
if int(sys.version_info[1]) <= 4:
	print 'You are using an outdated version of Python. Please update to v2.4 or above (v3 is not supported).'
	sys.exit(2)
	
# Custom modules
from checks import checks
from daemon import Daemon

# Config handling
try:
	config = ConfigParser.ConfigParser()
	config.read('config.cfg')
	SD_URL = config.get('Main', 'sd_url')
	AGENT_KEY = config.get('Main', 'agent_key')
	
except ConfigParser.NoSectionError, e:
	print 'Config file not found or incorrectly formatted'
	quit()
	
except ConfigParser.ParsingError, e:
	print 'Config file not found or incorrectly formatted'
	quit()
	
# Check to make sure the default config values have been changed
if SD_URL == 'http://www.example.com' or AGENT_KEY == 'keyHere':
	print 'You have not modified config.cfg for your server'
	quit()

# Override the generic daemon class to run our checks
class agent(Daemon):	
	
	def run(self):	
		agentLogger = logging.getLogger('agent')		
		agentLogger.debug('Creating checks instance')
		
		# Checks instance
		c = checks(SD_URL, AGENT_KEY, CHECK_FREQUENCY, VERSION, DEBUG_MODE)
		
		# Schedule the checks
		agentLogger.debug('Scheduling checks every ' + str(CHECK_FREQUENCY) + ' seconds')
		s = sched.scheduler(time.time, time.sleep)
		s.enter(CHECK_FREQUENCY, 1, c.doChecks, (s,))
		s.run()

# Control of daemon		
if __name__ == '__main__':	
	# Logging
	if DEBUG_MODE:
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
				
			except urllib2.URLError, e:
				print 'Unable to get latest version info - URLError = ' + str(e.reason)
				
			except httplib.HTTPException, e:
				print 'Unable to get latest version info - HTTPException'
				
			except Exception, e:
				import traceback
				print 'Unable to get latest version info - Exception = ' + traceback.format_exc()
			
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
					quit()
				
			else:
				import minjson
				
				mainLogger.debug('Update: decoding JSON (minjson)')
				
				try:
					updateInfo = minjson.safeRead(response)
				except Exception, e:
					print 'Unable to get latest version info. Try again later.'
					quit()
			
			# Do the version check	
			if updateInfo['version'] != VERSION:			
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
							quit()
				
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