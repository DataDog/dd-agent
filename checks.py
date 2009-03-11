'''
	Server Density
	www.serverdensity.com
	----
	A web based server resource monitoring application

	(C) Boxed Ice 2009 all rights reserved
'''

# Core modules
import logging
import logging.handlers
import re
import subprocess
import sys
import urllib
import urllib2

class checks:
	
	def __init__(self, SD_URL, AGENT_KEY, CHECK_FREQUENCY):
		self.SD_URL = SD_URL
		self.AGENT_KEY = AGENT_KEY
		self.CHECK_FREQUENCY = CHECK_FREQUENCY
	
	def getDf(self):
		# CURRENTLY UNUSED
		
		# Get output from df
		df = subprocess.Popen(['df'], stdout=subprocess.PIPE).communicate()[0]
		
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
		uptime = subprocess.Popen(['uptime'], stdout=subprocess.PIPE).communicate()[0]
		
		# Split out the 3 load average values (we actually only use the 5 min average)
		loadAvrgs = re.findall(r'([0-9]\.\d+)', uptime)
		
		self.checksLogger.debug('Got loadAvrgs - ' + uptime)
	
		return loadAvrgs # We only use loadAvrgs[0] but may use more in the future, so return all
		
	def getMemoryUsage(self):
		self.checksLogger.debug('Getting memoryUsage')
		
		# See http://stackoverflow.com/questions/446209/possible-values-from-sys-platform/446210#446210 for possible
		# sys.platform values
		if sys.platform == 'linux2':
			self.checksLogger.debug('memoryUsage - linux2')
			
			free = subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE).communicate()[0]
			
			lines = free.split('\n')
			physParts = re.findall(r'([0-9]+)', lines[1])
			swapParts = re.findall(r'([0-9]+)', lines[3])
			
			self.checksLogger.debug('Got memoryUsage, returning')
			
			return {'physUsed' : physParts[2], 'physFree' : physParts[3], 'swapUsed' : swapParts[2], 'swapFree' : swapParts[3]}			
		elif sys.platform == 'darwin':
			self.checksLogger.debug('memoryUsage - darwin')
			
			top = subprocess.Popen(['top', '-l 1'], stdout=subprocess.PIPE).communicate()[0]
			sysctl = subprocess.Popen(['sysctl', 'vm.swapusage'], stdout=subprocess.PIPE).communicate()[0]
			
			# Deal with top			
			lines = top.split('\n')
			physParts = re.findall(r'([0-9]\d+)', lines[5])
			
			# Deal with sysctl
			swapParts = re.findall(r'([0-9]+\.\d+)', sysctl)
			
			self.checksLogger.debug('Got memoryUsage, returning')
		
			return {'physUsed' : physParts[3], 'physFree' : physParts[4], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2]}			
		else:
			return false
		
	def getProcessCount(self):
		self.checksLogger.debug('Getting process count')
		
		# Get output from ps
		ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
		
		# Split out each process
		processes = ps.split('\n')
		
		# Loop through each process and increment count
		i = 0
		
		for process in processes:
			i = i + 1
		
		self.checksLogger.debug('Got process count - ' + str(i))
			
		return i
		
	def doPostBack(self, postBackData):
		self.checksLogger.debug('Doing postback to ' + self.SD_URL)
		
		# Build the request handler
		request = urllib2.Request(self.SD_URL + '/postback/', postBackData, { 'User-Agent' : 'Server Density Agent' })
		
		# Do the request, log any errors
		try: 
			response = urllib2.urlopen(request)
		except urllib2.HTTPError, e:
			self.checksLogger.error('Unable to postback - HTTPError = ' + str(e.code))
		except urllib2.URLError, e:
			self.checksLogger.error('Unable to postback - URLError = ' + str(e.reason))			
		
		self.checksLogger.debug('Posted back')
	
	def doChecks(self, sc):
		self.checksLogger = logging.getLogger('checks')
		
		self.checksLogger.debug('doChecks')
				
		# Do the checks
		loadAvrgs = self.getLoadAvrgs()
		processes = self.getProcessCount()
		memory = self.getMemoryUsage()
		
		self.checksLogger.debug('All checks done, now to post back')
		
		# Post back the data
		postBackData = urllib.urlencode({'agentKey' : self.AGENT_KEY, 'loadAvrg' : loadAvrgs[0], 'processCount' : processes, 'memPhysUsed' : memory['physUsed'], 'memPhysFree' : memory['physFree'], 'memSwapUsed' : memory['swapUsed'], 'memSwapFree' : memory['swapFree']})
		self.doPostBack(postBackData)
		
		self.checksLogger.debug('Rescheduling checks')
		sc.enter(self.CHECK_FREQUENCY, 1, self.doChecks, (sc,))	