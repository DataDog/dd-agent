"""cAdvisor check
Collects metrics from cAdvisor instance
"""

# stdlib
import urllib2
from urlparse import urljoin

# project
from checks import AgentCheck
from util import json
# import json

DEFAULT_BASEURL = "http://localhost:4194/"
DEFAULT_METRICS_CMD = "/api/v1.3/subcontainers/"
DEFAULT_EVENTS_CMD = "/api/v1.3/events/"

class cAdvisor(AgentCheck):
    """ Collect metrics and events from cAdvisor instance"""

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def _retrieve_json(self, url):
        try:
            fd = urllib2.urlopen(url)
            raw_response = fd.read()
            fd.close()
            parsed_response = json.loads(raw_response)
        except Exception:
            return None
        
        return parsed_response

    def _retrieve_json_mock(self, url):
        return json.loads(open('cadvisor-subcontainers.json').read())

    def check(self, instance):
        self.baseurl = instance.get('baseurl', DEFAULT_BASEURL)
        self.metrics_cmd = urljoin(self.baseurl, DEFAULT_METRICS_CMD)
        self.events_cmd = urljoin(self.baseurl, DEFAULT_EVENTS_CMD)
        self._update_metrics()

    def _discover_metrics(self, metric, dat, tags):
        type_ = type(dat)
        if type_ is int or type_ is long or type_ is float:
            self.rate(metric, long(dat), tags)
        elif type_ is dict:
            for k,v in dat.iteritems():
                self._discover_metrics(metric+'.%s'%k, v, tags)
        elif type_ is list:
            self._discover_metrics(metric, dat[-1], tags)
        else:
            return
    
    def _update_metrics(self):
        for subcontainer in self._retrieve_json(self.metrics_cmd):
            name = subcontainer['name']
            tags = [ 'container_name:%s' % name ]

            try:
                for label_name,label in subcontainer['spec']['labels'].iteritems():
                    tags.append('label.%s:%s'% (label_name, label))
            except KeyError:
                pass
            
            try:
                namespace = subcontainer['namespace']
                tags.append('namespace:%s' % namespace)
            except KeyError:
                pass
            
            stats = subcontainer['stats'][-1]
            try:
                self._discover_metrics('cadvisor.cpu', stats['cpu'], tags)
            except KeyError:
                pass
                
            try:
                self._discover_metrics('cadvisor.diskio', stats['diskio'], tags)
            except KeyError:
                pass

            try:
                self._discover_metrics('cadvisor.network', stats['network'], tags)
            except KeyError:
                pass
