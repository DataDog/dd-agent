# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# std
import glob
import os

#3p
import re
import simplejson as json

# project
from util import NoInstancesFound, check_yaml
from config import (
    load_check_directory,
    get_confd_path
)
from utils.hostname import get_hostname
from utils.dockerutil import DockerUtil
from utils.service_discovery.config_stores import get_config_store, SD_CONFIG_BACKENDS, TRACE_CONFIG


def configcheck():
    all_valid = True
    for conf_path in glob.glob(os.path.join(get_confd_path(), "*.yaml")):
        basename = os.path.basename(conf_path)
        try:
            check_yaml(conf_path)
        except NoInstancesFound as e:
            print "%s contains warning:\n    %s" % (basename, e)
        except Exception as e:
            all_valid = False
            print "%s contains errors:\n    %s" % (basename, e)
        else:
            print "%s is valid" % basename
    if all_valid:
        print "All yaml files passed. You can now run the Datadog agent."
        return 0
    else:
        print("Fix the invalid yaml files above in order to start the Datadog agent. "
              "A useful external tool for yaml parsing can be found at "
              "http://yaml-online-parser.appspot.com/")
        return 1


def sd_configcheck(agentConfig):
    if agentConfig.get('service_discovery', False):
        # set the TRACE_CONFIG flag to True to make load_check_directory return
        # the source of config objects.
        # Then call load_check_directory here and pass the result to get_sd_configcheck
        # to avoid circular imports
        agentConfig[TRACE_CONFIG] = True
        configs = {
            # check_name: (config_source, config)
        }
        print("\nLoading check configurations...\n\n")
        configs = load_check_directory(agentConfig, get_hostname(agentConfig))
        get_sd_configcheck(agentConfig, configs)

def agent_container_inspect():
    # Self inspection based on cgroups
    # On all platforms, the container ID is the last part of the path.
    REGEX_PATTERN = '(.*/)+([a-z0-9]{64})$'

    dockerutil = DockerUtil()
    cgroup_path = '/proc/self/cgroup'
    container_id = None

    with open(cgroup_path, 'r') as f:
        for ind in f:
            id_match = re.search(REGEX_PATTERN, ind)
            if id_match:
                container_id = id_match.group(2)
                break
    if container_id is None:
        print("The container_id could not be found. Refer to the docker log of the container running the agent")
        return 1
    try:
        inspect = dockerutil.inspect_container(container_id)
        key_indices = [i for i, k in enumerate(inspect['Config']['Env']) if 'API_KEY' in k]
        for ind in key_indices:
            inspect['Config']['Env'][ind] = '%s=%s' % (inspect['Config']['Env'][ind].split('=', 1)[0], 'redacted')
        print json.dumps(inspect, indent=4)
        return 0
    except Exception as e:
        print "Could not inspect container: %s" % e


def get_sd_configcheck(agentConfig, configs):
    """Trace how the configuration objects are loaded and from where.
        Also print containers detected by the agent and templates from the config store."""
    print("\nSource of the configuration objects built by the agent:\n")
    for check_name, config in configs.iteritems():
        print('Check "%s":\n  source --> %s\n  config --> %s\n' %
              (check_name, config[0], json.dumps(config[1], indent=2)))

    try:
        print_containers()
    except Exception:
        print("Failed to collect containers info.")

    try:
        print_templates(agentConfig)
    except Exception:
        print("Failed to collect configuration templates.")


def print_containers():
    dockerutil = DockerUtil()
    containers = dockerutil.client.containers()
    print("\nContainers info:\n")
    print("Number of containers found: %s" % len(containers))
    for co in containers:
        c_id = 'ID: %s' % co.get('Id')[:12]
        c_image = 'image: %s' % dockerutil.image_name_extractor(co)
        c_name = 'name: %s' % dockerutil.container_name_extractor(co)[0]
        print("\t- %s %s %s" % (c_id, c_image, c_name))
    print('\n')


def print_templates(agentConfig):
    if agentConfig.get('sd_config_backend') in SD_CONFIG_BACKENDS:
        print("Configuration templates:\n")
        templates = {}
        sd_template_dir = agentConfig.get('sd_template_dir')
        config_store = get_config_store(agentConfig)
        try:
            templates = config_store.dump_directory(sd_template_dir)
        except Exception as ex:
            print("Failed to extract configuration templates from the backend:\n%s" % str(ex))

        for ident, tpl in templates.iteritems():
            print(
                "- Identifier %s:\n\tcheck names: %s\n\tinit_configs: %s\n\tinstances: %s" % (
                    ident,
                    json.dumps(json.loads(tpl.get('check_names')), indent=2),
                    json.dumps(json.loads(tpl.get('init_configs')), indent=2),
                    json.dumps(json.loads(tpl.get('instances')), indent=2),
                )
            )
