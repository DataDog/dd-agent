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
# http://stackoverflow.com/questions/1052589/how-can-i-parse-the-output-of-proc-net-dev-into-keyvalue-pairs-per-interface-us

# Core modules
import httplib # Used only for handling httplib.HTTPException (case #26701)
import logging
import logging.handlers
import md5 # I know this is depreciated, but we still support Python 2.4 and hashlib is only in 2.5. Case 26918
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
		self.networkTrafficStore = {}
		
	def getApacheStatus(self):
		self.checksLogger.debug('getApacheStatus: start')
		
		if self.agentConfig['apacheStatusUrl'] != 'http://www.example.com/server-status/?auto':	# Don't do it if the status URL hasn't been provided
			self.checksLogger.debug('getApacheStatus: config set')
			
			try: 
				self.checksLogger.debug('getApacheStatus: attempting urlopen')
				
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
				
			self.checksLogger.debug('getApacheStatus: urlopen success, start parsing')
			
			# Split out each line
			lines = response.split('\n')
			
			# Loop over each line and get the values
			apacheStatus = {}
			
			self.checksLogger.debug('getApacheStatus: parsing, loop')
			
			# Loop through and extract the numerical values
			for line in lines:
				values = line.split(': ')
				
				try:
					apacheStatus[str(values[0])] = values[1]
					
				except IndexError:
					break
			
			self.checksLogger.debug('getApacheStatus: parsed')
			
			try:
				if apacheStatus['ReqPerSec'] != False and apacheStatus['BusyWorkers'] != False and apacheStatus['IdleWorkers'] != False:
					self.checksLogger.debug('getApacheStatus: completed, returning')
					
					return {'reqPerSec': apacheStatus['ReqPerSec'], 'busyWorkers': apacheStatus['BusyWorkers'], 'idleWorkers': apacheStatus['IdleWorkers']}
				
				else:
					self.checksLogger.debug('getApacheStatus: completed, status not available')
					
					return False
				
			# Stops the agent crashing if one of the apacheStatus elements isn't set (e.g. ExtendedStatus Off)	
			except IndexError:
				self.checksLogger.debug('getApacheStatus: IndexError - ReqPerSec, BusyWorkers or IdleWorkers not present')
				
			except KeyError:
				self.checksLogger.debug('getApacheStatus: IndexError - KeyError, BusyWorkers or IdleWorkers not present')
								
				return False
			
		else:
			self.checksLogger.debug('getApacheStatus: config not set')
			
			return False
		
	def getDiskUsage(self):
		self.checksLogger.debug('getDiskUsage: start')
		
		# Memory logging (case 27152)
		if self.agentConfig['debugMode'] and sys.platform == 'linux2':
			mem = subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
			self.checksLogger.debug('getDiskUsage: memory before Popen - ' + str(mem))
		
		# Get output from df
		try:
			self.checksLogger.debug('getDiskUsage: attempting Popen')
			
			df = subprocess.Popen(['df', '-ak'], stdout=subprocess.PIPE, close_fds=True).communicate()[0] # -k option uses 1024 byte blocks so we can calculate into MB
			
		except Exception, e:
			import traceback
			self.checksLogger.error('getDiskUsage: exception = ' + traceback.format_exc())
			return False
		
		# Memory logging (case 27152)
		if self.agentConfig['debugMode'] and sys.platform == 'linux2':
			mem = subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
			self.checksLogger.debug('getDiskUsage: memory after Popen - ' + str(mem))
		
		self.checksLogger.debug('getDiskUsage: Popen success, start parsing')
			
		# Split out each volume
		volumes = df.split('\n')
		
		self.checksLogger.debug('getDiskUsage: parsing, split')
		
		# Remove first (headings) and last (blank)
		volumes.pop(0)
		volumes.pop()
		
		self.checksLogger.debug('getDiskUsage: parsing, pop')
		
		usageData = []
		
		regexp = re.compile(r'([0-9]+)')
		
		previous_volume = ''
		
		self.checksLogger.debug('getDiskUsage: parsing, start loop')

		for volume in volumes:
			volume = (previous_volume + volume).split(None, 10)
			
			# Handle df output wrapping onto multiple lines (case 27078)
			# Thanks to http://github.com/sneeu
			if len(volume) == 1:
				previous_volume = volume[0]
				continue
			else:
				previous_volume = ''
			
			# Sometimes the first column will have a space, which is usually a system line that isn't relevant
			# e.g. map -hosts              0         0          0   100%    /net
			# so we just get rid of it
			if re.match(regexp, volume[1]) == None:
				
				pass
				
			else:			
				try:
					volume[2] = int(volume[2]) / 1024 / 1024 # Used
					volume[3] = int(volume[3]) / 1024 / 1024 # Available
				except IndexError:
					self.checksLogger.debug('getDiskUsage: parsing, loop IndexError - Used or Available not present')
					
				except KeyError:
					self.checksLogger.debug('getDiskUsage: parsing, loop KeyError - Used or Available not present')
				
				usageData.append(volume)
		
		self.checksLogger.debug('getDiskUsage: completed, returning')
			
		return usageData
	
	def getLoadAvrgs(self):
		self.checksLogger.debug('getLoadAvrgs: start')
		
		if sys.platform == 'linux2':
			self.checksLogger.debug('getLoadAvrgs: linux2')
			
			try:
				self.checksLogger.debug('getLoadAvrgs: attempting open')
				
				loadAvrgProc = open('/proc/loadavg', 'r')
				uptime = loadAvrgProc.readlines()
				
			except IOError, e:
				self.checksLogger.error('getLoadAvrgs: exception = ' + str(e))
				return False
			
			self.checksLogger.debug('getLoadAvrgs: open success')
				
			loadAvrgProc.close()
			
			uptime = uptime[0] # readlines() provides a list but we want a string
			
		elif sys.platform == 'darwin':
			self.checksLogger.debug('getLoadAvrgs: darwin')
			
			# Get output from uptime
			try:
				self.checksLogger.debug('getLoadAvrgs: attempting Popen')
				
				uptime = subprocess.Popen(['uptime'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
				
			except Exception, e:
				import traceback
				self.checksLogger.error('getLoadAvrgs: exception = ' + traceback.format_exc())
				return False
				
			self.checksLogger.debug('getLoadAvrgs: Popen success')
		
		self.checksLogger.debug('getLoadAvrgs: parsing')
				
		# Split out the 3 load average values
		loadAvrgs = re.findall(r'([0-9]+\.\d+)', uptime)
		loadAvrgs = {'1': loadAvrgs[0], '5': loadAvrgs[1], '15': loadAvrgs[2]}	
	
		self.checksLogger.debug('getLoadAvrgs: completed, returning')
	
		return loadAvrgs
		
	def getMemoryUsage(self):
		self.checksLogger.debug('getMemoryUsage: start')
		
		if sys.platform == 'linux2':
			self.checksLogger.debug('getMemoryUsage: linux2')
			
			try:
				self.checksLogger.debug('getMemoryUsage: attempting open')
				
				meminfoProc = open('/proc/meminfo', 'r')
				lines = meminfoProc.readlines()
				
			except IOError, e:
				self.checksLogger.error('getMemoryUsage: exception = ' + str(e))
				return False
				
			meminfoProc.close()
			
			self.checksLogger.debug('getMemoryUsage: open success, parsing')
			
			regexp = re.compile(r'([0-9]+)') # We run this several times so one-time compile now
			
			meminfo = {}
			
			self.checksLogger.debug('getMemoryUsage: parsing, looping')
			
			# Loop through and extract the numerical values
			for line in lines:
				values = line.split(':')
				
				try:
					# Picks out the key (values[0]) and makes a list with the value as the meminfo value (values[1])
					# We are only interested in the KB data so regexp that out
					match = re.search(regexp, values[1])
	
					if match != None:
						meminfo[str(values[0])] = match.group(0)
					
				except IndexError:
					break
					
			self.checksLogger.debug('getMemoryUsage: parsing, looped')
			
			memData = {}
			
			# Phys
			try:
				self.checksLogger.debug('getMemoryUsage: formatting (phys)')
				
				physTotal = int(meminfo['MemTotal'])
				physFree = int(meminfo['MemFree'])
				physUsed = physTotal - physFree
				
				# Convert to MB
				memData['physFree'] = physFree / 1024
				memData['physUsed'] = physUsed / 1024
				memData['cached'] = int(meminfo['Cached']) / 1024
								
			# Stops the agent crashing if one of the meminfo elements isn't set
			except IndexError:
				self.checksLogger.debug('getMemoryUsage: formatting (phys) IndexError - Cached, MemTotal or MemFree not present')
				
			except KeyError:
				self.checksLogger.debug('getMemoryUsage: formatting (phys) KeyError - Cached, MemTotal or MemFree not present')
			
			self.checksLogger.debug('getMemoryUsage: formatted (phys)')
			
			# Swap
			try:
				self.checksLogger.debug('getMemoryUsage: formatting (swap)')
				
				swapTotal = int(meminfo['SwapTotal'])
				swapFree = int(meminfo['SwapFree'])
				swapUsed = swapTotal - swapFree
				
				# Convert to MB
				memData['swapFree'] = swapFree / 1024
				memData['swapUsed'] = swapUsed / 1024
								
			# Stops the agent crashing if one of the meminfo elements isn't set
			except IndexError:
				self.checksLogger.debug('getMemoryUsage: formatting (swap) IndexErro) - SwapTotal or SwapFree not present')
				
			except KeyError:
				self.checksLogger.debug('getMemoryUsage: formatting (swap) KeyError - SwapTotal or SwapFree not present')
			
			self.checksLogger.debug('getMemoryUsage: formatted (swap), completed, returning')
			
			return memData	
				
		elif sys.platform == 'darwin':
			self.checksLogger.debug('getMemoryUsage: darwin')
			
			try:
				self.checksLogger.debug('getMemoryUsage: attempting Popen (top)')				
				top = subprocess.Popen(['top', '-l 1'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
				
				self.checksLogger.debug('getMemoryUsage: attempting Popen (sysctl)')
				sysctl = subprocess.Popen(['sysctl', 'vm.swapusage'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
				
			except Exception, e:
				import traceback
				self.checksLogger.error('getMemoryUsage: exception = ' + traceback.format_exc())
				return False
			
			self.checksLogger.debug('getMemoryUsage: Popen success, parsing')
			
			# Deal with top			
			lines = top.split('\n')
			physParts = re.findall(r'([0-9]\d+)', lines[5])
			
			self.checksLogger.debug('getMemoryUsage: parsed top')
			
			# Deal with sysctl
			swapParts = re.findall(r'([0-9]+\.\d+)', sysctl)
			
			self.checksLogger.debug('getMemoryUsage: parsed sysctl, completed, returning')
			
			return {'physUsed' : physParts[3], 'physFree' : physParts[4], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2], 'cached' : 'NULL'}	
					
		else:
			return False
			
	def getNetworkTraffic(self):
		self.checksLogger.debug('getNetworkTraffic: start')
		
		if sys.platform == 'linux2':
			self.checksLogger.debug('getNetworkTraffic: linux2')
			
			try:
				self.checksLogger.debug('getNetworkTraffic: attempting open')
				
				proc = open('/proc/net/dev', 'r')
				lines = proc.readlines()
				
			except IOError, e:
				self.checksLogger.error('getNetworkTraffic: exception = ' + str(e))
				return False
			
			proc.close()
			
			self.checksLogger.debug('getNetworkTraffic: open success, parsing')
			
			columnLine = lines[1]
			_, receiveCols , transmitCols = columnLine.split('|')
			receiveCols = map(lambda a:'recv_' + a, receiveCols.split())
			transmitCols = map(lambda a:'trans_' + a, transmitCols.split())
			
			cols = receiveCols + transmitCols
			
			self.checksLogger.debug('getNetworkTraffic: parsing, looping')
			
			faces = {}
			for line in lines[2:]:
				if line.find(':') < 0: continue
				face, data = line.split(':')
				faceData = dict(zip(cols, data.split()))
				faces[face] = faceData
			
			self.checksLogger.debug('getNetworkTraffic: parsed, looping')
			
			interfaces = {}
			
			# Now loop through each interface
			for face in faces:
				key = face.strip()
				
				# We need to work out the traffic since the last check so first time we store the current value
				# then the next time we can calculate the difference
				if key in self.networkTrafficStore:
					interfaces[key] = {}
					interfaces[key]['recv_bytes'] = long(faces[face]['recv_bytes']) - long(self.networkTrafficStore[key]['recv_bytes'])
					interfaces[key]['trans_bytes'] = long(faces[face]['trans_bytes']) - long(self.networkTrafficStore[key]['trans_bytes'])
					
					interfaces[key]['recv_bytes'] = str(interfaces[key]['recv_bytes'])
					interfaces[key]['trans_bytes'] = str(interfaces[key]['trans_bytes'])
					
					# And update the stored value to subtract next time round
					self.networkTrafficStore[key]['recv_bytes'] = faces[face]['recv_bytes']
					self.networkTrafficStore[key]['trans_bytes'] = faces[face]['trans_bytes']
					
				else:
					self.networkTrafficStore[key] = {}
					self.networkTrafficStore[key]['recv_bytes'] = faces[face]['recv_bytes']
					self.networkTrafficStore[key]['trans_bytes'] = faces[face]['trans_bytes']
		
			self.checksLogger.debug('getNetworkTraffic: completed, returning')
					
			return interfaces
		
		else:		
			self.checksLogger.debug('getNetworkTraffic: other platform, returning')
		
			return False
		
	def getProcesses(self):
		self.checksLogger.debug('getProcesses: start')
		
		# Memory logging (case 27152)
		if self.agentConfig['debugMode'] and sys.platform == 'linux2':
			mem = subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
			self.checksLogger.debug('getProcesses: memory before Popen - ' + str(mem))
		
		# Get output from ps
		try:
			self.checksLogger.debug('getProcesses: attempting Popen')
			
			ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
			
		except Exception, e:
			import traceback
			self.checksLogger.error('getProcesses: exception = ' + traceback.format_exc())
			return False
		
		self.checksLogger.debug('getProcesses: Popen success, parsing')
		
		# Memory logging (case 27152)
		if self.agentConfig['debugMode'] and sys.platform == 'linux2':
			mem = subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
			self.checksLogger.debug('getProcesses: memory after Popen - ' + str(mem))
		
		# Split out each process
		processLines = ps.split('\n')
		
		del processLines[0] # Removes the headers
		processLines.pop() # Removes a trailing empty line
		
		processes = []
		
		self.checksLogger.debug('getProcesses: Popen success, parsing, looping')
		
		for line in processLines:
			line = line.split(None, 10)
			processes.append(line)
		
		self.checksLogger.debug('getProcesses: completed, returning')
			
		return processes
		
	def doPostBack(self, postBackData):
		self.checksLogger.debug('doPostBack: start')	
		
		try: 
			self.checksLogger.debug('doPostBack: attempting postback: ' + self.agentConfig['sdUrl'])
			
			# Build the request handler
			request = urllib2.Request(self.agentConfig['sdUrl'] + '/postback/', postBackData, { 'User-Agent' : 'Server Density Agent' })
			
			# Do the request, log any errors
			response = urllib2.urlopen(request)
			
			if self.agentConfig['debugMode']:
				print response.read()
				
		except urllib2.HTTPError, e:
			self.checksLogger.error('doPostBack: HTTPError = ' + str(e))
			return False
			
		except urllib2.URLError, e:
			self.checksLogger.error('doPostBack: URLError = ' + str(e))
			return False
			
		except httplib.HTTPException, e: # Added for case #26701
			self.checksLogger.error('doPostBack: HTTPException')
			return False
				
		except Exception, e:
			import traceback
			self.checksLogger.error('doPostBack: Exception = ' + traceback.format_exc())
			return False
			
		self.checksLogger.debug('doPostBack: completed')
	
	def doChecks(self, sc, firstRun, systemStats=False):
		self.checksLogger = logging.getLogger('checks')
		
		self.checksLogger.debug('doChecks: start')
				
		# Do the checks
		apacheStatus = self.getApacheStatus()
		diskUsage = self.getDiskUsage()
		loadAvrgs = self.getLoadAvrgs()
		memory = self.getMemoryUsage()
		networkTraffic = self.getNetworkTraffic()
		processes = self.getProcesses()		
		
		self.checksLogger.debug('doChecks: checks success, build payload')
		
		checksData = {'agentKey' : self.agentConfig['agentKey'], 'agentVersion' : self.agentConfig['version'], 'diskUsage' : diskUsage, 'loadAvrg' : loadAvrgs['1'], 'memPhysUsed' : memory['physUsed'], 'memPhysFree' : memory['physFree'], 'memSwapUsed' : memory['swapUsed'], 'memSwapFree' : memory['swapFree'], 'memCached' : memory['cached'], 'networkTraffic' : networkTraffic, 'processes' : processes}
		
		self.checksLogger.debug('doChecks: payload built, build optional payloads')
		
		# Apache Status
		if apacheStatus != False:			
			checksData['apacheReqPerSec'] = apacheStatus['reqPerSec']
			checksData['apacheBusyWorkers'] = apacheStatus['busyWorkers']
			checksData['apacheIdleWorkers'] = apacheStatus['idleWorkers']
			
			self.checksLogger.debug('doChecks: built optional payload apacheStatus')
			
		# Include system stats on first postback
		if firstRun == True:
			checksData['systemStats'] = systemStats
			self.checksLogger.debug('doChecks: built optional payload systemStats')
		
		self.checksLogger.debug('doChecks: payloads built, convert to json')
		
		# Post back the data
		if int(pythonVersion[1]) >= 6:
			self.checksLogger.debug('doChecks: json convert')
			
			payload = json.dumps(checksData)
		
		else:
			self.checksLogger.debug('doChecks: minjson convert')
			
			payload = minjson.write(checksData)
			
		self.checksLogger.debug('doChecks: json converted, hash')
		
		payloadHash = md5.new(payload).hexdigest()
		postBackData = urllib.urlencode({'payload' : payload, 'hash' : payloadHash})

		self.checksLogger.debug('doChecks: hashed, doPostBack')

		self.doPostBack(postBackData)
		
		self.checksLogger.debug('doChecks: posted back, reschedule')
		
		sc.enter(self.agentConfig['checkFreq'], 1, self.doChecks, (sc, False))	