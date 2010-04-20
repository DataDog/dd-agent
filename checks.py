'''
	Server Density
	www.serverdensity.com
	----
	A web based server resource monitoring application

	Licensed under Simplified BSD License (see LICENSE)
	(C) Boxed Ice 2010 all rights reserved
'''

# SO references
# http://stackoverflow.com/questions/446209/possible-values-from-sys-platform/446210#446210
# http://stackoverflow.com/questions/682446/splitting-out-the-output-of-ps-using-python/682464#682464
# http://stackoverflow.com/questions/1052589/how-can-i-parse-the-output-of-proc-net-dev-into-keyvalue-pairs-per-interface-us

# Core modules
import httplib # Used only for handling httplib.HTTPException (case #26701)
import logging
import logging.handlers
import os
import platform
import re
import subprocess
import sys
import urllib
import urllib2

try:
    from hashlib import md5
except ImportError: # Python < 2.5
    from md5 import new as md5

# We need to return the data using JSON. As of Python 2.6+, there is a core JSON
# module. We have a 2.4/2.5 compatible lib included with the agent but if we're
# on 2.6 or above, we should use the core module which will be faster
pythonVersion = platform.python_version_tuple()

# Build the request headers
headers = {
	'User-Agent': 'Server Density Agent',
	'Content-Type': 'application/x-www-form-urlencoded',
	'Accept': 'text/html, */*',
}

if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
	import json
else:
	import minjson

