# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# std
import logging
import simplejson as json

# 3rd party
from docker.errors import NullResource, NotFound

# project
from utils.dockerutil import DockerUtil
from utils.kubernetes import KubeUtil
from utils.platform import Platform
from utils.service_discovery.abstract_sd_backend import AbstractSDBackend
from utils.service_discovery.config_stores import get_config_store, TRACE_CONFIG

DATADOG_ID = 'com.datadoghq.sd.check.id'
K8S_ANNOTATION_CHECK_NAMES = 'com.datadoghq.sd/check_names'
K8S_ANNOTATION_INIT_CONFIGS = 'com.datadoghq.sd/init_configs'
K8S_ANNOTATION_INSTANCES = 'com.datadoghq.sd/instances'
log = logging.getLogger(__name__)


class SDDockerBackend(AbstractSDBackend):
    """Docker-based service discovery"""

    def __init__(self, agentConfig):
        try:
            self.config_store = get_config_store(agentConfig=agentConfig)
        except Exception as e:
            log.error('Failed to instantiate the config store client. '
                      'Auto-config only will be used. %s' % str(e))
            agentConfig['sd_config_backend'] = None
            self.config_store = get_config_store(agentConfig=agentConfig)

        self.docker_client = DockerUtil(config_store=self.config_store).client
        if Platform.is_k8s():
            self.kubeutil = KubeUtil()

        self.VAR_MAPPING = {
            'host': self._get_host_address,
            'port': self._get_port,
            'tags': self._get_additional_tags,
        }

        AbstractSDBackend.__init__(self, agentConfig)

    def update_checks(self, changed_containers):
        conf_reload_set = set()
        for id_ in changed_containers:
            try:
                inspect = self.docker_client.inspect_container(id_)
            except (NullResource, NotFound):
                inspect = {}

            checks = self._get_checks_from_inspect(inspect)
            conf_reload_set.update(set(checks))

        if conf_reload_set:
            self.reload_check_configs = conf_reload_set

    def _get_checks_from_inspect(self, inspect):
        """Get the list of checks applied to a container from the identifier_to_checks cache in the config store.
        Use the DATADOG_ID label or the image."""
        identifier = inspect.get('Config', {}).get('Labels', {}).get(DATADOG_ID) or \
            inspect.get('Config', {}).get('Image')
        annotations = (self._get_kube_config(inspect.get('Id'), 'metadata') or {}).get('annotations') if Platform.is_k8s() else None

        return self.config_store.get_checks_to_refresh(identifier, kube_annotations=annotations)

    def _get_host_address(self, c_inspect, tpl_var):
        """Extract the container IP from a docker inspect object, or the kubelet API."""
        c_id, c_img = c_inspect.get('Id', ''), c_inspect.get('Config', {}).get('Image', '')

        networks = c_inspect.get('NetworkSettings', {}).get('Networks') or {}
        ip_dict = {}
        for net_name, net_desc in networks.iteritems():
            ip = net_desc.get('IPAddress')
            if ip:
                ip_dict[net_name] = ip
        ip_addr = self._extract_ip_from_networks(ip_dict, tpl_var)
        if ip_addr:
            return ip_addr

        # try to get the bridge (default) IP address
        log.debug("No IP address was found in container %s (%s) "
            "networks, trying with the IPAddress field" % (c_id[:12], c_img))
        ip_addr = c_inspect.get('NetworkSettings', {}).get('IPAddress')
        if ip_addr:
            return ip_addr

        if Platform.is_k8s():
            # kubernetes case
            log.debug("Couldn't find the IP address for container %s (%s), "
                      "using the kubernetes way." % (c_id[:12], c_img))
            pod_list = self.kubeutil.retrieve_pods_list().get('items', [])
            for pod in pod_list:
                pod_ip = pod.get('status', {}).get('podIP')
                if pod_ip is None:
                    continue
                else:
                    c_statuses = pod.get('status', {}).get('containerStatuses', [])
                    for status in c_statuses:
                        # compare the container id with those of containers in the current pod
                        if c_id == status.get('containerID', '').split('//')[-1]:
                            return pod_ip

        log.error("No IP address was found for container %s (%s)" % (c_id[:12], c_img))
        return None

    def _extract_ip_from_networks(self, ip_dict, tpl_var):
        """Extract a single IP from a dictionary made of network names and IPs."""
        if not ip_dict:
            return None
        tpl_parts = tpl_var.split('_', 1)

        # no specifier
        if len(tpl_parts) < 2:
            log.warning("No key was passed for template variable %s." % tpl_var)
            return self._get_fallback_ip(ip_dict)
        else:
            res = ip_dict.get(tpl_parts[-1])
            if res is None:
                log.warning("The key passed for template variable %s was not found." % tpl_var)
                return self._get_fallback_ip(ip_dict)
            else:
                return res

    def _get_fallback_ip(self, ip_dict):
        """try to pick the bridge key, falls back to the value of the last key"""
        if 'bridge' in ip_dict:
            log.warning("Using the bridge network.")
            return ip_dict['bridge']
        else:
            last_key = sorted(ip_dict.iterkeys())[-1]
            log.warning("Trying with the last (sorted) network: '%s'." % last_key)
            return ip_dict[last_key]

    def _get_port(self, container_inspect, tpl_var):
        """Extract a port from a container_inspect or the k8s API given a template variable."""
        c_id = container_inspect.get('Id', '')

        try:
            ports = map(lambda x: x.split('/')[0], container_inspect['NetworkSettings']['Ports'].keys())
        except (IndexError, KeyError, AttributeError):
            # try to get ports from the docker API. Works if the image has an EXPOSE instruction
            ports = map(lambda x: x.split('/')[0], container_inspect['Config'].get('ExposedPorts', {}).keys())

            # if it failed, try with the kubernetes API
            if not ports and Platform.is_k8s():
                log.debug("Didn't find the port for container %s (%s), trying the kubernetes way." %
                          (c_id[:12], container_inspect.get('Config', {}).get('Image', '')))
                co_statuses = self._get_kube_config(c_id, 'status').get('containerStatuses', [])
                c_name = None
                for co in co_statuses:
                    if co.get('containerID', '').split('//')[-1] == c_id:
                        c_name = co.get('name')
                        break
                containers = self._get_kube_config(c_id, 'spec').get('containers', [])
                for co in containers:
                    if co.get('name') == c_name:
                        ports = map(lambda x: str(x.get('containerPort')), co.get('ports', []))
        ports = sorted(ports, key=lambda x: int(x))
        return self._extract_port_from_list(ports, tpl_var)

    def _extract_port_from_list(self, ports, tpl_var):
        if not ports:
            return None

        tpl_parts = tpl_var.split('_', 1)

        if len(tpl_parts) == 1:
            log.debug("No index was passed for template variable %s. "
                      "Trying with the last element." % tpl_var)
            return ports[-1]

        try:
            idx = tpl_parts[-1]
            return ports[int(idx)]
        except ValueError:
            log.error("Port index is not an integer. Using the last element instead.")
        except IndexError:
            log.error("Port index is out of range. Using the last element instead.")
        return ports[-1]

    def get_tags(self, c_inspect):
        """Extract useful tags from docker or platform APIs. These are collected by default."""
        tags = []
        if Platform.is_k8s():
            pod_metadata = self._get_kube_config(c_inspect.get('Id'), 'metadata')

            if pod_metadata is None:
                log.warning("Failed to fetch pod metadata for container %s."
                            " Kubernetes tags may be missing." % c_inspect.get('Id', '')[:12])
                return []
            # get labels
            kube_labels = pod_metadata.get('labels', {})
            for label, value in kube_labels.iteritems():
                tags.append('%s:%s' % (label, value))

            # get replication controller
            created_by = json.loads(pod_metadata.get('annotations', {}).get('kubernetes.io/created-by', '{}'))
            if created_by.get('reference', {}).get('kind') == 'ReplicationController':
                tags.append('kube_replication_controller:%s' % created_by.get('reference', {}).get('name'))

            # get kubernetes namespace
            tags.append('kube_namespace:%s' % pod_metadata.get('namespace'))

        return tags

    def _get_additional_tags(self, container_inspect, *args):
        tags = []
        if Platform.is_k8s():
            pod_metadata = self._get_kube_config(container_inspect.get('Id'), 'metadata')
            pod_spec = self._get_kube_config(container_inspect.get('Id'), 'spec')
            if pod_metadata is None or pod_spec is None:
                log.warning("Failed to fetch pod metadata or pod spec for container %s."
                            " Additional Kubernetes tags may be missing." % container_inspect.get('Id', '')[:12])
                return []
            tags.append('node_name:%s' % pod_spec.get('nodeName'))
            tags.append('pod_name:%s' % pod_metadata.get('name'))
        return tags

    def _get_kube_config(self, c_id, key):
        """Get a part of a pod config from the kubernetes API"""
        pods = self.kubeutil.retrieve_pods_list().get('items', [])
        for pod in pods:
            c_statuses = pod.get('status', {}).get('containerStatuses', [])
            for status in c_statuses:
                if c_id == status.get('containerID', '').split('//')[-1]:
                    return pod.get(key, {})

    def get_configs(self):
        """Get the config for all docker containers running on the host."""
        configs = {}
        containers = [(
            container.get('Image'),
            container.get('Id'), container.get('Labels')
        ) for container in self.docker_client.containers()]

        # used by the configcheck agent command to trace where check configs come from
        trace_config = self.agentConfig.get(TRACE_CONFIG, False)

        for image, cid, labels in containers:
            try:
                # value of the DATADOG_ID tag or the image name if the label is missing
                identifier = self.get_config_id(image, labels)
                check_configs = self._get_check_configs(cid, identifier, trace_config=trace_config) or []
                for conf in check_configs:
                    if trace_config and conf is not None:
                        source, conf = conf

                    check_name, init_config, instance = conf
                    # build instances list if needed
                    if configs.get(check_name) is None:
                        if trace_config:
                            configs[check_name] = (source, (init_config, [instance]))
                        else:
                            configs[check_name] = (init_config, [instance])
                    else:
                        conflict_init_msg = 'Different versions of `init_config` found for check {}. ' \
                            'Keeping the first one found.'
                        if trace_config:
                            if configs[check_name][1][0] != init_config:
                                log.warning(conflict_init_msg.format(check_name))
                            configs[check_name][1][1].append(instance)
                        else:
                            if configs[check_name][0] != init_config:
                                log.warning(conflict_init_msg.format(check_name))
                            configs[check_name][1].append(instance)
            except Exception:
                log.exception('Building config for container %s based on image %s using service '
                              'discovery failed, leaving it alone.' % (cid[:12], image))
        return configs

    def get_config_id(self, image, labels):
        """Look for a DATADOG_ID label, return its value or the image name if missing"""
        return labels.get(DATADOG_ID) or image

    def _get_check_configs(self, c_id, identifier, trace_config=False):
        """Retrieve configuration templates and fill them with data pulled from docker and tags."""
        inspect = self.docker_client.inspect_container(c_id)
        annotations = (self._get_kube_config(inspect.get('Id'), 'metadata') or {}).get('annotations') if Platform.is_k8s() else None
        config_templates = self._get_config_templates(identifier, trace_config=trace_config, kube_annotations=annotations)
        if not config_templates:
            log.debug('No config template for container %s with identifier %s. '
                      'It will be left unconfigured.' % (c_id[:12], identifier))
            return None

        check_configs = []
        tags = self.get_tags(inspect)
        for config_tpl in config_templates:
            if trace_config:
                source, config_tpl = config_tpl
            check_name, init_config_tpl, instance_tpl, variables = config_tpl

            # insert tags in instance_tpl and process values for template variables
            instance_tpl, var_values = self._fill_tpl(inspect, instance_tpl, variables, tags)

            tpl = self._render_template(init_config_tpl or {}, instance_tpl or {}, var_values)
            if tpl and len(tpl) == 2:
                init_config, instance = tpl
                if trace_config:
                    check_configs.append((source, (check_name, init_config, instance)))
                else:
                    check_configs.append((check_name, init_config, instance))

        return check_configs

    def _get_config_templates(self, identifier, trace_config=False, kube_annotations=None):
        """Extract config templates for an identifier from a K/V store and returns it as a dict object."""
        config_backend = self.agentConfig.get('sd_config_backend')
        templates = []
        if config_backend is None:
            auto_conf = True
            log.warning('No supported configuration backend was provided, using auto-config only.')
        else:
            auto_conf = False

        # format: [('ident', {init_tpl}, {instance_tpl})] without trace_config
        # or      [(source, ('ident', {init_tpl}, {instance_tpl}))] with trace_config
        raw_tpls = self.config_store.get_check_tpls(
            identifier, auto_conf=auto_conf, trace_config=trace_config, kube_annotations=kube_annotations)
        for tpl in raw_tpls:
            if trace_config and tpl is not None:
                # each template can come from either auto configuration or user-supplied templates
                source, tpl = tpl
            if tpl is not None and len(tpl) == 3:
                check_name, init_config_tpl, instance_tpl = tpl
            else:
                log.debug('No template was found for identifier %s, leaving it alone.' % identifier)
                return None
            try:
                # build a list of all variables to replace in the template
                variables = self.PLACEHOLDER_REGEX.findall(str(init_config_tpl)) + \
                    self.PLACEHOLDER_REGEX.findall(str(instance_tpl))
                variables = map(lambda x: x.strip('%'), variables)
                if not isinstance(init_config_tpl, dict):
                    init_config_tpl = json.loads(init_config_tpl or '{}')
                if not isinstance(instance_tpl, dict):
                    instance_tpl = json.loads(instance_tpl or '{}')
            except json.JSONDecodeError:
                log.exception('Failed to decode the JSON template fetched for check {0}. Its configuration'
                              ' by service discovery failed for ident  {1}.'.format(check_name, identifier))
                return None

            if trace_config:
                templates.append((source, (check_name, init_config_tpl, instance_tpl, variables)))
            else:
                templates.append((check_name, init_config_tpl, instance_tpl, variables))

        return templates

    def _fill_tpl(self, inspect, instance_tpl, variables, tags=None):
        """Add container tags to instance templates and build a
           dict from template variable names and their values."""
        var_values = {}
        c_id, c_image = inspect.get('Id', ''), inspect.get('Config', {}).get('Image', '')

        # add default tags to the instance
        if tags:
            tpl_tags = instance_tpl.get('tags', [])
            tags += tpl_tags if isinstance(tpl_tags, list) else [tpl_tags]
            instance_tpl['tags'] = list(set(tags))

        for var in variables:
            # variables can be suffixed with an index in case several values are found
            if var.split('_')[0] in self.VAR_MAPPING:
                try:
                    res = self.VAR_MAPPING[var.split('_')[0]](inspect, var)
                    if res is None:
                        raise ValueError("Invalid value for variable %s." % var)
                    var_values[var] = res
                except Exception as ex:
                    log.error("Could not find a value for the template variable %s for container %s "
                              "(%s): %s" % (var, c_id[:12], c_image, str(ex)))
            else:
                log.error("No method was found to interpolate template variable %s for container %s "
                          "(%s)." % (var, c_id[:12], c_image))

        return instance_tpl, var_values
