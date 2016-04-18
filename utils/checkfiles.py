"""Helpers to work with check files (Python and YAML)."""
# std
import itertools
import logging
import os
from urlparse import urljoin

# project
from util import check_yaml

log = logging.getLogger(__name__)


def get_conf_path(check_name):
    """Return the yaml config file path for a given check name."""
    from config import get_confd_path, PathNotFound
    confd_path = ''

    try:
        confd_path = get_confd_path()
    except PathNotFound:
        log.error("Couldn't find the check configuration folder, this shouldn't happen.")
        return None

    conf_path = os.path.join(confd_path, '%s.yaml' % check_name)
    if not os.path.exists(conf_path):
        default_conf_path = os.path.join(confd_path, '%s.yaml.default' % check_name)
        if not os.path.exists(default_conf_path):
            log.error("Couldn't find any configuration file for the %s check." % check_name)
            return None
        else:
            conf_path = default_conf_path
    return conf_path


def get_check_class(agentConfig, check_name):
    """Return the class object for a given check name"""
    from config import get_os, get_checks_paths, get_check_class

    osname = get_os()
    checks_paths = get_checks_paths(agentConfig, osname)
    for check in itertools.chain(*checks_paths):
        py_check_name = os.path.basename(check).split('.')[0]
        if py_check_name == check_name:
            check_class = get_check_class(check_name, check)
            if isinstance(check_class, dict) or check_class is None:
                log.warning('Failed to load the check class for %s.' % check_name)
                return None
            else:
                return check_class


def get_auto_conf(agentConfig, check_name):
    """Return the yaml auto_config dict for a check name (None if it doesn't exist)."""
    from config import PathNotFound, get_auto_confd_path

    try:
        auto_confd_path = get_auto_confd_path()
    except PathNotFound:
        log.error("Couldn't find the check auto-configuration folder, no auto configuration will be used.")
        return None

    auto_conf_path = os.path.join(auto_confd_path, '%s.yaml' % check_name)
    if not os.path.exists(auto_conf_path):
        log.error("Couldn't find any auto configuration file for the %s check." % check_name)
        return None

    try:
        auto_conf = check_yaml(auto_conf_path)
    except Exception as e:
        log.error("Enable to load the auto-config, yaml file."
                  "Auto-config will not work for this check.\n%s" % str(e))
        return None

    return auto_conf


def get_auto_conf_images(agentConfig):
    """Walk through the auto_config folder and build a dict of auto-configurable images."""
    from config import PathNotFound, get_auto_confd_path
    auto_conf_images = {
        # image_name: check_name
    }

    try:
        auto_confd_path = get_auto_confd_path()
    except PathNotFound:
        log.error("Couldn't find the check auto-configuration folder, no auto configuration will be used.")
        return None

    # walk through the auto-config dir
    for yaml_file in os.listdir(auto_confd_path):
        check_name = yaml_file.split('.')[0]
        try:
            # load the config file
            auto_conf = check_yaml(urljoin(auto_confd_path, yaml_file))
        except Exception as e:
            log.error("Enable to load the auto-config, yaml file.\n%s" % str(e))
            auto_conf = {}
        # extract the supported image list
        images = auto_conf.get('docker_images', [])
        for image in images:
            auto_conf_images[image] = check_name
    return auto_conf_images
