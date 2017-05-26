import logging
import requests
from rancher_metadata import MetadataAPI

from utils.singleton import Singleton

log = logging.getLogger(__name__)


class RancherUtil:
    __metaclass__ = Singleton

    METADATA_URL_AUTHORITY = "http://rancher-metadata/"
    METADATA_VERSION = "2016-07-29"

    CONTAINER_NAME_LABEL = "io.rancher.container.name"
    CONTAINER_IP_LABEL = "io.rancher.container.ip"
    STACK_NAME_LABEL = "io.rancher.stack.name"
    SERVICE_NAME_LABEL = "io.rancher.stack_service.name"

    def __init__(self):
        self.metadata_url = "{}/{}".format(self.METADATA_URL_AUTHORITY, self.METADATA_VERSION)
        self.api = MetadataAPI(api_url=self.metadata_url)
        self.metadata_api_available = self.is_metadata_api_available()

    def is_metadata_api_available(self):
        try:
            response = requests.get(url=self.metadata_url)
            return response.status_code == 200 and self.api.is_network_managed()
        except requests.exceptions.ConnectionError:
            return False

    def is_rancher(self):
        return self.metadata_api_available

    def get_hosts_ip_for_container(self, container_name):
        if not self.is_rancher():
            return []

        return self.api.get_container_ip(container_name=container_name)

    def get_ports_for_container(self, container_name):
        if not self.is_rancher():
            return []

        all_ports = self.api.get_container(container_name=container_name)['ports']

        return [port.split(":")[1] for port in all_ports] if all_ports else []
