# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# std
import logging
import simplejson as json

# project
from utils.dockerutil import DockerUtil
from utils.kubeutil import KubeUtil, is_k8s
from utils.service_discovery.abstract_sd_backend import AbstractSDBackend
from utils.service_discovery.config_stores import get_config_store, TRACE_CONFIG

DATADOG_ID = 'com.datadoghq.sd.check.id'
log = logging.getLogger(__name__)


class SDDockerBackend(AbstractSDBackend):
    """Docker-based service discovery"""

    def __init__(self, agentConfig):
        self.docker_client = DockerUtil().client
        if is_k8s():
            self.kubeutil = KubeUtil()

        try:
            self.config_store = get_config_store(agentConfig=agentConfig)
        except Exception as e:
            log.error('Failed to instantiate the config store client. '
                      'Auto-config only will be used. %s' % str(e))
            agentConfig['sd_config_backend'] = None
            self.config_store = get_config_store(agentConfig=agentConfig)

        self.VAR_MAPPING = {
            'host': self._get_host,
            'port': self._get_ports,
            'tags': self._get_additional_tags,
        }
        AbstractSDBackend.__init__(self, agentConfig)

    def _get_host(self, container_inspect):
        """Extract the host IP from a docker inspect object, or the kubelet API."""
        ip_addr = container_inspect.get('NetworkSettings', {}).get('IPAddress')
        if not ip_addr:
            if not is_k8s():
                return
            # kubernetes case
            log.debug("Didn't find the IP address for container %s (%s), using the kubernetes way." %
                      (container_inspect.get('Id', '')[:12], container_inspect.get('Config', {}).get('Image', '')))
            pod_list = self.kubeutil.retrieve_pods_list().get('items', [])
            c_id = container_inspect.get('Id')
            for pod in pod_list:
                pod_ip = pod.get('status', {}).get('podIP')
                if pod_ip is None:
                    continue
                else:
                    c_statuses = pod.get('status', {}).get('containerStatuses', [])
                    for status in c_statuses:
                        # compare the container id with those of containers in the current pod
                        if c_id == status.get('containerID', '').split('//')[-1]:
                            ip_addr = pod_ip

        return ip_addr

    def _get_ports(self, container_inspect):
        """Extract a list of available ports from a docker inspect object. Sort them numerically."""
        c_id = container_inspect.get('Id', '')
        try:
            ports = map(lambda x: x.split('/')[0], container_inspect['NetworkSettings']['Ports'].keys())
        except (IndexError, KeyError, AttributeError):
            log.debug("Didn't find the port for container %s (%s), trying the kubernetes way." %
                      (c_id[:12], container_inspect.get('Config', {}).get('Image', '')))
            # first we try to get it from the docker API
            # it works if the image has an EXPOSE instruction
            ports = map(lambda x: x.split('/')[0], container_inspect['Config'].get('ExposedPorts', {}).keys())
            # if it failed, try with the kubernetes API
            if not ports and is_k8s():
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
        return ports

    def get_tags(self, c_inspect):
        """Extract useful tags from docker or platform APIs. These are collected by default."""
        tags = []
        if is_k8s():
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

    def _get_additional_tags(self, container_inspect):
        tags = []
        if is_k8s():
            pod_metadata = self._get_kube_config(container_inspect.get('Id'), 'metadata')
            pod_spec = self._get_kube_config(container_inspect.get('Id'), 'spec')
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
                        conflict_init_msg = 'Different versions of `init_config` found for check {0}. ' \
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
                log.exception('Building config for container %s based on image %s using service'
                              ' discovery failed, leaving it alone.' % (cid[:12], image))
        return configs

    def get_config_id(self, image, labels):
        """Look for a DATADOG_ID label, return its value or the image name if missing"""
        return labels.get(DATADOG_ID) if DATADOG_ID in labels else image

    def _get_check_configs(self, c_id, identifier, trace_config=False):
        """Retrieve configuration templates and fill them with data pulled from docker and tags."""
        inspect = self.docker_client.inspect_container(c_id)
        config_templates = self._get_config_templates(identifier, trace_config=trace_config)
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

    def _get_config_templates(self, identifier, trace_config=False):
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
            identifier, auto_conf=auto_conf, trace_config=trace_config)
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
        """Add container tags to instance templates and build a """
        """dict from template variable names and their values."""
        var_values = {}

        # add default tags to the instance
        if tags:
            tags += instance_tpl.get('tags', [])
            instance_tpl['tags'] = list(set(tags))

        for v in variables:
            # variables can be suffixed with an index in case a list is found
            var_parts = v.split('_')
            if var_parts[0] in self.VAR_MAPPING:
                try:
                    res = self.VAR_MAPPING[var_parts[0]](inspect)
                    if not res:
                        raise ValueError("Invalid value for variable %s." % var_parts[0])
                    # if an index is found in the variable, use it to select a value
                    if len(var_parts) > 1 and isinstance(res, list) and int(var_parts[-1]) < len(res):
                        var_values[v] = res[int(var_parts[-1])]
                    # if no valid index was found but we have a list, return the last element
                    elif isinstance(res, list):
                        var_values[v] = res[-1]
                    else:
                        var_values[v] = res
                except Exception as ex:
                    log.error("Could not find a value for the template variable %s: %s" % (v, str(ex)))
            else:
                log.error("No method was found to interpolate template variable %s." % v)

        return instance_tpl, var_values
