"""kubernetes check
Collects metrics from cAdvisor instance
"""

from urlparse import urljoin
import requests
from checks import AgentCheck

DEFAULT_CADVISOR_PORT = 4194
DEFAULT_METRICS_CMD = '/api/v1.3/subcontainers/'
DEFAULT_MAX_DEPTH = 10
DEFAULT_NAMESPACE = 'kubernetes'
DEFAULT_KUBELET_PORT = 10255
DEFAULT_MASTER_PORT = 8080
DEFAULT_PUBLISH_CONTAINER_NAMES = False

class Kubernetes(AgentCheck):
    """ Collect metrics and events from kubelet """

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.default_router = self._get_default_router()
        
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
    
    def _perform_kubelet_checks(self, url):
        service_check_name = self.namespace+'.kubelet.check'
        try:
            r = requests.get(url)
            if r.text.find('ok')!=-1:
                self.service_check(service_check_name, AgentCheck.OK)
                return
            reason = 'health_not_ok'
        except Exception, e:
            reason = str(e)
        self.service_check(service_check_name, AgentCheck.CRITICAL, 'Kubelet health check failed: %s' % reason)

    def _perform_master_checks(self, url):
        try:
            r = requests.get(url)
            for nodeinfo in r.json()['items']:
                nodename = nodeinfo['name']
                service_check_name = self.namespace+'.master.'+nodename+'.check'
                cond = nodeinfo['status'][-1]['type']
                if cond!='Ready':
                    self.service_check(service_check_name, AgentCheck.CRITICAL, cond)
                else:
                    self.service_check(service_check_name, AgentCheck.OK)
        except Exception, e:
            self.log.warning('master checks url=%s exception=%s' % (url, str(e)))
    
    def check(self, instance):
        host = instance.get('host', self.default_router)
        port = instance.get('port', DEFAULT_CADVISOR_PORT)
        method = instance.get('method', 'http')
        self.metrics_url = '%s://%s:%d' % (method, host, port)
        self.metrics_cmd = urljoin(self.metrics_url, DEFAULT_METRICS_CMD)
        self.max_depth = instance.get('max_depth', DEFAULT_MAX_DEPTH)
        self.namespace = instance.get('namespace', DEFAULT_NAMESPACE)

        # master health checks
        if instance.get('enable_master_checks', False):
            master_port = instance.get('master_port', DEFAULT_MASTER_PORT)
            master_host = instance.get('master_host', 'localhost')
            master_url = '%s://%s:%d/nodes' % (method, host, master_port)
            self._perform_master_checks(master_url)

        # kubelet health checks
        if instance.get('enable_kubelet_checks', True):
            kubelet_port = instance.get('kubelet_port', DEFAULT_KUBELET_PORT)
            kubelet_url = '%s://%s:%d' % (method, host, kubelet_port)
            self._perform_kubelet_checks(kubelet_url)

        # kubelet metrics
        publish_container_names = instance.get('publish_container_names', DEFAULT_PUBLISH_CONTAINER_NAMES)
        self._update_metrics(instance, publish_container_names)
        
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
        service_check_name = self.namespace+'.metrics_collection'
        if not metrics:
            self.service_check(service_check_name, AgentCheck.CRITICAL, 'No metrics retrieved')
            return
        
        self.service_check(service_check_name, AgentCheck.OK)
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
