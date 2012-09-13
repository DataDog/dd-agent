import re
import time
import urllib2

from util import headers
from checks import *

class Apache(Check):
    """Tracks basic connection/requests/workers metrics

    See http://httpd.apache.org/docs/2.2/mod/mod_status.html for more details
    """
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.gauge("apacheConnections")
        self.gauge("apacheReqPerSec")
        self.gauge("apacheBusyWorkers")
        self.gauge("apacheIdleWorkers")
        self.gauge("apacheBytesPerSec")
        self.gauge("apacheUptime")
        # don't make counters of these, they already exist
        self.gauge("apacheTotalBytes")
        self.gauge("apacheTotalAccesses")
        self.gauge("apacheCPULoad")

    def check(self, agentConfig):
        if 'apache_status_url' in agentConfig and agentConfig['apache_status_url'] != 'http://www.example.com/server-status/?auto': # Don't do it if the status URL hasn't been provided
            try: 
                req = urllib2.Request(agentConfig['apache_status_url'], None, headers(agentConfig))
                request = urllib2.urlopen(req)
                response = request.read()
                sample_time = time.time()
                
                # Split out each line
                lines = response.split('\n')
            
                # Loop over each line and get the values
                apacheStatus = {}

                # Loop through and extract the numerical values
                for line in lines:
                    values = line.split(': ')
                    if len(values) == 2: # match
                        try:
                            metric, value = values
                            # prefix metric name with apache
                            if metric == "Total kBytes":
                                self.save_sample("apacheTotalBytes", float(value) * 1024, sample_time)
                            elif metric == "Total Accesses":
                                self.save_sample("apacheTotalAccesses", float(value), sample_time)
                            else:
                                self.save_sample("apache"+values[0], float(values[1]), sample_time)
                        except CheckException:
                            continue
                        except ValueError:
                            continue

                return self.get_samples()
            except:
                self.logger.exception('Unable to get Apache status')

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
        self.gauge("nginx.net.connections")
        self.counter("nginx.net.request_per_s")
        self.gauge("nginx.net.reading")
        self.gauge("nginx.net.writing")
        self.gauge("nginx.net.waiting")

    def _load_conf(self, agentConfig):
        # Load the conf according to the old schema
        nginx_url = agentConfig.get("nginx_status_url", None)
        nginx_status_urls = []
        tags = []
        if nginx_url is not None:
            nginx_status_urls.append(nginx_url)
            tags.append(None)

        # Load the conf according to the new schema
        #nginx_status_url_1: http://www.example.com/nginx_status:first_tag
        #nginx_status_url_2: http://www.example2.com/nginx_status:8080:second_tag
        #nginx_status_url_2: http://www.example3.com/nginx_status:third_tag
        def load_conf(index=1):
            instance = agentConfig.get("nginx_status_url_%s" % index, None)
            if instance is not None:
                instance = instance.split(":")
                tags.append(instance[-1])
                nginx_status_urls.append(":".join(instance[:-1]))
                load_conf(index+1)

        load_conf()

        return (nginx_status_urls, tags)

    def _get_metrics(self, url, tag, agentConfig):
        req = urllib2.Request(url, None, headers(agentConfig))
        request = urllib2.urlopen(req)
        response = request.read()
        sample_time = time.time()

        # Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code
        # Connections
        parsed = re.search(r'Active connections:\s+(\d+)', response)
        if parsed:
            connections = int(parsed.group(1))
            self.save_sample("nginx.net.connections", connections, sample_time, tags=tag)
    
        # Requests per second
        parsed = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', response)
        if parsed:
            requests = int(parsed.group(3))
            self.save_sample("nginx.net.request_per_s", requests, sample_time, tags=tag)

        # Connection states, reading, writing or waiting for clients
        parsed = re.search(r'Reading: (\d+)\s+Writing: (\d+)\s+Waiting: (\d+)', response)
        if parsed:
            reading, writing, waiting = map(int, parsed.groups())
            assert connections == reading + writing + waiting 
            self.save_sample("nginx.net.reading", reading, sample_time, tags=tag)
            self.save_sample("nginx.net.writing", writing, sample_time, tags=tag)
            self.save_sample("nginx.net.waiting", waiting, sample_time, tags=tag)



    
    def check(self, agentConfig):
        """
        $ curl http://localhost:81/nginx_status/
        Active connections: 8 
        server accepts handled requests
         1156958 1156958 4491319 
        Reading: 0 Writing: 2 Waiting: 6
        """
        (nginx_status_urls, tags) = self._load_conf(agentConfig)

        
        for i in range(len(nginx_status_urls)):
            url = nginx_status_urls[i]
            tag = None
            if tags[i] is not None:
                tag = ["instance:%s" % tags[i]]
            
            if url and url!='http://www.example.com/nginx_status':  # Don't do it if the status URL hasn't been provided
                try:
                    self._get_metrics(url, tag, agentConfig)
                    
                except:
                    self.logger.exception('Unable to get Nginx status')
        return self.get_metrics()
