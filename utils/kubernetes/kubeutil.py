# (C) Datadog, Inc. 2015-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict
import logging
import os
from urlparse import urljoin

# project
from util import check_yaml
from utils.checkfiles import get_conf_path
from utils.http import retrieve_json
from utils.singleton import Singleton
from utils.dockerutil import DockerUtil

import requests

log = logging.getLogger('collector')

KUBERNETES_CHECK_NAME = 'kubernetes'


class KubeUtil:
    __metaclass__ = Singleton

    DEFAULT_METHOD = 'http'
    MACHINE_INFO_PATH = '/api/v1.3/machine/'
    METRICS_PATH = '/api/v1.3/subcontainers/'
    PODS_LIST_PATH = '/pods/'
    DEFAULT_CADVISOR_PORT = 4194
    DEFAULT_KUBELET_PORT = 10255
    DEFAULT_MASTER_PORT = 8080
    DEFAULT_MASTER_NAME = 'kubernetes'  # DNS name to reach the master from a pod.
    CA_CRT_PATH = '/run/secrets/kubernetes.io/serviceaccount/ca.crt'
    AUTH_TOKEN_PATH = '/run/secrets/kubernetes.io/serviceaccount/token'

    POD_NAME_LABEL = "io.kubernetes.pod.name"
    NAMESPACE_LABEL = "io.kubernetes.pod.namespace"

    def __init__(self, instance=None):
        self.docker_util = DockerUtil()
        if instance is None:
            try:
                config_file_path = get_conf_path(KUBERNETES_CHECK_NAME)
                check_config = check_yaml(config_file_path)
                instance = check_config['instances'][0]
            # kubernetes.yaml was not found
            except IOError as ex:
                log.error(ex.message)
                instance = {}
            except Exception:
                log.error('Kubernetes configuration file is invalid. '
                          'Trying connecting to kubelet with default settings anyway...')
                instance = {}

        self.method = instance.get('method', KubeUtil.DEFAULT_METHOD)
        self.host = instance.get("host") or self.docker_util.get_hostname()
        self._node_ip = self._node_name = None  # lazy evaluation
        self.host_name = os.environ.get('HOSTNAME')

        self.cadvisor_port = instance.get('port', KubeUtil.DEFAULT_CADVISOR_PORT)
        self.kubelet_port = instance.get('kubelet_port', KubeUtil.DEFAULT_KUBELET_PORT)

        self.kubelet_api_url = '%s://%s:%d' % (self.method, self.host, self.kubelet_port)
        self.cadvisor_url = '%s://%s:%d' % (self.method, self.host, self.cadvisor_port)
        self.kubernetes_api_url = 'https://%s/api/v1' % (os.environ.get('KUBERNETES_SERVICE_HOST') or self.DEFAULT_MASTER_NAME)

        self.metrics_url = urljoin(self.cadvisor_url, KubeUtil.METRICS_PATH)
        self.machine_info_url = urljoin(self.cadvisor_url, KubeUtil.MACHINE_INFO_PATH)
        self.pods_list_url = urljoin(self.kubelet_api_url, KubeUtil.PODS_LIST_PATH)
        self.kube_health_url = urljoin(self.kubelet_api_url, 'healthz')

        # keep track of the latest k8s event we collected and posted
        # default value is 0 but TTL for k8s events is one hour anyways
        self.last_event_collection_ts = 0

    def get_kube_labels(self, excluded_keys=None):
        pods = self.retrieve_pods_list()
        return self.extract_kube_labels(pods, excluded_keys=excluded_keys)

    def extract_kube_labels(self, pods_list, excluded_keys=None):
        """
        Extract labels from a list of pods coming from
        the kubelet API.
        """
        excluded_keys = excluded_keys or []
        kube_labels = defaultdict(list)
        pod_items = pods_list.get("items") or []
        for pod in pod_items:
            metadata = pod.get("metadata", {})
            name = metadata.get("name")
            namespace = metadata.get("namespace")
            labels = metadata.get("labels")
            if name and labels and namespace:
                key = "%s/%s" % (namespace, name)

                for k, v in labels.iteritems():
                    if k in excluded_keys:
                        continue

                    kube_labels[key].append(u"kube_%s:%s" % (k, v))

        return kube_labels

    def extract_meta(self, pods_list, field_name):
        """
        Exctract fields like `uid` or `name` from the `metadata` section of a
        list of pods coming from the kubelet API.

        TODO: currently not in use, was added to support events filtering, consider to remove it.
        """
        uids = []
        pods = pods_list.get("items") or []
        for p in pods:
            value = p.get('metadata', {}).get(field_name)
            if value is not None:
                uids.append(value)
        return uids

    def retrieve_pods_list(self):
        """
        Retrieve the list of pods for this cluster querying the kubelet API.

        TODO: the list of pods could be cached with some policy to be decided.
        """
        return retrieve_json(self.pods_list_url)

    def retrieve_machine_info(self):
        """
        Retrieve machine info from Cadvisor.
        """
        return retrieve_json(self.machine_info_url)

    def retrieve_metrics(self):
        """
        Retrieve metrics from Cadvisor.
        """
        return retrieve_json(self.metrics_url)

    def filter_pods_list(self, pods_list, host_ip):
        """
        Filter out (in place) pods that are not running on the given host.

        TODO: currently not in use, was added to support events filtering, consider to remove it.
        """
        pod_items = pods_list.get('items') or []
        log.debug('Found {} pods to filter'.format(len(pod_items)))

        filtered_pods = []
        for pod in pod_items:
            status = pod.get('status', {})
            if status.get('hostIP') == host_ip:
                filtered_pods.append(pod)
        log.debug('Pods after filtering: {}'.format(len(filtered_pods)))

        pods_list['items'] = filtered_pods
        return pods_list

    def retrieve_json_auth(self, url, auth_token, timeout=10):
        """
        Kubernetes API requires authentication using a token available in
        every pod.

        We try to verify ssl certificate if available.
        """
        verify = self.CA_CRT_PATH if os.path.exists(self.CA_CRT_PATH) else False
        log.debug('ssl validation: {}'.format(verify))
        headers = {'Authorization': 'Bearer {}'.format(auth_token)}
        r = requests.get(url, timeout=timeout, headers=headers, verify=verify)
        r.raise_for_status()
        return r.json()

    def get_node_info(self):
        """
        Return the IP address and the hostname of the node where the pod is running.
        """
        if None in (self._node_ip, self._node_name):
            self._fetch_host_data()
        return self._node_ip, self._node_name

    def _fetch_host_data(self):
        """
        Retrieve host name and IP address from the payload returned by the listing
        pods endpoints from kubelet or kubernetes API.

        The host IP address is different from the default router for the pod.
        """
        try:
            pod_items = self.retrieve_pods_list().get("items") or []
        except Exception as e:
            log.warning("Unable to retrieve pod list %s. Not fetching host data", str(e))
            return

        for pod in pod_items:
            metadata = pod.get("metadata", {})
            name = metadata.get("name")
            if name == self.host_name:
                status = pod.get('status', {})
                spec = pod.get('spec', {})
                # if not found, use an empty string - we use None as "not initialized"
                self._node_ip = status.get('hostIP', '')
                self._node_name = spec.get('nodeName', '')
                break

    def extract_event_tags(self, event):
        """
        Return a list of tags extracted from an event object
        """
        tags = []

        if 'reason' in event:
            tags.append('reason:%s' % event.get('reason', '').lower())
        if 'namespace' in event.get('metadata', {}):
            tags.append('namespace:%s' % event['metadata']['namespace'])
        if 'host' in event.get('source', {}):
            tags.append('node_name:%s' % event['source']['host'])
        if 'kind' in event.get('involvedObject', {}):
            tags.append('object_type:%s' % event['involvedObject'].get('kind', '').lower())

        return tags

    def are_tags_filtered(self, tags):
        """
        Because it is a pain to call it from the kubernetes check otherwise.
        """
        return self.docker_util.are_tags_filtered(tags)

    @classmethod
    def get_auth_token(cls):
        """
        Return a string containing the authorization token for the pod.
        """
        try:
            with open(cls.AUTH_TOKEN_PATH) as f:
                return f.read()
        except IOError as e:
            log.error('Unable to read token from {}: {}'.format(cls.AUTH_TOKEN_PATH, e))

        return None
