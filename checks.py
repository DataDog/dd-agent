'''
	Server Density
	www.serverdensity.com
	----
	A web based server resource monitoring application

	Licensed under Simplified BSD License (see LICENSE)
	(C) Boxed Ice 2009 all rights reserved
'''

# SO references
# http://stackoverflow.com/questions/446209/possible-values-from-sys-platform/446210#446210
# http://stackoverflow.com/questions/682446/splitting-out-the-output-of-ps-using-python/682464#682464

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
	
	def __init__(self, agentConfig):
		self.agentConfig = agentConfig
		
	def getApacheStatus(self):
		self.checksLogger.debug('Getting apacheStatus')
		
		if self.agentConfig['apacheStatusUrl'] != 'http://www.example.com/server-status/?auto':	# Don't do it if the status URL hasn't been provided
			self.checksLogger.debug('Apache config value set')
			
			try: 
				request = urllib2.urlopen(self.agentConfig['apacheStatusUrl'])
				response = request.read()
				
			except urllib2.HTTPError, e:
				self.checksLogger.error('Unable to get Apache status - HTTPError = ' + str(e))
				return False
				
			except urllib2.URLError, e:
				self.checksLogger.error('Unable to get Apache status - URLError = ' + str(e))
				return False
				
			except httplib.HTTPException, e:
				self.checksLogger.error('Unable to get Apache status - HTTPException = ' + str(e))
				return False
				
			except Exception, e:
				import traceback
				self.checksLogger.error('Unable to get Apache status - Exception = ' + traceback.format_exc())
				return False
				
			self.checksLogger.debug('Got server response')
			
			# Split out each line
			lines = response.split('\n')
			
			# Loop over each line and get the values
			apacheStatus = {}
			
			self.checksLogger.debug('Looping over lines')
			
			# Loop through and extract the numerical values
			for line in lines:
				values = line.split(': ')
				
				try:
					apacheStatus[str(values[0])] = values[1]
					
				except IndexError:
					break
			
			self.checksLogger.debug('Done looping')
			
			try:
				if apacheStatus['ReqPerSec'] != False and apacheStatus['BusyWorkers'] != False and apacheStatus['IdleWorkers'] != False:
					self.checksLogger.debug('Returning statuses')
					
					return {'reqPerSec': apacheStatus['ReqPerSec'], 'busyWorkers': apacheStatus['BusyWorkers'], 'idleWorkers': apacheStatus['IdleWorkers']}
				
				else:
					self.checksLogger.debug('One of the statuses was empty')
					
					return False
				
			# Stops the agent crashing if one of the apacheStatus elements isn't set (e.g. ExtendedStatus Off)	
			except IndexError:
				self.checksLogger.debug('Apache status failed - ReqPerSec, BusyWorkers or IdleWorkers not present')
				
			except KeyError:
				self.checksLogger.debug('Apache status failed - ReqPerSec, BusyWorkers or IdleWorkers not present')
								
				return False
			
		else:
			self.checksLogger.debug('Apache config not set')
			
			return False
		
	def getDf(self):
		# CURRENTLY UNUSED
		
		# Get output from df
		try:
			df = subprocess.Popen(['df'], stdout=subprocess.PIPE).communicate()[0]
			
		except Exception, e:
			import traceback
			self.checksLogger.error('getDf - Exception = ' + traceback.format_exc())
			return False
			
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
		
		if sys.platform == 'linux2':
			self.checksLogger.debug('memoryUsage - linux2 - /proc/meminfo')
			
			try:
				loadAvrgProc = open('/proc/loadavg', 'r')
				uptime = loadAvrgProc.readlines()
				
			except IOError, e:
				self.checksLogger.error('getLoadAvrgs (linux2) - Exception = ' + str(e))
				return False
				
			loadAvrgProc.close()
			
			uptime = uptime[0] # readlines() provides a list but we want a string
			
		elif sys.platform == 'darwin':
			self.checksLogger.debug('memoryUsage - darwin - uptime')
			
			# Get output from uptime
			try:
				uptime = subprocess.Popen(['uptime'], stdout=subprocess.PIPE).communicate()[0]
				
			except Exception, e:
				import traceback
				self.checksLogger.error('getLoadAvrgs - Exception = ' + traceback.format_exc())
				return False
		
		self.checksLogger.debug('Got loadAvrgs - ' + uptime)
				
		# Split out the 3 load average values
		loadAvrgs = re.findall(r'([0-9]+\.\d+)', uptime)
		loadAvrgs = {'1': loadAvrgs[0], '5': loadAvrgs[1], '15': loadAvrgs[2]}	
	
		return loadAvrgs
		
	def getMemoryUsage(self):
		self.checksLogger.debug('Getting memoryUsage')
		
		if sys.platform == 'linux2':
			self.checksLogger.debug('memoryUsage - linux2 - /proc/meminfo')
			
			try:
				meminfoProc = open('/proc/meminfo', 'r')
				lines = meminfoProc.readlines()
				
			except IOError, e:
				self.checksLogger.error('getMemoryUsage (linux2) - Exception = ' + str(e))
				return False
				
			meminfoProc.close()
				
			self.checksLogger.debug('Looping over lines')
			
			regexp = re.compile(r'([0-9]+)') # We run this several times so one-time compile now
			
			meminfo = {}
			
			# Loop through and extract the numerical values
			for line in lines:
				values = line.split(':')
				
				try:
					# Picks out the key (values[0]) and makes a list with the value as the meminfo value (values[1])
					# We are only interested in the KB data so regexp that out
					meminfo[str(values[0])] = re.search(regexp, values[1]).group(0)
					
				except IndexError:
					break
					
			self.checksLogger.debug('Done looping')
			
			memData = {}
			
			# Phys
			try:
				self.checksLogger.debug('phys')
				
				physTotal = int(meminfo['MemTotal'])
				physFree = int(meminfo['MemFree'])
				physUsed = physTotal - physFree
				
				# Convert to MB
				memData['physFree'] = physFree / 1024
				memData['physUsed'] = physUsed / 1024
				
				self.checksLogger.debug('Phys Used: ' + str(memData['physUsed']) + ' / Free: ' + str(memData['physFree']))
				
			# Stops the agent crashing if one of the meminfo elements isn't set
			except IndexError:
				self.checksLogger.debug('/proc/meminfo failed (IndexError) - MemTotal or MemFree not present')
				
			except KeyError:
				self.checksLogger.debug('/proc/meminfo failed (KeyError) - MemTotal or MemFree not present')

			
			# Swap
			try:
				self.checksLogger.debug('swap')
				
				swapTotal = int(meminfo['SwapTotal'])
				swapFree = int(meminfo['SwapFree'])
				swapUsed = swapTotal - swapFree
				
				# Convert to MB
				memData['swapFree'] = swapFree / 1024
				memData['swapUsed'] = swapUsed / 1024
				
				self.checksLogger.debug('Swap Used: ' + str(memData['swapUsed']) + ' / Free: ' + str(memData['swapFree']))
				
			# Stops the agent crashing if one of the meminfo elements isn't set
			except IndexError:
				self.checksLogger.debug('/proc/meminfo failed (IndexError) - SwapTotal or SwapFree not present')
				
			except KeyError:
				self.checksLogger.debug('/proc/meminfo failed (KeyError) - SwapTotal or SwapFree not present')
			
			return memData	
				
		elif sys.platform == 'darwin':
			self.checksLogger.debug('memoryUsage - darwin - top/sysctl')
			
			try:
				top = subprocess.Popen(['top', '-l 1'], stdout=subprocess.PIPE).communicate()[0]
				sysctl = subprocess.Popen(['sysctl', 'vm.swapusage'], stdout=subprocess.PIPE).communicate()[0]
				
			except Exception, e:
				import traceback
				self.checksLogger.error('getMemoryUsage (darwin) - Exception = ' + traceback.format_exc())
				return False
			
			# Deal with top			
			lines = top.split('\n')
			physParts = re.findall(r'([0-9]\d+)', lines[5])
			
			# Deal with sysctl
			swapParts = re.findall(r'([0-9]+\.\d+)', sysctl)
			
			self.checksLogger.debug('Got memoryUsage - Phys ' + physParts[3] + ' / ' + physParts[4] + ' Swap ' + swapParts[1] + ' / ' + swapParts[2])
		
			return {'physUsed' : physParts[3], 'physFree' : physParts[4], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2]}	
					
		else:
			return False
		
	def getProcesses(self):
		self.checksLogger.debug('Getting processes')
		
		# Get output from ps
		try:
			ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
			
		except Exception, e:
			import traceback
			self.checksLogger.error('getProcessCount - Exception = ' + traceback.format_exc())
			return False
		
		self.checksLogger.debug('Got processes, now to split')
		
		# Split out each process
		processLines = ps.split('\n')
		
		del processLines[0] # Removes the headers
		processLines.pop() # Removes a trailing empty line
		
		processes = []
		
		for line in processLines:
			line = line.split(None, 10)
			processes.append(line)
			
		return processes
		
	def doPostBack(self, postBackData):
		self.checksLogger.debug('Doing postback to ' + self.agentConfig['sdUrl'])	
		
		try: 
			# Build the request handler
			request = urllib2.Request(self.agentConfig['sdUrl'] + '/postback/', postBackData, { 'User-Agent' : 'Server Density Agent' })
			
			# Do the request, log any errors
			response = urllib2.urlopen(request)
			
			if self.agentConfig['debugMode']:
				print response.read()
				
		except urllib2.HTTPError, e:
			self.checksLogger.error('Unable to postback - HTTPError = ' + str(e))
			return False
			
		except urllib2.URLError, e:
			self.checksLogger.error('Unable to postback - URLError = ' + str(e))
			return False
			
		except httplib.HTTPException, e: # Added for case #26701
			self.checksLogger.error('Unable to postback - HTTPException')
			return False
				
		except Exception, e:
			import traceback
			self.checksLogger.error('Unable to postback - Exception = ' + traceback.format_exc())
			return False
			
		self.checksLogger.debug('Posted back')
	
	def doChecks(self, sc):
		self.checksLogger = logging.getLogger('checks')
		
		self.checksLogger.debug('doChecks')
				
		# Do the checks
		loadAvrgs = self.getLoadAvrgs()
		processes = self.getProcesses()
		memory = self.getMemoryUsage()
		apacheStatus = self.getApacheStatus()
		
		self.checksLogger.debug('All checks done, now to post back')
		
		checksData = {'agentKey' : self.agentConfig['agentKey'], 'agentVersion' : self.agentConfig['version'], 'loadAvrg' : loadAvrgs['1'], 'processes' : processes, 'memPhysUsed' : memory['physUsed'], 'memPhysFree' : memory['physFree'], 'memSwapUsed' : memory['swapUsed'], 'memSwapFree' : memory['swapFree']}
		
		# Apache Status
		if apacheStatus != False:
			checksData['apacheReqPerSec'] = apacheStatus['reqPerSec']
			checksData['apacheBusyWorkers'] = apacheStatus['busyWorkers']
			checksData['apacheIdleWorkers'] = apacheStatus['idleWorkers']
		
		# Post back the data
		if int(pythonVersion[1]) >= 6:
			payload = json.dumps(checksData)
		
		else:
			payload = minjson.write(checksData)
		
		payloadHash = md5.new(payload).hexdigest()
		postBackData = urllib.urlencode({'payload' : payload, 'hash' : payloadHash})

		self.doPostBack(postBackData)
		
		self.checksLogger.debug('Rescheduling checks')
		sc.enter(self.agentConfig['checkFreq'], 1, self.doChecks, (sc,))	