class checks:
	
	def __init__(self, agentConfig):
		self.agentConfig = agentConfig
		self.mysqlConnectionsStore = None
		self.mysqlCreatedTmpDiskTablesStore = None
		self.mysqlSlowQueriesStore = None
		self.mysqlTableLocksWaited = None
		self.networkTrafficStore = {}
		self.nginxRequestsStore = None
		self.mongoDBStore = {}
		self.plugins = None
		self.topIndex = 0
		self.os = None
		
	def getApacheStatus(self):
		self.checksLogger.debug('getApacheStatus: start')
		
		if self.agentConfig['apacheStatusUrl'] != 'http://www.example.com/server-status/?auto':	# Don't do it if the status URL hasn't been provided
			self.checksLogger.debug('getApacheStatus: config set')
			
			try: 
				self.checksLogger.debug('getApacheStatus: attempting urlopen')
				
				req = urllib2.Request(self.agentConfig['apacheStatusUrl'], None, headers)
				request = urllib2.urlopen(req)
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
			
			df = subprocess.Popen(['df', '-k'], stdout=subprocess.PIPE, close_fds=True).communicate()[0] # -k option uses 1024 byte blocks so we can calculate into MB
			
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
		loadAvrgs = [res.replace(',', '.') for res in re.findall(r'([0-9]+[\.,]\d+)', uptime)]
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
			physParts = re.findall(r'([0-9]\d+)', lines[self.topIndex])
			
			self.checksLogger.debug('getMemoryUsage: parsed top')
			
			# Deal with sysctl
			swapParts = re.findall(r'([0-9]+\.\d+)', sysctl)
			
			self.checksLogger.debug('getMemoryUsage: parsed sysctl, completed, returning')
			
			return {'physUsed' : physParts[3], 'physFree' : physParts[4], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2], 'cached' : 'NULL'}	
					
		else:
			return False
	
	def getMySQLStatus(self):
		self.checksLogger.debug('getMySQLStatus: start')
		
		if 'MySQLServer' in self.agentConfig and 'MySQLUser' in self.agentConfig and self.agentConfig['MySQLServer'] != '' and self.agentConfig['MySQLUser'] != '':
		
			self.checksLogger.debug('getMySQLStatus: config')
			
			# Try import MySQLdb - http://sourceforge.net/projects/mysql-python/files/
			try:
				import MySQLdb
			
			except ImportError, e:
				self.checksLogger.debug('getMySQLStatus: unable to import MySQLdb')
				return False
				
			# Connect
			try:
				db = MySQLdb.connect(self.agentConfig['MySQLServer'], self.agentConfig['MySQLUser'], self.agentConfig['MySQLPass'])
				
			except MySQLdb.OperationalError, message:
				
				self.checksLogger.debug('getMySQLStatus: MySQL connection error: ' + str(message))
				return False
			
			self.checksLogger.debug('getMySQLStatus: connected')
			
			self.checksLogger.debug('getMySQLStatus: getting Connections')
			
			# Connections
			try:
				cursor = db.cursor()
				cursor.execute('SHOW GLOBAL STATUS LIKE "Connections"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				self.checksLogger.debug('getMySQLStatus: MySQL query error when getting Connections: ' + str(message))
		
			if self.mysqlConnectionsStore == None:
				
				self.checksLogger.debug('getMySQLStatus: mysqlConnectionsStore unset storing for first time')
				
				self.mysqlConnectionsStore = result[1]
				
				connections = 0
				
			else:
		
				self.checksLogger.debug('getMySQLStatus: mysqlConnectionsStore set so calculating')
				self.checksLogger.debug('getMySQLStatus: self.mysqlConnectionsStore = ' + str(self.mysqlConnectionsStore))
				self.checksLogger.debug('getMySQLStatus: result = ' + str(result[1]))
				
				connections = float(float(result[1]) - float(self.mysqlConnectionsStore)) / 60
				
				self.mysqlConnectionsStore = result[1]
				
			self.checksLogger.debug('getMySQLStatus: connections = ' + str(connections))
			
			self.checksLogger.debug('getMySQLStatus: getting Connections - done')
			
			self.checksLogger.debug('getMySQLStatus: getting Created_tmp_disk_tables')
				
			# Created_tmp_disk_tables
			try:
				cursor = db.cursor()
				cursor.execute('SHOW GLOBAL STATUS LIKE "Created_tmp_disk_tables"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				self.checksLogger.debug('getMySQLStatus: MySQL query error when getting Created_tmp_disk_tables: ' + str(message))
		
			if self.mysqlCreatedTmpDiskTablesStore == None:
				
				self.checksLogger.debug('getMySQLStatus: mysqlCreatedTmpDiskTablesStore unset so storing for first time')
				
				self.mysqlCreatedTmpDiskTablesStore = result[1]
				
				createdTmpDiskTables = 0
				
			else:
		
				self.checksLogger.debug('getMySQLStatus: mysqlCreatedTmpDiskTablesStore set so calculating')
				self.checksLogger.debug('getMySQLStatus: self.mysqlCreatedTmpDiskTablesStore = ' + str(self.mysqlCreatedTmpDiskTablesStore))
				self.checksLogger.debug('getMySQLStatus: result = ' + str(result[1]))
				
				createdTmpDiskTables = float(float(result[1]) - float(self.mysqlCreatedTmpDiskTablesStore)) / 60
				
				self.mysqlCreatedTmpDiskTablesStore = result[1]
				
			self.checksLogger.debug('getMySQLStatus: createdTmpDiskTables = ' + str(createdTmpDiskTables))
			
			self.checksLogger.debug('getMySQLStatus: getting Created_tmp_disk_tables - done')
			
			self.checksLogger.debug('getMySQLStatus: getting Max_used_connections')
				
			# Max_used_connections
			try:
				cursor = db.cursor()
				cursor.execute('SHOW GLOBAL STATUS LIKE "Max_used_connections"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				self.checksLogger.debug('getMySQLStatus: MySQL query error when getting Max_used_connections: ' + str(message))
				
			maxUsedConnections = result[1]
			
			self.checksLogger.debug('getMySQLStatus: maxUsedConnections = ' + str(createdTmpDiskTables))
			
			self.checksLogger.debug('getMySQLStatus: getting Max_used_connections - done')
			
			self.checksLogger.debug('getMySQLStatus: getting Open_files')
			
			# Open_files
			try:
				cursor = db.cursor()
				cursor.execute('SHOW GLOBAL STATUS LIKE "Open_files"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				self.checksLogger.debug('getMySQLStatus: MySQL query error when getting Open_files: ' + str(message))
				
			openFiles = result[1]
			
			self.checksLogger.debug('getMySQLStatus: openFiles = ' + str(openFiles))
			
			self.checksLogger.debug('getMySQLStatus: getting Open_files - done')
			
			self.checksLogger.debug('getMySQLStatus: getting Slow_queries')
			
			# Slow_queries
			try:
				cursor = db.cursor()
				cursor.execute('SHOW GLOBAL STATUS LIKE "Slow_queries"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				self.checksLogger.debug('getMySQLStatus: MySQL query error when getting Slow_queries: ' + str(message))
		
			if self.mysqlSlowQueriesStore == None:
				
				self.checksLogger.debug('getMySQLStatus: mysqlSlowQueriesStore unset so storing for first time')
				
				self.mysqlSlowQueriesStore = result[1]
				
				slowQueries = 0
				
			else:
		
				self.checksLogger.debug('getMySQLStatus: mysqlSlowQueriesStore set so calculating')
				self.checksLogger.debug('getMySQLStatus: self.mysqlSlowQueriesStore = ' + str(self.mysqlSlowQueriesStore))
				self.checksLogger.debug('getMySQLStatus: result = ' + str(result[1]))
				
				slowQueries = float(float(result[1]) - float(self.mysqlSlowQueriesStore)) / 60
				
				self.mysqlSlowQueriesStore = result[1]
				
			self.checksLogger.debug('getMySQLStatus: slowQueries = ' + str(slowQueries))
			
			self.checksLogger.debug('getMySQLStatus: getting Slow_queries - done')
			
			self.checksLogger.debug('getMySQLStatus: getting Table_locks_waited')
				
			# Table_locks_waited
			try:
				cursor = db.cursor()
				cursor.execute('SHOW GLOBAL STATUS LIKE "Table_locks_waited"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				self.checksLogger.debug('getMySQLStatus: MySQL query error when getting Table_locks_waited: ' + str(message))
		
			if self.mysqlTableLocksWaited == None:
				
				self.checksLogger.debug('getMySQLStatus: mysqlTableLocksWaited unset so storing for first time')
				
				self.mysqlTableLocksWaited = result[1]
				
				tableLocksWaited = 0
				
			else:
		
				self.checksLogger.debug('getMySQLStatus: mysqlTableLocksWaited set so calculating')
				self.checksLogger.debug('getMySQLStatus: self.mysqlTableLocksWaited = ' + str(self.mysqlTableLocksWaited))
				self.checksLogger.debug('getMySQLStatus: result = ' + str(result[1]))
				
				tableLocksWaited = float(float(result[1]) - float(self.mysqlTableLocksWaited)) / 60
				
				self.mysqlTableLocksWaited = result[1]
				
			self.checksLogger.debug('getMySQLStatus: tableLocksWaited = ' + str(tableLocksWaited))
			
			self.checksLogger.debug('getMySQLStatus: getting Table_locks_waited - done')
			
			self.checksLogger.debug('getMySQLStatus: getting Threads_connected')
				
			# Threads_connected
			try:
				cursor = db.cursor()
				cursor.execute('SHOW GLOBAL STATUS LIKE "Threads_connected"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				self.checksLogger.debug('getMySQLStatus: MySQL query error when getting Threads_connected: ' + str(message))
				
			threadsConnected = result[1]
			
			self.checksLogger.debug('getMySQLStatus: threadsConnected = ' + str(threadsConnected))
			
			self.checksLogger.debug('getMySQLStatus: getting Threads_connected - done')
			
			self.checksLogger.debug('getMySQLStatus: getting Seconds_Behind_Master')
			
			# Seconds_Behind_Master
			try:
				cursor = db.cursor()
				cursor.execute('SHOW SLAVE STATUS')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				self.checksLogger.debug('getMySQLStatus: MySQL query error when getting SHOW SLAVE STATUS: ' + str(message))
			
			if result != None:
				try:
					secondsBehindMaster = result[28]
				
					self.checksLogger.debug('getMySQLStatus: secondsBehindMaster = ' + str(secondsBehindMaster))
					
				except IndexError, e:					
					secondsBehindMaster = None
					
					self.checksLogger.debug('getMySQLStatus: secondsBehindMaster empty')
			
			else:
				secondsBehindMaster = None
				
				self.checksLogger.debug('getMySQLStatus: secondsBehindMaster empty')
			
			self.checksLogger.debug('getMySQLStatus: getting Seconds_Behind_Master - done')
			
			return {'connections' : connections, 'createdTmpDiskTables' : createdTmpDiskTables, 'maxUsedConnections' : maxUsedConnections, 'openFiles' : openFiles, 'slowQueries' : slowQueries, 'tableLocksWaited' : tableLocksWaited, 'threadsConnected' : threadsConnected, 'secondsBehindMaster' : secondsBehindMaster}

		else:			
			
			self.checksLogger.debug('getMySQLStatus: config not set')
			return False
		
	
	def getNginxStatus(self):
		self.checksLogger.debug('getNginxStatus: start')
		
		if 'nginxStatusUrl' in self.agentConfig and self.agentConfig['nginxStatusUrl'] != 'http://www.example.com/nginx_status':	# Don't do it if the status URL hasn't been provided
			self.checksLogger.debug('getNginxStatus: config set')
			
			try: 
				self.checksLogger.debug('getNginxStatus: attempting urlopen')
				
				req = urllib2.Request(self.agentConfig['nginxStatusUrl'], None, headers)

				# Do the request, log any errors
				request = urllib2.urlopen(req)
				response = request.read()
				
			except urllib2.HTTPError, e:
				self.checksLogger.error('Unable to get Nginx status - HTTPError = ' + str(e))
				return False
				
			except urllib2.URLError, e:
				self.checksLogger.error('Unable to get Nginx status - URLError = ' + str(e))
				return False
				
			except httplib.HTTPException, e:
				self.checksLogger.error('Unable to get Nginx status - HTTPException = ' + str(e))
				return False
				
			except Exception, e:
				import traceback
				self.checksLogger.error('Unable to get Nginx status - Exception = ' + traceback.format_exc())
				return False
				
			self.checksLogger.debug('getNginxStatus: urlopen success, start parsing')
			
			# Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code
			
			self.checksLogger.debug('getNginxStatus: parsing connections')
			
			# Connections
			parsed = re.search(r'Active connections:\s+(\d+)', response)
			connections = int(parsed.group(1))
			
			self.checksLogger.debug('getNginxStatus: parsed connections')
			self.checksLogger.debug('getNginxStatus: parsing reqs')
			
			# Requests per second
			parsed = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', response)
			requests = int(parsed.group(3))
			
			self.checksLogger.debug('getNginxStatus: parsed reqs')
			
			if self.nginxRequestsStore == None:
				
				self.checksLogger.debug('getNginxStatus: no reqs so storing for first time')
				
				self.nginxRequestsStore = requests
				
				requestsPerSecond = 0
				
			else:
				
				self.checksLogger.debug('getNginxStatus: reqs stored so calculating')
				self.checksLogger.debug('getNginxStatus: self.nginxRequestsStore = ' + str(self.nginxRequestsStore))
				self.checksLogger.debug('getNginxStatus: requests = ' + str(requests))
				
				requestsPerSecond = float(requests - self.nginxRequestsStore) / 60
				
				self.checksLogger.debug('getNginxStatus: requestsPerSecond = ' + str(requestsPerSecond))
				
				self.nginxRequestsStore = requests
			
			if connections != None and requestsPerSecond != None:
			
				self.checksLogger.debug('getNginxStatus: returning with data')
				
				return {'connections' : connections, 'reqPerSec' : requestsPerSecond}
			
			else:
			
				self.checksLogger.debug('getNginxStatus: returning without data')
				
				return False
			
		else:
			self.checksLogger.debug('getNginxStatus: config not set')
			
			return False

	def getRabbitMQStatus(self):
		self.checksLogger.debug('getRabbitMQStatus: start')

		if 'rabbitMQStatusUrl' not in self.agentConfig or \
		   'rabbitMQUser' not in self.agentConfig or \
		   'rabbitMQPass' not in self.agentConfig or \
			self.agentConfig['rabbitMQStatusUrl'] == 'http://www.example.com:55672/json':

			self.checksLogger.debug('getRabbitMQStatus: config not set')
			return False

		self.checksLogger.debug('getRabbitMQStatus: config set')

		try:
			self.checksLogger.debug('getRabbitMQStatus: attempting authentication setup')
			manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
			manager.add_password(None, self.agentConfig['rabbitMQStatusUrl'], self.agentConfig['rabbitMQUser'], self.agentConfig['rabbitMQPass'])
			handler = urllib2.HTTPBasicAuthHandler(manager)
			opener = urllib2.build_opener(handler)
			urllib2.install_opener(opener)

			self.checksLogger.debug('getRabbitMQStatus: attempting urlopen')
			req = urllib2.Request(self.agentConfig['rabbitMQStatusUrl'], None, headers)

			# Do the request, log any errors
			request = urllib2.urlopen(req)
			response = request.read()

		except urllib2.HTTPError, e:
			self.checksLogger.error('Unable to get RabbitMQ status - HTTPError = ' + str(e))
			return False

		except urllib2.URLError, e:
			self.checksLogger.error('Unable to get RabbitMQ status - URLError = ' + str(e))
			return False

		except httplib.HTTPException, e:
			self.checksLogger.error('Unable to get RabbitMQ status - HTTPException = ' + str(e))
			return False

		except Exception, e:
			import traceback
			self.checksLogger.error('Unable to get RabbitMQ status - Exception = ' + traceback.format_exc())
			return False
			
		try:

			if int(pythonVersion[1]) >= 6:
				self.checksLogger.debug('getRabbitMQStatus: json read')
				status = json.loads(response)

			else:
				self.checksLogger.debug('getRabbitMQStatus: minjson read')
				status = minjson.safeRead(response)

		except Exception, e:
			import traceback
			self.checksLogger.error('Unable to load RabbitMQ status JSON - Exception = ' + traceback.format_exc())
			return False

		self.checksLogger.debug('getRabbitMQStatus: completed, returning')
		return status

	def getMongoDBStatus(self):
		self.checksLogger.debug('getMongoDBStatus: start')

		if 'MongoDBServer' not in self.agentConfig or self.agentConfig['MongoDBServer'] == '':
			self.checksLogger.debug('getMongoDBStatus: config not set')
			return False

		self.checksLogger.debug('getMongoDBStatus: config set')

		try:
			import pymongo
			from pymongo import Connection
		except ImportError:
			self.checksLogger.error('Unable to import pymongo library')
			return False

		# The dictionary to be returned.
		mongodb = {}

		try:
			conn = Connection(self.agentConfig['MongoDBServer'])
		except Exception, ex:
			import traceback
			self.checksLogger.error('Unable to connect to MongoDB server - Exception = ' + traceback.format_exc())
			return False

		# Older versions of pymongo did not support the command()
		# method below.
		try:
			for dbName in conn.database_names():
				db = conn[dbName]
				status = db.command('serverStatus') # Shorthand for {'serverStatus': 1}
				# If these keys exist, remove them for now as they cannot be serialized
				try:
					status['backgroundFlushing'].pop('last_finished')
				except KeyError:
					pass
				try:
					status.pop('localTime')
				except KeyError:
					pass

				if dbName not in self.mongoDBStore:
					self.checksLogger.debug('getMongoDBStatus: no cached data, so storing for first time')
					status['indexCounters']['btree']['accessesPS'] = 0
					status['indexCounters']['btree']['hitsPS'] = 0
					status['indexCounters']['btree']['missesPS'] = 0
					status['opcounters']['insertPS'] = 0
					status['opcounters']['queryPS'] = 0
					status['opcounters']['updatePS'] = 0
					status['opcounters']['deletePS'] = 0
					status['opcounters']['getmorePS'] = 0
					status['opcounters']['commandPS'] = 0
					status['asserts']['regularPS'] = 0
					status['asserts']['warningPS'] = 0
					status['asserts']['msgPS'] = 0
					status['asserts']['userPS'] = 0
					status['asserts']['rolloversPS'] = 0
				else:
					self.checksLogger.debug('getMongoDBStatus: cached data exists, so calculating per sec metrics')
					status['indexCounters']['btree']['accessesPS'] = float(status['indexCounters']['btree']['accesses'] - self.mongoDBStore[dbName]['indexCounters']['btree']['accesses']) / 60
					status['indexCounters']['btree']['hitsPS'] = float(status['indexCounters']['btree']['hits'] - self.mongoDBStore[dbName]['indexCounters']['btree']['hits']) / 60
					status['indexCounters']['btree']['missesPS'] = float(status['indexCounters']['btree']['misses'] - self.mongoDBStore[dbName]['indexCounters']['btree']['misses']) / 60
					status['opcounters']['insertPS'] = float(status['opcounters']['insert'] - self.mongoDBStore[dbName]['opcounters']['insert']) / 60
					status['opcounters']['queryPS'] = float(status['opcounters']['query'] - self.mongoDBStore[dbName]['opcounters']['query']) / 60
					status['opcounters']['updatePS'] = float(status['opcounters']['update'] - self.mongoDBStore[dbName]['opcounters']['update']) / 60
					status['opcounters']['deletePS'] = float(status['opcounters']['delete'] - self.mongoDBStore[dbName]['opcounters']['delete']) / 60
					status['opcounters']['getmorePS'] = float(status['opcounters']['getmore'] - self.mongoDBStore[dbName]['opcounters']['getmore']) / 60
					status['opcounters']['commandPS'] = float(status['opcounters']['command'] - self.mongoDBStore[dbName]['opcounters']['command']) / 60
					status['asserts']['regularPS'] = float(status['asserts']['regular'] - self.mongoDBStore[dbName]['asserts']['regular']) / 60
					status['asserts']['warningPS'] = float(status['asserts']['warning'] - self.mongoDBStore[dbName]['asserts']['warning']) / 60
					status['asserts']['msgPS'] = float(status['asserts']['msg'] - self.mongoDBStore[dbName]['asserts']['msg']) / 60
					status['asserts']['userPS'] = float(status['asserts']['user'] - self.mongoDBStore[dbName]['asserts']['user']) / 60
					status['asserts']['rolloversPS'] = float(status['asserts']['rollovers'] - self.mongoDBStore[dbName]['asserts']['rollovers']) / 60

				self.mongoDBStore[dbName] = status
				mongodb[dbName] = status
		except Exception, ex:
			import traceback
			self.checksLogger.error('Unable to get MongoDB status - Exception = ' + traceback.format_exc())
			return False

		self.checksLogger.debug('getMongoDBStatus: completed, returning')
		return mongodb

	def getCouchDBStatus(self):
		self.checksLogger.debug('getCouchDBStatus: start')

		if ('CouchDBServer' not in self.agentConfig or self.agentConfig['CouchDBServer'] == ''):
			self.checksLogger.debug('getCouchDBStatus: config not set')
			return False

		self.checksLogger.debug('getCouchDBStatus: config set')

		# The dictionary to be returned.
		couchdb = {'stats': None, 'databases': {}}

		# First, get overall statistics.
		endpoint = '/_stats/'

		try:
			url = '%s%s' % (self.agentConfig['CouchDBServer'], endpoint)
			self.checksLogger.debug('getCouchDBStatus: attempting urlopen')
			req = urllib2.Request(url, None, headers)

			# Do the request, log any errors
			request = urllib2.urlopen(req)
			response = request.read()
		except urllib2.HTTPError, e:
			self.checksLogger.error('Unable to get CouchDB statistics - HTTPError = ' + str(e))
			return False

		except urllib2.URLError, e:
			self.checksLogger.error('Unable to get CouchDB statistics - URLError = ' + str(e))
			return False

		except httplib.HTTPException, e:
			self.checksLogger.error('Unable to get CouchDB statistics - HTTPException = ' + str(e))
			return False

		except Exception, e:
			import traceback
			self.checksLogger.error('Unable to get CouchDB statistics - Exception = ' + traceback.format_exc())
			return False

		try:

			if int(pythonVersion[1]) >= 6:
				self.checksLogger.debug('getCouchDBStatus: json read')
				stats = json.loads(response)

			else:
				self.checksLogger.debug('getCouchDBStatus: minjson read')
				stats = minjson.safeRead(response)

		except Exception, e:
			import traceback
			self.checksLogger.error('Unable to load CouchDB database JSON - Exception = ' + traceback.format_exc())
			return False

		couchdb['stats'] = stats

		# Next, get all database names.
		endpoint = '/_all_dbs/'

		try:
			url = '%s%s' % (self.agentConfig['CouchDBServer'], endpoint)
			self.checksLogger.debug('getCouchDBStatus: attempting urlopen')
			req = urllib2.Request(url, None, headers)

			# Do the request, log any errors
			request = urllib2.urlopen(req)
			response = request.read()
		except urllib2.HTTPError, e:
			self.checksLogger.error('Unable to get CouchDB status - HTTPError = ' + str(e))
			return False

		except urllib2.URLError, e:
			self.checksLogger.error('Unable to get CouchDB status - URLError = ' + str(e))
			return False

		except httplib.HTTPException, e:
			self.checksLogger.error('Unable to get CouchDB status - HTTPException = ' + str(e))
			return False

		except Exception, e:
			import traceback
			self.checksLogger.error('Unable to get CouchDB status - Exception = ' + traceback.format_exc())
			return False

		try:

			if int(pythonVersion[1]) >= 6:
				self.checksLogger.debug('getCouchDBStatus: json read')
				databases = json.loads(response)

			else:
				self.checksLogger.debug('getCouchDBStatus: minjson read')
				databases = minjson.safeRead(response)

		except Exception, e:
			import traceback
			self.checksLogger.error('Unable to load CouchDB database JSON - Exception = ' + traceback.format_exc())
			return False

		for dbName in databases:
			endpoint = '/%s/' % dbName

			try:
				url = '%s%s' % (self.agentConfig['CouchDBServer'], endpoint)
				self.checksLogger.debug('getCouchDBStatus: attempting urlopen')
				req = urllib2.Request(url, None, headers)

				# Do the request, log any errors
				request = urllib2.urlopen(req)
				response = request.read()
			except urllib2.HTTPError, e:
				self.checksLogger.error('Unable to get CouchDB database status - HTTPError = ' + str(e))
				return False

			except urllib2.URLError, e:
				self.checksLogger.error('Unable to get CouchDB database status - URLError = ' + str(e))
				return False

			except httplib.HTTPException, e:
				self.checksLogger.error('Unable to get CouchDB database status - HTTPException = ' + str(e))
				return False

			except Exception, e:
				import traceback
				self.checksLogger.error('Unable to get CouchDB database status - Exception = ' + traceback.format_exc())
				return False

			try:

				if int(pythonVersion[1]) >= 6:
					self.checksLogger.debug('getCouchDBStatus: json read')
					couchdb['databases'][dbName] = json.loads(response)

				else:
					self.checksLogger.debug('getCouchDBStatus: minjson read')
					couchdb['databases'][dbName] = minjson.safeRead(response)

			except Exception, e:
				import traceback
				self.checksLogger.error('Unable to load CouchDB database JSON - Exception = ' + traceback.format_exc())
				return False

		self.checksLogger.debug('getCouchDBStatus: completed, returning')
		return couchdb

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
		
	def getPlugins(self):
		self.checksLogger.debug('getPlugins: start')
		
		if 'pluginDirectory' in self.agentConfig:
			if os.path.exists(self.agentConfig['pluginDirectory']) == False:
				self.checksLogger.debug('getPlugins: ' + self.agentConfig['pluginDirectory'] + ' directory does not exist')
				return False
		else:
			return False
		
		# Have we already imported the plugins?
		# Only load the plugins once
		if self.plugins == None:			
			self.checksLogger.debug('getPlugins: initial load from ' + self.agentConfig['pluginDirectory'])
			
			sys.path.append(self.agentConfig['pluginDirectory'])
			
			self.plugins = []
			plugins = []
			
			# Loop through all the plugin files
			for root, dirs, files in os.walk(self.agentConfig['pluginDirectory']):				
				for name in files:				
					self.checksLogger.debug('getPlugins: considering: ' + name)
				
					name = name.split('.')
					
					# Only pull in .py files (ignores others, inc .pyc files)
					try:
						if name[1] == 'py':
							
							self.checksLogger.debug('getPlugins: ' + name[0] + '.' + name[1] + ' is a plugin')
							
							plugins.append(name[0])
							
					except IndexError, e:
						
						continue
			
			# Loop through all the found plugins, import them then create new objects
			for pluginName in plugins:				
				self.checksLogger.debug('getPlugins: importing ' + pluginName)
				
				# Import the plugin, but only from the pluginDirectory (ensures no conflicts with other module names elsehwhere in the sys.path
				import imp
				importedPlugin = imp.load_source(pluginName, os.path.join(self.agentConfig['pluginDirectory'], '%s.py' % pluginName))
				
				self.checksLogger.debug('getPlugins: imported ' + pluginName)
				
				# Find out the class name and then instantiate it
				pluginClass = getattr(importedPlugin, pluginName)
				pluginObj = pluginClass()
				
				self.checksLogger.debug('getPlugins: instantiated ' + pluginName)
				
				# Store in class var so we can execute it again on the next cycle
				self.plugins.append(pluginObj)
		
		# Now execute the objects previously created
		if self.plugins != None:			
			self.checksLogger.debug('getPlugins: executing plugins')
			
			# Execute the plugins
			output = {}
					
			for plugin in self.plugins:				
				self.checksLogger.debug('getPlugins: executing ' + plugin.__class__.__name__)
				
				output[plugin.__class__.__name__] = plugin.run()
				
				self.checksLogger.debug('getPlugins: executed ' + plugin.__class__.__name__)
			
			self.checksLogger.debug('getPlugins: returning')
			
			# Each plugin should output a dictionary so we can convert it to JSON later	
			return output
			
		else:			
			self.checksLogger.debug('getPlugins: no plugins, returning false')
			
			return False
		
	def doPostBack(self, postBackData):
		self.checksLogger.debug('doPostBack: start')	
		
		try: 
			self.checksLogger.debug('doPostBack: attempting postback: ' + self.agentConfig['sdUrl'])
			
			# Build the request handler
			request = urllib2.Request(self.agentConfig['sdUrl'] + '/postback/', postBackData, headers)
			
			# Do the request, log any errors
			response = urllib2.urlopen(request)
			
			self.checksLogger.debug('doPostBack: postback response: ' + str(response.read()))
				
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
		macV = None
		if sys.platform == 'darwin':
			macV = platform.mac_ver()
		
		if not self.topIndex: # We cache the line index from which to read from top
			# Output from top is slightly modified on OS X 10.6 (case #28239)
			if macV and macV[0].startswith('10.6.'):
				self.topIndex = 6
			else:
				self.topIndex = 5
		
		if not self.os:
			if macV:
				self.os = 'mac'
			else:
				self.os = 'linux'
		
		self.checksLogger = logging.getLogger('checks')
		
		self.checksLogger.debug('doChecks: start')
		
		# Do the checks
		apacheStatus = self.getApacheStatus()
		diskUsage = self.getDiskUsage()
		loadAvrgs = self.getLoadAvrgs()
		memory = self.getMemoryUsage()
		mysqlStatus = self.getMySQLStatus()
		networkTraffic = self.getNetworkTraffic()
		nginxStatus = self.getNginxStatus()
		processes = self.getProcesses()
		rabbitmq = self.getRabbitMQStatus()
		mongodb = self.getMongoDBStatus()
		couchdb = self.getCouchDBStatus()
		plugins = self.getPlugins()
		
		self.checksLogger.debug('doChecks: checks success, build payload')
		
		checksData = {'os' : self.os, 'agentKey' : self.agentConfig['agentKey'], 'agentVersion' : self.agentConfig['version'], 'diskUsage' : diskUsage, 'loadAvrg' : loadAvrgs['1'], 'memPhysUsed' : memory['physUsed'], 'memPhysFree' : memory['physFree'], 'memSwapUsed' : memory['swapUsed'], 'memSwapFree' : memory['swapFree'], 'memCached' : memory['cached'], 'networkTraffic' : networkTraffic, 'processes' : processes}
		
		self.checksLogger.debug('doChecks: payload built, build optional payloads')
		
		# Apache Status
		if apacheStatus != False:			
			checksData['apacheReqPerSec'] = apacheStatus['reqPerSec']
			checksData['apacheBusyWorkers'] = apacheStatus['busyWorkers']
			checksData['apacheIdleWorkers'] = apacheStatus['idleWorkers']
			
			self.checksLogger.debug('doChecks: built optional payload apacheStatus')
		
		# MySQL Status
		if mysqlStatus != False:
			
			checksData['mysqlConnections'] = mysqlStatus['connections']
			checksData['mysqlCreatedTmpDiskTables'] = mysqlStatus['createdTmpDiskTables']
			checksData['mysqlMaxUsedConnections'] = mysqlStatus['maxUsedConnections']
			checksData['mysqlOpenFiles'] = mysqlStatus['openFiles']
			checksData['mysqlSlowQueries'] = mysqlStatus['slowQueries']
			checksData['mysqlTableLocksWaited'] = mysqlStatus['tableLocksWaited']
			checksData['mysqlThreadsConnected'] = mysqlStatus['threadsConnected']
			
			if mysqlStatus['secondsBehindMaster'] != None:
				checksData['mysqlSecondsBehindMaster'] = mysqlStatus['secondsBehindMaster']
		
		# Nginx Status
		if nginxStatus != False:
			checksData['nginxConnections'] = nginxStatus['connections']
			checksData['nginxReqPerSec'] = nginxStatus['reqPerSec']
			
		# RabbitMQ
		if rabbitmq != False:
			checksData['rabbitMQ'] = rabbitmq
		
		# MongoDB
		if mongodb != False:
			checksData['mongoDB'] = mongodb
			
		# CouchDB
		if couchdb != False:
			checksData['couchDB'] = couchdb
		
		# Plugins
		if plugins != False:
			checksData['plugins'] = plugins
			
		# Include system stats on first postback
		if firstRun == True:
			checksData['systemStats'] = systemStats
			self.checksLogger.debug('doChecks: built optional payload systemStats')
			
		# Include server indentifiers
		import socket	
		
		try:
			checksData['internalHostname'] = socket.gethostname()
			
		except socket.error, e:
			self.checksLogger.debug('Unable to get hostname: ' + str(e))
		
		self.checksLogger.debug('doChecks: payloads built, convert to json')
		
		# Post back the data
		if int(pythonVersion[1]) >= 6:
			self.checksLogger.debug('doChecks: json convert')
			
			payload = json.dumps(checksData)
		
		else:
			self.checksLogger.debug('doChecks: minjson convert')
			
			payload = minjson.write(checksData)
			
		self.checksLogger.debug('doChecks: json converted, hash')
		
		payloadHash = md5(payload).hexdigest()
		postBackData = urllib.urlencode({'payload' : payload, 'hash' : payloadHash})

		self.checksLogger.debug('doChecks: hashed, doPostBack')

		self.doPostBack(postBackData)
		
		self.checksLogger.debug('doChecks: posted back, reschedule')
		
		sc.enter(self.agentConfig['checkFreq'], 1, self.doChecks, (sc, False))	
