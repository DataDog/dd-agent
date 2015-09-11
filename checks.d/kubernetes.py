"""kubernetes check
Collects metrics from cAdvisor instance
"""

from urlparse import urljoin
import requests
from checks import AgentCheck

DEFAULT_PORT = 4194
DEFAULT_METRICS_CMD = '/api/v1.3/subcontainers/'
DEFAULT_EVENTS_CMD = '/api/v1.3/events/'
DEFAULT_MAX_DEPTH = 10
DEFAULT_NAMESPACE = 'kubernetes'
DEFAULT_HEALTHCHECK_PORT = 10255
DEFAULT_PUBLISH_CONTAINER_NAMES = False

class Kubernetes(AgentCheck):
    """ Collect metrics and events from kubelet """

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def _retrieve_json(self, url):
        try:
            r = requests.get(url)
            return r.json()
        except Exception:
            return None

    def _get_default_router(self):
        import socket
        import struct
        try:
            for line in open("/proc/net/route").readlines():
                fields = line.strip().split()
                if fields[1]=='00000000':
                    return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))
        except IOError:
            pass

        return None
    
    def _perform_health_check(self, url):
        try:
            r = requests.get(url)
            return r.text.find('ok')==0
        except Exception:
            return False
        
    def check(self, instance):
        host = instance.get('host', self._get_default_router())
        port = instance.get('port', DEFAULT_PORT)
        method = instance.get('method', 'http')
        self.baseurl = '%s://%s:%d' % (method, host, port)
        self.metrics_cmd = urljoin(self.baseurl, DEFAULT_METRICS_CMD)
        self.events_cmd = urljoin(self.baseurl, DEFAULT_EVENTS_CMD)
        self.max_depth = instance.get('max_depth', DEFAULT_MAX_DEPTH)
        self.namespace = instance.get('namespace', DEFAULT_NAMESPACE)

        healthcheck_port = instance.get('healthcheck_port', DEFAULT_HEALTHCHECK_PORT)
        healthcheck_url = '%s://%s:%d' % (method, host, healthcheck_port)
        if not self._perform_health_check(healthcheck_url):
            self.log.warning('Kubelet health check failed, url=%s' % healthcheck_url)

        self._update_metrics(instance, instance.get('publish_container_names', DEFAULT_PUBLISH_CONTAINER_NAMES))
        
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
    
    def _update_metrics(self, instance, publish_container_names):
        metrics = self._retrieve_json(self.metrics_cmd)
        if not metrics:
            self.log.warning('Unable to retrieve metrics cmd=%s' % self.metrics_cmd)
            return
        
        for subcontainer in metrics:
            tags = []
            if publish_container_names:
                name = subcontainer['name']
                tags.append('container_name:%s' % name)

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
