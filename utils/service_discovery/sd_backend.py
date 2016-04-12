# std
import logging

# project
from utils.service_discovery.sd_docker_backend import SDDockerBackend

log = logging.getLogger(__name__)

AUTO_CONFIG_DIR = 'auto_conf/'
SD_BACKENDS = ['docker']


def get_sd_backend(agentConfig):
    if agentConfig.get('service_discovery_backend') == 'docker':
        return SDDockerBackend(agentConfig)
    else:
        log.error("Service discovery backend not supported. This feature won't be enabled")
