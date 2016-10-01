# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# std
from collections import defaultdict
import logging
import simplejson as json
from os import path

# 3p
from requests.packages.urllib3.exceptions import TimeoutError

# project
from utils.checkfiles import get_check_class, get_auto_conf, get_auto_conf_images
from utils.singleton import Singleton

log = logging.getLogger(__name__)

CONFIG_FROM_AUTOCONF = 'auto-configuration'
CONFIG_FROM_FILE = 'YAML file'
CONFIG_FROM_TEMPLATE = 'template'
CONFIG_FROM_KUBE = 'Kubernetes Pod Annotation'
TRACE_CONFIG = 'trace_config'  # used for tracing config load by service discovery
CHECK_NAMES = 'check_names'
INIT_CONFIGS = 'init_configs'
INSTANCES = 'instances'
KUBE_ANNOTATIONS = 'kube_annotations'
KUBE_ANNOTATION_PREFIX = 'com.datadoghq.sd/'


class KeyNotFound(Exception):
    pass


class AbstractConfigStore(object):
    """Singleton for config stores"""
    __metaclass__ = Singleton

    previous_config_index = None

    def __init__(self, agentConfig):
        self.client = None
        self.agentConfig = agentConfig
        self.settings = self._extract_settings(agentConfig)
        self.client = self.get_client()
        self.sd_template_dir = agentConfig.get('sd_template_dir')
        self.auto_conf_images = get_auto_conf_images(agentConfig)

        # Cache mapping identifiers to their templates;
        # ident: [[check_names], [init_config_tpls], [instance_tpls]]
        # Used by dockerutil to determine which check to reload based on the image linked to an event
        # Also used by AbstractConfigStore to get templates and avoid querying the kv store.
        #
        # it is invalidated entirely when a change is detected in the kv store.
        #
        # this is a defaultdict(lambda: [[]] * 3) and some calls to it rely on this property
        # so if you're planning on changing that, track its references
        self.identifier_to_tpls = self._populate_identifier_to_tpls(trace_config=TRACE_CONFIG in agentConfig)

    @classmethod
    def _drop(cls):
        """Drop the config store instance. This is only used for testing."""
        if cls in cls._instances:
            del cls._instances[cls]

    def _extract_settings(self, config):
        raise NotImplementedError()

    def get_client(self, reset=False):
        raise NotImplementedError()

    def client_read(self, path, **kwargs):
        raise NotImplementedError()

    def dump_directory(self, path, **kwargs):
        raise NotImplementedError()

    def _populate_identifier_to_tpls(self, **kwargs):
        """Populate the identifier_to_tpls cache with templates pulled
        from the config store and from the auto-config folder"""
        identifier_to_tpls = defaultdict(lambda: [[]] * 3)
        # config store templates
        try:
            templates = self.client_read(self.sd_template_dir.lstrip('/'), all=True)
        except (NotImplementedError, TimeoutError, AttributeError):
            templates = []
        for tpl in templates:
            split_key = tpl[0].split('/')
            ident, var = split_key[-2], split_key[-1]
            if var == CHECK_NAMES:
                identifier_to_tpls[ident][0] = json.loads(tpl[1])
            elif var == INIT_CONFIGS:
                identifier_to_tpls[ident][1] = json.loads(tpl[1])
            elif var == INSTANCES:
                identifier_to_tpls[ident][2] = json.loads(tpl[1])

        if kwargs.get('trace_config'):
            for ident in identifier_to_tpls:
                identifier_to_tpls[ident] = (CONFIG_FROM_TEMPLATE, identifier_to_tpls[ident])

        # auto-config templates
        templates = get_auto_conf_images(self.agentConfig, full_tpl=True)
        for image, tpl in templates.iteritems():
            check_name, init_tpl, instance_tpl = tpl
            # there is already a user-defined template for this image
            if image in identifier_to_tpls:
                if check_name in identifier_to_tpls[image][0] or \
                   identifier_to_tpls[image][0] == CONFIG_FROM_TEMPLATE:
                    continue
                identifier_to_tpls[image][0].append(check_name)
                identifier_to_tpls[image][1].append(init_tpl)
                identifier_to_tpls[image][2].append(instance_tpl)
            else:
                identifier_to_tpls[image][0] = [check_name]
                identifier_to_tpls[image][1] = [init_tpl or {}]
                # no list wrapping because auto_conf files already have a list of instances
                identifier_to_tpls[image][2] = instance_tpl or [{}]

        if kwargs.get('trace_config'):
            for ident in identifier_to_tpls:
                tpl = identifier_to_tpls[ident]
                if not isinstance(tpl, tuple):
                    identifier_to_tpls[ident] = (CONFIG_FROM_AUTOCONF, identifier_to_tpls[ident])

        return identifier_to_tpls

    def _get_kube_config(self, identifier, kube_annotations):
        try:
            check_names = json.loads(kube_annotations[KUBE_ANNOTATION_PREFIX + CHECK_NAMES])
            init_config_tpls = json.loads(kube_annotations[KUBE_ANNOTATION_PREFIX + INIT_CONFIGS])
            instance_tpls = json.loads(kube_annotations[KUBE_ANNOTATION_PREFIX + INSTANCES])
            return [check_names, init_config_tpls, instance_tpls]
        except KeyError:
            return None
        except json.JSONDecodeError:
            log.exception('Could not decode the JSON configuration template '
                          'for the kubernetes pod with ident %s...' % identifier)
            return None

    def _get_auto_config(self, image_name):
        ident = self._get_image_ident(image_name)
        if ident in self.auto_conf_images:
            check_name = self.auto_conf_images[ident][0]

            # get the check class to verify it matches
            check = get_check_class(self.agentConfig, check_name)
            if check is None:
                log.info("Could not find an auto configuration template for %s."
                         " Leaving it unconfigured." % image_name)
                return None

            auto_conf = get_auto_conf(self.agentConfig, check_name)
            init_config, instances = auto_conf.get('init_config', {}), auto_conf.get('instances', [])
            return (check_name, init_config, instances[0] or {})

        return None

    def get_checks_to_refresh(self, identifier, **kwargs):
        # get check names list
        to_check = set(self.identifier_to_tpls[identifier][0])
        kube_annotations = kwargs.get('kube_annotations')
        if kube_annotations:
            kube_config = self._get_kube_config(identifier, kube_annotations)
            if kube_config is not None:
                to_check.update(kube_config[0])

        return to_check

    def get_check_tpls(self, identifier, **kwargs):
        """Retrieve template configs for an identifier from the config_store or auto configuration."""
        trace_config = kwargs.get(TRACE_CONFIG, False)

        # this flag is used when no valid configuration store was provided
        # it makes the method skip directly to the auto_conf
        if kwargs.get('auto_conf') is True:
            # When not using a configuration store on kubernetes, check the pod
            # annotations for configs before falling back to autoconf.
            kube_annotations = kwargs.get(KUBE_ANNOTATIONS)
            if kube_annotations:
                kube_config = self._get_kube_config(identifier, kube_annotations)
                if kube_config is not None:
                    check_names, init_config_tpls, instance_tpls = kube_config
                    source = CONFIG_FROM_KUBE
                    return [(source, vs) if trace_config else vs
                            for vs in zip(check_names, init_config_tpls, instance_tpls)]

            # in auto config mode, identifier is the image name
            auto_config = self._get_auto_config(identifier)
            if auto_config is not None:
                source = CONFIG_FROM_AUTOCONF
                if trace_config:
                    return [(source, auto_config)]
                return [auto_config]
            else:
                log.debug('No auto config was found for image %s, leaving it alone.' % identifier)
                return []
        else:
            config = self.retrieve_config_tpl(identifier, trace_config=trace_config)
            if config:
                if trace_config:
                    source, check_names, init_config_tpls, instance_tpls = config
                else:
                    check_names, init_config_tpls, instance_tpls = config
            else:
                return []

        if len(check_names) != len(init_config_tpls) or len(check_names) != len(instance_tpls):
            log.error('Malformed configuration template: check_names, init_configs '
                      'and instances are not all the same length. Container with identifier {} '
                      'will not be configured by the service discovery'.format(identifier))
            return []

        # Try to update the identifier_to_tpls cache
        self._update_identifier_to_tpls(identifier, check_names, init_config_tpls, instance_tpls)

        return [(source, values) if trace_config else values
                for values in zip(check_names, init_config_tpls, instance_tpls)]

    def retrieve_config_tpl(self, identifier, **kwargs):
        """Try to read from the config store (or the cache), falls back to auto-config in case of failure."""
        trace_config = kwargs.get('trace_config', False)
        try:
            try:
                res = self._issue_read(identifier)
            except KeyNotFound:
                log.debug("Could not find directory {} in the config store, "
                          "trying to convert to the old format.".format(identifier))
                image_ident = self._get_image_ident(identifier)
                res = self._issue_read(image_ident)

            if trace_config and res:
                source, res = res

            if res and len(res) == 3:
                check_names, init_config_tpls, instance_tpls = res
            else:
                log.debug("Could not find directory {} in the config store, "
                          "trying to convert to the old format...".format(identifier))
                image_ident = self._get_image_ident(identifier)
                res = self._issue_read(image_ident)

                if trace_config and res:
                    source, res = res

                if res and len(res) == 3:
                    check_names, init_config_tpls, instance_tpls = res
                else:
                    raise KeyError
        except (KeyError, KeyNotFound, TimeoutError, json.JSONDecodeError) as ex:
            # this case is not expected, the agent can't reach the config store
            if isinstance(ex, TimeoutError):
                log.warning("Connection to the config backend timed out. Is it reachable?\n"
                            "Trying to auto-configure a check for the container with ident %s." % identifier)
            # the template is reachable but invalid
            elif isinstance(ex, json.JSONDecodeError):
                log.error('Could not decode the JSON configuration template '
                          'for the container with ident %s...' % identifier)
                return []
            else:
                log.debug('No config was found for container with identifier %s, leaving it alone.' % identifier)
                return []
        except Exception as ex:
            log.warning(
                'Fetching the value for {0} failed, this check will not be '
                'configured by the service discovery. Error: {1}'.format(identifier, str(ex)))
            return []
        if trace_config:
            return source, check_names, init_config_tpls, instance_tpls
        else:
            return check_names, init_config_tpls, instance_tpls

    def _get_image_ident(self, ident):
        """Extract an identifier from the image"""
        # if a custom image store is used there can be a port which adds a colon
        if ident.count(':') > 1:
            return ident.split(':')[1].split('/')[-1]
        # otherwise we just strip the tag and keep the image name
        else:
            return ident.split(':')[0].split('/')[-1]

    def _issue_read(self, identifier):
        """Query a full template for the config store for an identifier."""
        if identifier in self.identifier_to_tpls:
            return self.identifier_to_tpls[identifier]

        try:
            check_names = json.loads(
                self.client_read(path.join(self.sd_template_dir, identifier, CHECK_NAMES).lstrip('/')))
            init_config_tpls = json.loads(
                self.client_read(path.join(self.sd_template_dir, identifier, INIT_CONFIGS).lstrip('/')))
            instance_tpls = json.loads(
                self.client_read(path.join(self.sd_template_dir, identifier, INSTANCES).lstrip('/')))
            return [check_names, init_config_tpls, instance_tpls]
        except KeyError:
            return None

    def crawl_config_template(self):
        """Return whether or not configuration templates have changed since the previous crawl"""
        try:
            config_index = self.client_read(self.sd_template_dir.lstrip('/'), recursive=True, watch=True)
        except KeyNotFound:
            log.debug('Config template not found (normal if running on auto-config alone).'
                      ' Not Triggering a config reload.')
            return False
        except TimeoutError:
            msg = 'Request for the configuration template timed out.'
            raise Exception(msg)
        # Initialize the config index reference
        if self.previous_config_index is None:
            self.previous_config_index = config_index
            return False
        # Config has been modified since last crawl
        # in this case a full config reload is triggered and the identifier_to_tpls cache is rebuilt
        if config_index != self.previous_config_index:
            log.info('Detected an update in config templates, reloading check configs...')
            self.previous_config_index = config_index
            self.identifier_to_tpls = self._populate_identifier_to_tpls()
            return True
        return False

    def _update_identifier_to_tpls(self, identifier, check_names, init_tpl, instance_tpl):
        """Try to insert in the identifier_to_tpls cache the mapping between
           an identifier and its check names.
           This should very rarely happen.
           When/If it does we can correct the cache if the key was missing but not if there is a conflict."""
        if identifier not in self.identifier_to_tpls:
            self.identifier_to_tpls[identifier] = [check_names, init_tpl, instance_tpl]
        elif self.identifier_to_tpls[identifier][0] != check_names and \
                self.identifier_to_tpls[identifier][0] not in [CONFIG_FROM_TEMPLATE, CONFIG_FROM_AUTOCONF]:
            log.warning("Trying to cache template(s) for ident %s but a different value is already there. "
                        "Not updating." % identifier)
