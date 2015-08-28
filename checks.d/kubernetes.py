"""kubernetes check
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

class Kubernetes(AgentCheck):
    """ Collect metrics and events from Kubernetes instance"""

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

    def check(self, instance):
        self.baseurl = instance.get('baseurl', DEFAULT_BASEURL)
        self.metrics_cmd = urljoin(self.baseurl, DEFAULT_METRICS_CMD)
        self.events_cmd = urljoin(self.baseurl, DEFAULT_EVENTS_CMD)
        self._update_metrics(instance)

    def _discover_metrics(self, metric, dat, tags):
        type_ = type(dat)
        if type_ is int or type_ is long or type_ is float:
            self.rate(metric, long(dat), tags)
        elif type_ is dict:
            for k,v in dat.iteritems():
                self._discover_metrics(metric+'.%s'%k.lower(), v, tags)
        elif type_ is list:
            self._discover_metrics(metric, dat[-1], tags)
        else:
            return
    
    def _update_metrics(self, instance):
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
                namespace = 'kubernetes'
            
            stats = subcontainer['stats'][-1]
            try:
                self._discover_metrics(namespace+'.cpu', stats['cpu'], tags)
            except KeyError:
                pass
                
            try:
                self._discover_metrics(namespace+'.diskio', stats['diskio'], tags)
            except KeyError:
                pass

            try:
                self._discover_metrics(namespace+'.network', stats['network'], tags)
            except KeyError:
                pass
