# stdlib
import logging
import os
import socket
import struct
from urlparse import urljoin

# project
from util import check_yaml
from utils.checkfiles import get_conf_path
from utils.http import retrieve_json
from utils.singleton import Singleton

log = logging.getLogger('collector')

KUBERNETES_CHECK_NAME = 'kubernetes'


def is_k8s():
    return 'KUBERNETES_PORT' in os.environ


class KubeUtil():
    __metaclass__ = Singleton

    DEFAULT_METHOD = 'http'
    METRICS_PATH = '/api/v1.3/subcontainers/'
    PODS_LIST_PATH = '/pods/'
    DEFAULT_CADVISOR_PORT = 4194
    DEFAULT_KUBELET_PORT = 10255
    DEFAULT_MASTER_PORT = 8080

    def __init__(self):
        config_file_path = get_conf_path(KUBERNETES_CHECK_NAME)
        try:
            check_config = check_yaml(config_file_path)
            instance = check_config['instances'][0]
        except Exception:
            log.error('Kubernetes configuration file is invalid. '
                      'Trying connecting to kubelet with default settings anyway...')
            instance = {}

        self.method = instance.get('method', KubeUtil.DEFAULT_METHOD)
        self.host = instance.get("host") or self._get_default_router()
        self.master_host = instance.get('master_host', self.host)

        self.cadvisor_port = instance.get('port', KubeUtil.DEFAULT_CADVISOR_PORT)
        self.kubelet_port = instance.get('kubelet_port', KubeUtil.DEFAULT_KUBELET_PORT)
        self.master_port = instance.get('master_port', KubeUtil.DEFAULT_MASTER_PORT)

        self.metrics_url = urljoin(
            '%s://%s:%d' % (self.method, self.host, self.cadvisor_port), KubeUtil.METRICS_PATH)
        self.pods_list_url = urljoin(
            '%s://%s:%d' % (self.method, self.host, self.kubelet_port), KubeUtil.PODS_LIST_PATH)

        self.master_url_nodes = '%s://%s:%d/api/v1/nodes' % (self.method, self.master_host, self.master_port)
        self.kube_health_url = '%s://%s:%d/healthz' % (self.method, self.host, self.kubelet_port)

    def get_kube_labels(self):
        pods = retrieve_json(self.pods_list_url)
        return self.extract_kube_labels(pods)

    def extract_kube_labels(self, pods_list):
        """
        Extract labels from a list of pods coming from
        the kubelet API.
        """
        kube_labels = {}
        for pod in pods_list["items"]:
            metadata = pod.get("metadata", {})
            name = metadata.get("name")
            namespace = metadata.get("namespace")
            labels = metadata.get("labels")
            if name and labels and namespace:
                key = "%s/%s" % (namespace, name)
                kube_labels[key] = ["kube_%s:%s" % (k, v) for k, v in labels.iteritems()]

        return kube_labels

    def retrieve_pods_list(self):
        return retrieve_json(self.pods_list_url)

    @classmethod
    def _get_default_router(cls):
        try:
            with open('/proc/net/route') as f:
                for line in f.readlines():
                    fields = line.strip().split()
                    if fields[1] == '00000000':
                        return socket.inet_ntoa(struct.pack('<L', int(fields[2], 16)))
        except IOError, e:
            log.error('Unable to open /proc/net/route: %s', e)

        return None
