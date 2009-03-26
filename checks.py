'''
	Server Density
	www.serverdensity.com
	----
	A web based server resource monitoring application

	Licensed under Simplified BSD License (see LICENSE)
	(C) Boxed Ice 2009 all rights reserved
'''

# Core modules
import httplib # Used only for handling httplib.HTTPException (case #26701)
import logging
import logging.handlers
import md5
import platform
import re
import subprocess
import sys
import urllib
import urllib2

# We need to return the data using JSON. As of Python 2.6+, there is a core JSON
# module. We have a 2.4/2.5 compatible lib included with the agent but if we're
# on 2.6 or above, we should use the core module which will be faster
pythonVersion = platform.python_version_tuple()

if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
	import json
else:
	import minjson

class checks:
	
	def __init__(self, SD_URL, AGENT_KEY, CHECK_FREQUENCY, VERSION, DEBUG_MODE):
		self.SD_URL = SD_URL
		self.AGENT_KEY = AGENT_KEY
		self.CHECK_FREQUENCY = CHECK_FREQUENCY
		self.VERSION = VERSION
		self.DEBUG_MODE = DEBUG_MODE
		
	def getDf(self):
		# CURRENTLY UNUSED
		
		# Get output from df
		try:
			df = subprocess.Popen(['df'], stdout=subprocess.PIPE).communicate()[0]
		except Exception, e:
			import traceback
			self.checksLogger.error('getDf - Exception = ' + traceback.format_exc())
		
		# Split out each volume
		volumes = df.split('\n')
		
		# Remove first (headings) and last (blank)
		volumes.pop()
		volumes.pop(0)
		
		# Loop through each volue and split out parts
		for volume in volumes:
			parts = re.findall(r'[a-zA-Z0-9_/]+', volume)
	
	def getLoadAvrgs(self):
		self.checksLogger.debug('Getting loadAvrgs')
		
		# Get output from uptime
		try:
			uptime = subprocess.Popen(['uptime'], stdout=subprocess.PIPE).communicate()[0]
		except Exception, e:
			import traceback
			self.checksLogger.error('getLoadAvrgs - Exception = ' + traceback.format_exc())
			
		# Split out the 3 load average values (we actually only use the 5 min average)
		loadAvrgs = re.findall(r'([0-9]+\.\d+)', uptime)
		
		self.checksLogger.debug('Got loadAvrgs - ' + uptime)
	
		return loadAvrgs # We only use loadAvrgs[0] but may use more in the future, so return all
		
	def getMemoryUsage(self):
		self.checksLogger.debug('Getting memoryUsage')
		
		# See http://stackoverflow.com/questions/446209/possible-values-from-sys-platform/446210#446210 for possible
		# sys.platform values
		if sys.platform == 'linux2':
			self.checksLogger.debug('memoryUsage - linux2')
			
			try:
				free = subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE).communicate()[0]
			except Exception, e:
				import traceback
				self.checksLogger.error('getMemoryUsage (linux2) - Exception = ' + traceback.format_exc())
			
			lines = free.split('\n')
			physParts = re.findall(r'([0-9]+)', lines[1])
			swapParts = re.findall(r'([0-9]+)', lines[3])
			
			self.checksLogger.debug('Got memoryUsage - Phys ' + physParts[1] + ' / ' + physParts[2] + ' Swap ' + swapParts[1] + ' / ' + swapParts[2])
			
			return {'physUsed' : physParts[1], 'physFree' : physParts[2], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2]}			
		elif sys.platform == 'darwin':
			self.checksLogger.debug('memoryUsage - darwin')
			
			try:
				top = subprocess.Popen(['top', '-l 1'], stdout=subprocess.PIPE).communicate()[0]
				sysctl = subprocess.Popen(['sysctl', 'vm.swapusage'], stdout=subprocess.PIPE).communicate()[0]
			except Exception, e:
				import traceback
				self.checksLogger.error('getMemoryUsage (darwin) - Exception = ' + traceback.format_exc())
			
			# Deal with top			
			lines = top.split('\n')
			physParts = re.findall(r'([0-9]\d+)', lines[5])
			
			# Deal with sysctl
			swapParts = re.findall(r'([0-9]+\.\d+)', sysctl)
			
			self.checksLogger.debug('Got memoryUsage - Phys ' + physParts[3] + ' / ' + physParts[4] + ' Swap ' + swapParts[1] + ' / ' + swapParts[2])
		
			return {'physUsed' : physParts[3], 'physFree' : physParts[4], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2]}			
		else:
			return false
		
	def getProcesses(self):
		self.checksLogger.debug('Getting processes')
		
		# Get output from ps
		try:
			ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
		except Exception, e:
			import traceback
			self.checksLogger.error('getProcessCount - Exception = ' + traceback.format_exc())
		
		self.checksLogger.debug('Got processes, now to split')
		
		# Split out each process
		processLines = ps.split('\n')
		
		del processLines[0] # Removes the headers
		processLines.pop() # Removes a trailing empty line
		
		processes = []
		
		# http://stackoverflow.com/questions/682446/splitting-out-the-output-of-ps-using-python/682464#682464
		for line in processLines:
			line = line.split(None, 10)
			processes.append(line)
			
		return processes
		
	def doPostBack(self, postBackData):
		self.checksLogger.debug('Doing postback to ' + self.SD_URL)	
		
		try: 
			# Build the request handler
			request = urllib2.Request(self.SD_URL + '/postback/', postBackData, { 'User-Agent' : 'Server Density Agent' })
			
			# Do the request, log any errors
			response = urllib2.urlopen(request)
			
			if self.DEBUG_MODE:
				print response.read()
		except urllib2.HTTPError, e:
			self.checksLogger.error('Unable to postback - HTTPError = ' + str(e.reason))
		except urllib2.URLError, e:
			self.checksLogger.error('Unable to postback - URLError = ' + str(e.reason))
		except httplib.HTTPException, e: # Added for case #26701
			self.checksLogger.error('Unable to postback - HTTPException')	
		except Exception, e:
			import traceback
			self.checksLogger.error('Unable to postback - Exception = ' + traceback.format_exc())
		
		self.checksLogger.debug('Posted back')
	
	def doChecks(self, sc):
		self.checksLogger = logging.getLogger('checks')
		
		self.checksLogger.debug('doChecks')
				
		# Do the checks
		loadAvrgs = self.getLoadAvrgs()
		processes = self.getProcesses()
		memory = self.getMemoryUsage()
		
		self.checksLogger.debug('All checks done, now to post back')
		
		# Post back the data
		if int(pythonVersion[1]) >= 6:
			payload = json.dumps({'agentKey' : self.AGENT_KEY, 'agentVersion' : self.VERSION, 'loadAvrg' : loadAvrgs[0], 'processes' : processes, 'memPhysUsed' : memory['physUsed'], 'memPhysFree' : memory['physFree'], 'memSwapUsed' : memory['swapUsed'], 'memSwapFree' : memory['swapFree']})
		else:
			payload = minjson.write({'agentKey' : self.AGENT_KEY, 'agentVersion' : self.VERSION, 'loadAvrg' : loadAvrgs[0], 'processes' : processes, 'memPhysUsed' : memory['physUsed'], 'memPhysFree' : memory['physFree'], 'memSwapUsed' : memory['swapUsed'], 'memSwapFree' : memory['swapFree']})
		
		payloadHash = md5.new(payload).hexdigest()
		postBackData = urllib.urlencode({'payload' : payload, 'hash' : payloadHash})

		self.doPostBack(postBackData)
		
		self.checksLogger.debug('Rescheduling checks')
		sc.enter(self.CHECK_FREQUENCY, 1, self.doChecks, (sc,))	
