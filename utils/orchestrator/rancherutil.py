import requests
from rancher_metadata import MetadataAPI
from .baseutil import BaseUtil

from utils.singleton import Singleton


class RancherUtil(BaseUtil):
    __metaclass__ = Singleton

    METADATA_URL_AUTHORITY = "http://rancher-metadata/"
    METADATA_VERSION = "2016-07-29"
    METADATA_URL = "{}/{}".format(METADATA_URL_AUTHORITY, METADATA_VERSION)

    CONTAINER_NAME_LABEL = "io.rancher.container.name"
    CONTAINER_IP_LABEL = "io.rancher.container.ip"
    STACK_NAME_LABEL = "io.rancher.stack.name"
    SERVICE_NAME_LABEL = "io.rancher.stack_service.name"

    _is_rancher = None

    def __init__(self):
        BaseUtil.__init__(self)
        self.needs_inspect_config = True
        self.needs_inspect_labels = True

        self.api = MetadataAPI(api_url=RancherUtil.METADATA_URL)

    @staticmethod
    def is_detected():
        return RancherUtil.is_rancher()

    def _get_cacheable_tags(self, cid=None, co=None):
        tags = []

        container_name = co.get('Config', {}).get('Labels', {}).get(RancherUtil.CONTAINER_NAME_LABEL)

        container_metadata = self.get_container_metadata(container_name=container_name)

        service_name = co.get('Config', {}).get('Labels', {}).get(RancherUtil.SERVICE_NAME_LABEL) \
            or container_metadata.get('service_name')

        stack_name = co.get('Config', {}).get('Labels', {}).get(RancherUtil.STACK_NAME_LABEL) \
            or container_metadata.get('stack_name')

        if container_name:
            tags.append('rancher_container:%s' % container_name)
        if service_name:
            tags.append('rancher_service:%s' % service_name)
        if stack_name:
            tags.append('rancher_stack:%s' % stack_name)

        return tags

    @staticmethod
    def is_rancher():
        if RancherUtil._is_rancher is None:
            try:
                response = requests.get(url=RancherUtil.METADATA_URL, timeout=1)
                RancherUtil._is_rancher = response.status_code == 200
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                RancherUtil._is_rancher = False

        return RancherUtil._is_rancher

    def get_container_metadata(self, container_name):
        if not self.is_rancher():
            return []

        return self.api.get_container(container_name=container_name)

    def get_hosts_ip_for_container(self, container_name):
        if not self.is_rancher():
            return []

        return self.api.get_container_ip(container_name=container_name)

    def get_ports_for_container(self, container_name):
        all_ports = self.get_container_metadata(container_name=container_name)['ports']

        return [port.split(":")[1] for port in all_ports] if all_ports else []

    def get_container_stack_name(self, container_name):
        return self.get_container_metadata(container_name=container_name)['stack_name']

    def get_container_service_name(self, container_name):
        return self.get_container_metadata(container_name=container_name)['service_name']

    def get_labels_for_host(self):
        if not self.is_rancher():
            return {}

        return self.api.get_host(host_name=None)['labels']

    def get_host_tags(self):
        raw_labels = self.get_labels_for_host()
        labels = []

        for (k, v) in raw_labels.iteritems():
            labels.append("%s:%s" % (k, v))

        return labels
