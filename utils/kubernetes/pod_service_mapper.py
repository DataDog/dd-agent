# (C) Datadog, Inc. 2015-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict
import logging

log = logging.getLogger('collector')

class PodServiceMapper:
    _service_cache_selectors = defaultdict(dict)   # {service_name:{selectors}}
    _service_cache_invalidated = True              # True to trigger service parsing
    _service_cache_last_event_resversion = -1      # last event ressource version

    _pod_labels_cache = defaultdict(dict)          # {pod_uid:{label}}
    _pod_services_mapping = defaultdict(list)      # {pod_uid:[service_name]}

    def __init__(self, kubeutil_object):
        """
        Create a new service PodServiceMapper
        The apiserver requests are routed through the given KubeUtil instance
        """
        self.kube = kubeutil_object

    def _fill_services_cache(self):
        """
        Get the list of services from the kubelet API and store the label selector dicts.
        The cache is to be invalidated by the user class by calling check_services_cache_freshness
        """
        try:
            if self._service_cache_last_event_resversion == -1:
                self._service_cache_invalidated = False
                # Retrieving latest service event number with check_services_cache_freshness dry run
                self.check_services_cache_freshness()
            reply = self.kube.retrieve_json_auth(self.kube.kubernetes_api_url + '/services')
            self._service_cache_selectors = defaultdict(dict)
            for service in reply.get('items', []):
                name = service.get('metadata', {}).get('name', '')
                selector = service.get('spec', {}).get('selector', {})
                if len(name) and len(selector):
                    self._service_cache_selectors[name] = selector
            self._service_cache_invalidated = False
            log.warning(self._service_cache_selectors)
        except Exception as e:
            log.exception('Unable to read service list from apiserver: %s', e)
            self._service_cache_selectors = defaultdict(dict)
            self._service_cache_invalidated = False

    def check_services_cache_freshness(self):
        """
        Entry point for sd_docker_backend to check whether to invalidate the cached services
        For now, we remove the whole cache as the fill_service_cache logic
        doesn't handle partial lookups

        We use the event's resourceVersion, as using the service's version wouldn't catch deletion
        """

        # Don't check if cache is already invalidated
        if self._service_cache_invalidated:
            return

        lastestVersion = None
        invalidate = False
        try:
            reply = self.kube.retrieve_json_auth(self.kube.kubernetes_api_url + '/events',
                params={'fieldSelector': 'involvedObject.kind=Service'})
            for event in reply.get('items', []):
                version = int(event.get('metadata', {}).get('resourceVersion', None))
                if version > self._service_cache_last_event_resversion:
                    invalidate = True
                    lastestVersion = max(lastestVersion, version)
            if invalidate:
                self._service_cache_last_event_resversion = lastestVersion
                self._service_cache_invalidated = True
                log.debug("Flushing services cache triggered by resourceVersion %d", lastestVersion)
        except Exception as e:
            log.warning("Exception while parsing service events, not invalidating cache: %s", e)

    def match_services_for_pod(self, pod_metadata, refresh=False):
        """
        Match the pods labels with services' label selectors to determine the list
        of services that point to that pod. Returns an array of service names.

        Pass refresh=True if you want to bypass the cached cid->services mapping (after a service change)
        """
        matches = []

        try:
            # Fail intentionally if no uid
            pod_id = pod_metadata['uid']

            # Mapping cache lookup
            if (refresh is False and pod_id in self._pod_services_mapping):
                log.debug("Returning cache for pod %s: pod_id %s", pod_metadata.get('name'), pod_id)
                return self._pod_services_mapping[pod_id]

            if (self._service_cache_invalidated is True):
                self._fill_services_cache()
            for name, label_selectors in self._service_cache_selectors.iteritems():
                if self._does_pod_fulfill_selectors(pod_metadata.get('labels', {}), label_selectors):
                    matches.append(name)
            self._pod_services_mapping[pod_id] = matches
        except Exception as e:
            log.exception('Error while matching k8s services: %s', e)
        finally:
            log.debug("Services match for pod %s: %s", pod_metadata.get('name'), str(matches))
            return matches

    @classmethod
    def _does_pod_fulfill_selectors(cls, pod_labels, label_selectors):
        """
        Allows to check if a pod fulfills the label_selectors for a service by
        iterating over the dictionnary.
        If the pod's label or label_selectors are empty, the match is assumed false
        Note: Job, Deployment, ReplicaSet and DaemonSet introduce matchExpressions
        that are not handled by this method
        """
        if len(pod_labels) == 0 or len(label_selectors) == 0:
            return False
        for label, value in label_selectors.iteritems():
            if pod_labels.get(label, '') != value:
                return False
        return True
