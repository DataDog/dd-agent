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
DEFAULT_MAX_DEPTH = 10
DEFAULT_NAMESPACE = 'kubernetes'

class Kubernetes(AgentCheck):
    """ Collect metrics and events from kubelet agent"""

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
        self.max_depth = instance.get('max_depth', DEFAULT_MAX_DEPTH)
        self.namespace = instance.get('namespace', DEFAULT_NAMESPACE)
        
        self._update_metrics(instance)
        
    def _discover_metrics(self, metric, dat, tags, depth=0):
        if depth>=self.max_depth:
            self.log.warning('Reached max depth on metric=%s' % metric)
            return
        
        type_ = type(dat)
        if type_ is int or type_ is long or type_ is float:
            self.rate(metric, long(dat), tags)
        elif type_ is dict:
            for k,v in dat.iteritems():
                self._discover_metrics(metric+'.%s'%k.lower(), v, tags, depth+1)
        elif type_ is list:
            self._discover_metrics(metric, dat[-1], tags, depth+1)
        else:
            return
    
    def _update_metrics(self, instance):
        metrics = self._retrieve_json(self.metrics_cmd)
        if not metrics:
            self.log.warning('Unable to retrieve metrics cmd=%s' % self.metrics_cmd)
            return
        
        for subcontainer in metrics:
            name = subcontainer['name']
            tags = [ 'container_name:%s' % name ]

            try:
                for label_name,label in subcontainer['spec']['labels'].iteritems():
                    tags.append('label.%s:%s'% (label_name, label))
            except KeyError:
                pass
            
            stats = subcontainer['stats'][-1]  # take latest
            for metrics_type in [ 'cpu', 'diskio', 'network' ]:
                try:
                    self._discover_metrics(self.namespace+'.'+metrics_type, stats[metrics_type], tags)
                except KeyError:
                    self.log.warning('Unable to retrieve metrics_type=%s' % metrics_type)
