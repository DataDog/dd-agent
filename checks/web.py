import urllib2
import re
import time
from util import headers

from checks import *

class Apache(Check):
    """Tracks basic connection/requests/workers metrics

    See http://httpd.apache.org/docs/2.2/mod/mod_status.html for more details
    """
    def __init__(self, logger):
        Check.__init__(self, logger)

    def check(self, agentConfig):
        if 'apacheStatusUrl' in agentConfig and agentConfig['apacheStatusUrl'] != 'http://www.example.com/server-status/?auto': # Don't do it if the status URL hasn't been provided
            try: 
                req = urllib2.Request(agentConfig['apacheStatusUrl'], None, headers(agentConfig))
                request = urllib2.urlopen(req)
                response = request.read()
                
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
                if apacheStatus['ReqPerSec'] and apacheStatus['BusyWorkers'] and apacheStatus['IdleWorkers']:
                    return {'reqPerSec': apacheStatus['ReqPerSec'], 'busyWorkers': apacheStatus['BusyWorkers'], 'idleWorkers': apacheStatus['IdleWorkers']}
            except:
                logger.exception('Unable to get Apache status')

        return False        
            
class Nginx(Check):
    """Tracks basic nginx metrics via the status module
    * number of connections
    * number of requets per second

    Requires nginx to have the status option compiled.
    See http://wiki.nginx.org/HttpStubStatusModule for more details
    """
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.gauge("connections")
        self.counter("reqPerSec")
    
    def check(self, agentConfig):
        if 'nginxStatusUrl' in agentConfig and agentConfig['nginxStatusUrl'] != 'http://www.example.com/nginx_status':  # Don't do it if the status URL hasn't been provided
            try: 
                req = urllib2.Request(agentConfig['nginxStatusUrl'], None, headers(agentConfig))
                request = urllib2.urlopen(req)
                response = request.read()

                # Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code
                # Connections
                parsed = re.search(r'Active connections:\s+(\d+)', response)
                connections = int(parsed.group(1))
                self.save_sample("connections", connections)
            
                # Requests per second
                parsed = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', response)
                requests = int(parsed.group(3))
                self.save_sample("reqPerSec", requests)
                
                return self.get_samples()
            except:
                logger.exception('Unable to get Nginx status')
                return False
        else:
            return False
