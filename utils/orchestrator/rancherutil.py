import logging
import requests
from rancher_metadata import MetadataAPI

from utils.singleton import Singleton

log = logging.getLogger(__name__)


class RancherUtil:
    __metaclass__ = Singleton

    METADATA_URL_AUTHORITY = "http://rancher-metadata/"
    METADATA_VERSION = "2016-07-29"
    METADATA_URL = "{}/{}".format(METADATA_URL_AUTHORITY, METADATA_VERSION)

    CONTAINER_NAME_LABEL = "io.rancher.container.name"
    CONTAINER_IP_LABEL = "io.rancher.container.ip"
    STACK_NAME_LABEL = "io.rancher.stack.name"
    SERVICE_NAME_LABEL = "io.rancher.stack_service.name"

    HOST_AGENT_IMAGE_LABEL = "io.rancher.host.agent_image"
    HOST_DOCKER_VERSION_LABEL = "io.rancher.host.docker_version"
    HOST_LINUX_KERNEL_VERSION_LABEL = "io.rancher.host.linux_kernel_version"

    _is_rancher = None

    def __init__(self):
        self.api = MetadataAPI(api_url=RancherUtil.METADATA_URL)

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
