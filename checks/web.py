import httplib
import traceback
import urllib2
import re
import time
from util import headers

class Apache(object):
    def check(self, logger, agentConfig):
        if 'apacheStatusUrl' in agentConfig and agentConfig['apacheStatusUrl'] != 'http://www.example.com/server-status/?auto': # Don't do it if the status URL hasn't been provided
            
            try: 
                req = urllib2.Request(agentConfig['apacheStatusUrl'], None, headers(agentConfig))
                request = urllib2.urlopen(req)
                response = request.read()
                
            except:
                logger.exception('Unable to get Apache status')
                return False
            
            # Split out each line
            lines = response.split('\n')
            
            # Loop over each line and get the values
            apacheStatus = {}
            
            # Loop through and extract the numerical values
            for line in lines:
                values = line.split(': ')
                
                try:
                    apacheStatus[str(values[0])] = values[1]
                    
                except IndexError:
                    break
            
            try:
                if apacheStatus['ReqPerSec'] != False and apacheStatus['BusyWorkers'] != False and apacheStatus['IdleWorkers'] != False:
                    return {'reqPerSec': apacheStatus['ReqPerSec'], 'busyWorkers': apacheStatus['BusyWorkers'], 'idleWorkers': apacheStatus['IdleWorkers']}
                
                else:
                    logger.debug('getApacheStatus: completed, status not available')
                    return False
                
            # Stops the agent crashing if one of the apacheStatus elements isn't set (e.g. ExtendedStatus Off)  
            except:
                logger.debug('getApacheStatus: ReqPerSec, BusyWorkers or IdleWorkers not present')
                                
            return False
            
        else:
            logger.debug('getApacheStatus: config not set')
            
            return False        
            
class Nginx(object):
    def __init__(self):
        # Used to measure request velocity
        self.nginxRequestsStore = None
        self.nginxRequestsTstamp = None
    
    def check(self, logger, agentConfig):
        logger.debug('getNginxStatus: start')
        
        if 'nginxStatusUrl' in agentConfig and agentConfig['nginxStatusUrl'] != 'http://www.example.com/nginx_status':  # Don't do it if the status URL hasn't been provided
            logger.debug('getNginxStatus: config set')
            
            try: 
                req = urllib2.Request(agentConfig['nginxStatusUrl'], None, headers(agentConfig))

                # Do the request, log any errors
                request = urllib2.urlopen(req)
                response = request.read()
                
            except:
                logger.exception('Unable to get Nginx status')
                return False
            
            # Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code
            
            # Connections
            parsed = re.search(r'Active connections:\s+(\d+)', response)
            connections = int(parsed.group(1))
            
            # Requests per second
            parsed = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', response)
            requests = int(parsed.group(3))
            
            # First time we see nginx_status data
            if self.nginxRequestsStore == None or self.nginxRequestsStore < 0:
                logger.debug('getNginxStatus: no reqs so storing for first time')
                self.nginxRequestsStore = requests
                requestsPerSecond = 0
                
            # Compute averages
            else:
                logger.debug('getNginxStatus: reqs stored so calculating')
                logger.debug('getNginxStatus: self.nginxRequestsStore = ' + str(self.nginxRequestsStore))
                logger.debug('getNginxStatus: requests = ' + str(requests))
                requestsPerSecond = float(requests - self.nginxRequestsStore) / (time.time() - self.nginxRequestsTstamp)
                logger.debug('getNginxStatus: requestsPerSecond = ' + str(requestsPerSecond))
                self.nginxRequestsStore = requests

            self.nginxRequestsTstamp = time.time()
            
            if connections != None and requestsPerSecond != None:
                return {'connections' : connections, 'reqPerSec' : requestsPerSecond}
            
            else:
                logger.debug('getNginxStatus: returning without data')
                return False
            
        else:
            return False
        
