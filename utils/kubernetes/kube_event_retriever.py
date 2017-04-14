class KubeEventRetriever:
    """
    Queries the apiserver for events of given kinds and namespaces
    and filters them on ressourceVersion to return only the new ones

    Best performance is achieved with only one namespace & one kind
    (server side-filtering), but multiple ns or kinds are supported
    via client-side filtering

    Needs a KubeUtil objet to route requests through
    Best way to get one is through KubeUtil.get_event_retriever()
    """
    def __init__(self, kubeutil_object, namespaces=None, kinds=None):
        self.kubeutil = kubeutil_object
        self.last_resversion = -1

        self.request_url = self.kubeutil.kubernetes_api_url + '/events'
        self.request_params = {}

        self.namespace_filter = None
        if isinstance(namespaces, basestring):
            self.request_url = "%s/namespaces/%s/events" % self.kubeutil.kubernetes_api_url, namespaces
        elif isinstance(namespaces, set) or isinstance(namespaces, list):
            if len(namespaces == 1):
                self.request_url = "%s/namespaces/%s/events" % self.kubeutil.kubernetes_api_url, namespaces[0]
            else:
                # Client-side filtering
                self.namespace_filter = set(namespaces)

        self.kind_filter = None
        if isinstance(kinds, basestring):
            self.request_url = "%s/namespaces/%s/events" % self.kubeutil.kubernetes_api_url, namespaces
            self.request_params['fieldSelector'] = 'involvedObject.kind=' + kinds
        elif isinstance(kinds, set) or isinstance(kinds, list):
            if len(kinds == 1):
                self.request_params['fieldSelector'] = 'involvedObject.kind=' + kinds[0]
            else:
                # Client-side filtering
                self.kind_filter = set(kinds)


    def get_events(self):
        """
        Fetch latest events from the apiserver for the namespaces and kinds set on init
        and returns as list of events
        """
        filtered_events = []
        lastest_resversion = None

        events = self.kubeutil.retrieve_json_auth(self.request_url, params=self.request_params)

        for event in events.get('items', []):
            resversion = int(event.get('metadata', {}).get('resourceVersion', None))
            if resversion > self._service_cache_last_event_resversion:
                lastest_resversion = max(lastest_resversion, resversion)

                if self.namespace_filter is not None:
                    ns = event.get('involvedObject', {}).get('namespace', 'default')
                    if ns not in self.namespace_filter:
                        continue

                if self.kind_filter is not None:
                    kind = event.get('involvedObject', {}).get('kind', None)
                    if kind is None or kind not in self.kind_filter:
                        continue

                filtered_events.append(event)

        self.last_resversion = max(self.last_resversion, lastest_resversion)

        return filtered_events
