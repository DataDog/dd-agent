# (C) Datadog, Inc. 2015-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict
import logging

log = logging.getLogger('collector')


class PodServiceMapper:
    def __init__(self, kubeutil_object):
        """
        Create a new service PodServiceMapper
        The apiserver requests are routed through the given KubeUtil instance
        """
        self.kube = kubeutil_object
        self._event_retriever = self.kube.get_event_retriever(kinds=['Service'])
        self._service_cache_selectors = defaultdict(dict)   # {service_uid:{selectors}}
        self._service_cache_names = {}                      # {service_uid:service_name
        self._service_cache_invalidated = False             # True to trigger service parsing
        self._pod_labels_cache = defaultdict(dict)          # {pod_uid:{label}}
        self._pod_services_mapping = defaultdict(list)      # {pod_uid:[service_uid]}

        # Consume past events
        self.check_services_cache_freshness()
        self._service_cache_invalidated = True

    def _fill_services_cache(self):
        """
        Get the list of services from the kubelet API and store the label selector dicts.
        The cache is to be invalidated by the user class by calling check_services_cache_freshness
        """
        try:
            reply = self.kube.retrieve_json_auth(self.kube.kubernetes_api_url + '/services')
            self._service_cache_selectors = defaultdict(dict)
            self._service_cache_names = {}
            for service in reply.get('items', []):
                uid = service.get('metadata', {}).get('uid', '')
                name = service.get('metadata', {}).get('name', '')
                selector = service.get('spec', {}).get('selector', {})
                if uid == '' or len(selector) == 0:
                    continue
                self._service_cache_names[uid] = name
                self._service_cache_selectors[uid] = selector
            self._service_cache_invalidated = False
        except Exception as e:
            log.exception('Unable to read service list from apiserver: %s', e)
            self._service_cache_selectors = defaultdict(dict)
            self._service_cache_names = {}
            self._service_cache_invalidated = False

    def check_services_cache_freshness(self):
        """
        Entry point for sd_docker_backend to check whether to invalidate the cached services
        For now, we remove the whole cache as the fill_service_cache logic
        doesn't handle partial lookups
        """

        # Don't check if cache is already invalidated
        if self._service_cache_invalidated:
            return

        try:
            if self._event_retriever.get_event_array():
                self._service_cache_invalidated = True
        except Exception as e:
            log.warning("Exception while parsing service events, not invalidating cache: %s", e)

    def match_services_for_pod(self, pod_metadata, refresh=False, names=False):
        """
        Match the pods labels with services' label selectors to determine the list
        of services that point to that pod. Returns an array of service uids or names.

        Pass names=True if you want the service name instead of the uids
        Pass refresh=True if you want to bypass the cached cid->services mapping (after a service change)
        """
        matches = []

        try:
            # Fail intentionally if no uid
            pod_id = pod_metadata['uid']
            pod_labels = pod_metadata.get('labels', {})

            # Keep pod labels in cache for service->pod search
            self._pod_labels_cache[pod_id] = pod_labels

            # Mapping cache lookup
            if (refresh is False and pod_id in self._pod_services_mapping):
                matches = self._pod_services_mapping[pod_id]
            else:
                if (self._service_cache_invalidated is True):
                    self._fill_services_cache()
                for service_uid, label_selectors in self._service_cache_selectors.iteritems():
                    if self._does_pod_fulfill_selectors(pod_labels, label_selectors):
                        matches.append(service_uid)
                self._pod_services_mapping[pod_id] = matches

            if names:
                return [self._service_cache_names.get(uid) for uid in matches]
            else:
                return matches
        except Exception as e:
            log.exception('Error while matching k8s services: %s', e)
            return []

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

    def search_pods_for_service(self, service_uid):
        """
        Returns the [pod_uid] list matching a service uid.
        Uses the service selector and pod labels caches, but not _pod_services_mapping
        """
        matches = []

        try:
            if (self._service_cache_invalidated is True):
                self._fill_services_cache()

            if service_uid not in self._service_cache_selectors:
                log.debug("No selectors cached for service %s, skipping search", service_uid)
                return []

            for pod_uid, labels in self._pod_labels_cache.iteritems():
                if self._does_pod_fulfill_selectors(labels, self._service_cache_selectors[service_uid]):
                    matches.append(pod_uid)
        except Exception as e:
            log.exception('Error while matching k8s services: %s', e)
        finally:
            log.debug("Pods match for service %s: %s", service_uid, str(matches))
            return matches

    def process_events(self, event_array):
        """
        Reads a list of kube events, invalidates caches and and computes a set
        of pods impacted by the changes, to refresh service discovery
        """
        pod_uids = set()
        service_cache_checked = False

        for event in event_array:
            kind = event.get('involvedObject', {}).get('kind', None)
            reason = event.get('reason', None)
            # Possible values in kubernetes/pkg/kubelet/events/event.go
            if kind == 'Pod' and reason == 'Killing':
                pod_id = event.get('involvedObject', {}).get('uid', None)
                if pod_id in self._pod_labels_cache:
                    del self._pod_labels_cache[pod_id]
                if pod_id in self._pod_services_mapping:
                    del self._pod_services_mapping[pod_id]

            elif kind == 'Service':
                service_uid = event.get('involvedObject', {}).get('uid', None)

                if service_cache_checked is False:
                    self.check_services_cache_freshness()
                    service_cache_checked = True

                # Possible values in kubernetes/pkg/controller/service/servicecontroller.go
                if reason == 'DeletedLoadBalancer':
                    for pod, services in self._pod_services_mapping.iteritems():
                        if service_uid in services:
                            services.remove(service_uid)
                            pod_uids.add(pod)
                elif reason == 'CreatedLoadBalancer' or reason == 'UpdatedLoadBalancer':
                    for pod in self.search_pods_for_service(service_uid):
                        if (pod in self._pod_services_mapping and
                                service_uid not in self._pod_services_mapping[pod]):
                            self._pod_services_mapping[pod].append(service_uid)
                            pod_uids.add(pod)

        return pod_uids
