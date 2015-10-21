"""kubernetes check
Collects metrics from cAdvisor instance
"""
# stdlib
import socket
import struct
from urlparse import urljoin
from fnmatch import fnmatch
import re

# 3rd party
import requests

# project
from checks import AgentCheck

DEFAULT_METHOD = 'http'
DEFAULT_CADVISOR_PORT = 4194
DEFAULT_METRICS_CMD = '/api/v1.3/subcontainers/'
DEFAULT_MAX_DEPTH = 10
DEFAULT_NAMESPACE = 'kubernetes'
DEFAULT_KUBELET_PORT = 10255
DEFAULT_MASTER_PORT = 8080
DEFAULT_PUBLISH_CONTAINER_NAMES = False
DEFAULT_ENABLED_RATES = [
    'diskio.io_service_bytes.stats.total',
    'network.??_bytes',
    'cpu.*.total']

DEFAULT_ENABLED_GAUGES = [
    'memory.usage',
    'filesystem.usage']

class Kubernetes(AgentCheck):
    """ Collect metrics and events from kubelet """

    def __init__(self, name, init_config, agentConfig, instances=None):
        if instances is not None and len(instances) > 1:
            raise Exception('Kubernetes check only supports one configured instance.')
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.default_router = self._get_default_router()
        self.log.info('default_router=%s' % self.default_router)

    def _get_default_router(self):
        try:
            with open('/proc/net/route') as f:
                for line in f.readlines():
                    fields = line.strip().split()
                    if fields[1] == '00000000':
                        return socket.inet_ntoa(struct.pack('<L', int(fields[2], 16)))
        except IOError, e:
            self.log.error('Unable to open /proc/net/route: %s', e)

        return None

    def _perform_kubelet_checks(self, url):
        import re
        service_check_base = self.namespace + '.kubelet.check'
        try:
            r = requests.get(url)
            for line in r.iter_lines():

                # avoid noise; this check is expected to fail since we override the container hostname
                if line.find('hostname') != -1:
                    continue

                matches = re.match('\[(.)\]([^\s]+) (.*)?', line)
                if not matches or len(matches.groups()) < 2:
                    continue

                service_check_name = service_check_base + '.' + matches.group(2)
                status = matches.group(1)
                if status == '+':
                    self.service_check(service_check_name, AgentCheck.OK)
                else:
                    self.service_check(service_check_name, AgentCheck.CRITICAL, matches.group(3))

        except Exception, e:
            self.log.warning('kubelet check failed: %s' % str(e))
            self.service_check(service_check_base, AgentCheck.CRITICAL, 'Kubelet check failed: %s' % str(e))

    def _perform_master_checks(self, url):
        try:
            r = requests.get(url)
            for nodeinfo in r.json()['items']:
                nodename = nodeinfo['name']
                service_check_name = self.namespace+'.master.'+nodename+'.check'
                cond = nodeinfo['status'][-1]['type']
                if cond != 'Ready':
                    self.service_check(service_check_name, AgentCheck.CRITICAL, cond)
                else:
                    self.service_check(service_check_name, AgentCheck.OK)
        except Exception, e:
            self.log.warning('master checks url=%s exception=%s' % (url, str(e)))

    def check(self, instance):
        host = instance.get('host', self.default_router)
        if not host:
            raise Exception('Unable to get default router and host parameter is not set')

        port = instance.get('port', DEFAULT_CADVISOR_PORT)
        method = instance.get('method', DEFAULT_METHOD)
        self.metrics_url = '%s://%s:%d' % (method, host, port)
        self.metrics_cmd = urljoin(self.metrics_url, DEFAULT_METRICS_CMD)
        self.max_depth = instance.get('max_depth', DEFAULT_MAX_DEPTH)
        self.namespace = instance.get('namespace', DEFAULT_NAMESPACE)
        enabled_gauges = instance.get('enabled_gauges', DEFAULT_ENABLED_GAUGES)
        self.enabled_gauges = [self.namespace+'.'+x for x in enabled_gauges]
        enabled_rates = instance.get('enabled_rates', DEFAULT_ENABLED_RATES)
        self.enabled_rates = [self.namespace+'.'+x for x in enabled_rates]

        # master health checks
        if instance.get('enable_master_checks', False):
            master_port = instance.get('master_port', DEFAULT_MASTER_PORT)
            master_host = instance.get('master_host', 'localhost')
            master_url = '%s://%s:%d/nodes' % (method, host, master_port)
            self._perform_master_checks(master_url)

        # kubelet health checks
        if instance.get('enable_kubelet_checks', True):
            kubelet_port = instance.get('kubelet_port', DEFAULT_KUBELET_PORT)
            kubelet_url = '%s://%s:%d/healthz' % (method, host, kubelet_port)
            self._perform_kubelet_checks(kubelet_url)

        # kubelet metrics
        self._update_metrics(instance)

    def _publish_raw_metrics(self, metric, dat, tags, depth=0):
        if depth >= self.max_depth:
            self.log.warning('Reached max depth on metric=%s' % metric)
            return

        type_ = type(dat)
        if type_ is int or type_ is long or type_ is float:
            if self.enabled_rates and any([fnmatch(metric, pat) for pat in self.enabled_rates]):
                self.rate(metric, long(dat), tags)
            elif self.enabled_gauges and any([fnmatch(metric, pat) for pat in self.enabled_gauges]):
                self.gauge(metric, long(dat), tags)
            else:
                return
        elif type_ is dict:
            for k,v in dat.iteritems():
                self._publish_raw_metrics(metric + '.%s' % k.lower(), v, tags, depth + 1)
        elif type_ is list:
            self._publish_raw_metrics(metric, dat[-1], tags, depth + 1)
        else:
            return

    def _retrieve_json(self, url):
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _shorten_name(name):
        # shorten docker image id
        return re.sub('([0-9a-fA-F]{64,})', lambda x: x.group(1)[0:12], name)

    def _publish_calculated_metrics(self, namespace, stats, tags):
        try:
            fs = stats['filesystem'][-1]
            fs_capacity = long(fs['capacity'])
            fs_usage = long(fs['usage'])
            self.gauge(namespace+'.filesystem.usage_pct', fs_usage/fs_capacity, tags)
        except Exception:
            pass

        try:
            net = stats['network']
            self.rate(namespace+'.network_errors',
                      sum(long(net[x]) for x in ['rx_errors', 'tx_errors', 'rx_dropped', 'tx_dropped']), tags)
        except Exception:
            pass

    def _update_metrics(self, instance):
        metrics = self._retrieve_json(self.metrics_cmd)
        if not metrics:
            raise Exception('No metrics retrieved cmd=%s' % self.metrics_cmd)

        for subcontainer in metrics:
            tags = []
            tags.append('container_name:%s' % self._shorten_name(subcontainer['name']))

            try:
                for label_name,label in subcontainer['spec']['labels'].iteritems():
                    label_name = label_name.replace('io.kubernetes.pod.name', 'pod_name')
                    tags.append('%s:%s' % (label_name, label))
            except KeyError:
                pass

            try:
                for alias in subcontainer['aliases']:
                    tags.append('container_name:%s' % (self._shorten_name(alias)))
            except KeyError:
                pass

            stats = subcontainer['stats'][-1]  # take latest
            self._publish_raw_metrics(self.namespace, stats, tags)
            self._publish_calculated_metrics(self.namespace, stats, tags)
