import httplib
import traceback
import urllib2
import re

class Apache(object):
	def check(self, logger, agentConfig, headers):
		logger.debug('getApacheStatus: start')
		
		if 'apacheStatusUrl' in agentConfig and agentConfig['apacheStatusUrl'] != 'http://www.example.com/server-status/?auto':	# Don't do it if the status URL hasn't been provided
			logger.debug('getApacheStatus: config set')
			
			try: 
				logger.debug('getApacheStatus: attempting urlopen')
				
				req = urllib2.Request(agentConfig['apacheStatusUrl'], None, headers)
				request = urllib2.urlopen(req)
				response = request.read()
				
			except urllib2.HTTPError, e:
				logger.error('Unable to get Apache status - HTTPError = ' + str(e))
				return False
				
			except urllib2.URLError, e:
				logger.error('Unable to get Apache status - URLError = ' + str(e))
				return False
				
			except httplib.HTTPException, e:
				logger.error('Unable to get Apache status - HTTPException = ' + str(e))
				return False
				
			except Exception, e:
				logger.error('Unable to get Apache status - Exception = ' + traceback.format_exc())
				return False
				
			logger.debug('getApacheStatus: urlopen success, start parsing')
			
			# Split out each line
			lines = response.split('\n')
			
			# Loop over each line and get the values
			apacheStatus = {}
			
			logger.debug('getApacheStatus: parsing, loop')
			
			# Loop through and extract the numerical values
			for line in lines:
				values = line.split(': ')
				
				try:
					apacheStatus[str(values[0])] = values[1]
					
				except IndexError:
					break
			
			logger.debug('getApacheStatus: parsed')
			
			try:
				if apacheStatus['ReqPerSec'] != False and apacheStatus['BusyWorkers'] != False and apacheStatus['IdleWorkers'] != False:
					logger.debug('getApacheStatus: completed, returning')
					
					return {'reqPerSec': apacheStatus['ReqPerSec'], 'busyWorkers': apacheStatus['BusyWorkers'], 'idleWorkers': apacheStatus['IdleWorkers']}
				
				else:
					logger.debug('getApacheStatus: completed, status not available')
					
					return False
				
			# Stops the agent crashing if one of the apacheStatus elements isn't set (e.g. ExtendedStatus Off)	
			except IndexError:
				logger.debug('getApacheStatus: IndexError - ReqPerSec, BusyWorkers or IdleWorkers not present')
				
			except KeyError:
				logger.debug('getApacheStatus: IndexError - KeyError, BusyWorkers or IdleWorkers not present')
								
				return False
			
		else:
			logger.debug('getApacheStatus: config not set')
			
			return False        
			
class Nginx(object):
	def __init__(self):
		self.nginxRequestsStore = None
	
	def check(self, logger, agentConfig, headers):
		logger.debug('getNginxStatus: start')
		
		if 'nginxStatusUrl' in agentConfig and agentConfig['nginxStatusUrl'] != 'http://www.example.com/nginx_status':	# Don't do it if the status URL hasn't been provided
			logger.debug('getNginxStatus: config set')
			
			try: 
				logger.debug('getNginxStatus: attempting urlopen')
				
				req = urllib2.Request(agentConfig['nginxStatusUrl'], None, headers)

				# Do the request, log any errors
				request = urllib2.urlopen(req)
				response = request.read()
				
			except urllib2.HTTPError, e:
				logger.error('Unable to get Nginx status - HTTPError = ' + str(e))
				return False
				
			except urllib2.URLError, e:
				logger.error('Unable to get Nginx status - URLError = ' + str(e))
				return False
				
			except httplib.HTTPException, e:
				logger.error('Unable to get Nginx status - HTTPException = ' + str(e))
				return False
				
			except Exception, e:
				import traceback
				logger.error('Unable to get Nginx status - Exception = ' + traceback.format_exc())
				return False
				
			logger.debug('getNginxStatus: urlopen success, start parsing')
			
			# Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code
			
			logger.debug('getNginxStatus: parsing connections')
			
			# Connections
			parsed = re.search(r'Active connections:\s+(\d+)', response)
			connections = int(parsed.group(1))
			
			logger.debug('getNginxStatus: parsed connections')
			logger.debug('getNginxStatus: parsing reqs')
			
			# Requests per second
			parsed = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', response)
			requests = int(parsed.group(3))
			
			logger.debug('getNginxStatus: parsed reqs')
			
			if self.nginxRequestsStore == None or self.nginxRequestsStore < 0:
				
				logger.debug('getNginxStatus: no reqs so storing for first time')
				
				self.nginxRequestsStore = requests
				
				requestsPerSecond = 0
				
			else:
				
				logger.debug('getNginxStatus: reqs stored so calculating')
				logger.debug('getNginxStatus: self.nginxRequestsStore = ' + str(self.nginxRequestsStore))
				logger.debug('getNginxStatus: requests = ' + str(requests))
				
				requestsPerSecond = float(requests - self.nginxRequestsStore) / 60
				
				logger.debug('getNginxStatus: requestsPerSecond = ' + str(requestsPerSecond))
				
				self.nginxRequestsStore = requests
			
			if connections != None and requestsPerSecond != None:
			
				logger.debug('getNginxStatus: returning with data')
				
				return {'connections' : connections, 'reqPerSec' : requestsPerSecond}
			
			else:
			
				logger.debug('getNginxStatus: returning without data')
				
				return False
			
		else:
			logger.debug('getNginxStatus: config not set')
			
			return False
		
