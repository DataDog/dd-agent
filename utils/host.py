from collections import namedtuple
from datadog import initialize
from datadog import api


class HostTagger(object):
    """
    Uses the DataDog API Client to update the tags for a host discovered by the agent.

    Useful in environments where the agent must keep track of guest machines, e.g.
    virtualized instances runnning on the agent host, but mandating their own "host:" tag

    Such hosts can't be tagged via the standard mechanisms, since the agent normalizes
    payloads to a single "hostname" before reporting to the backend.
    """
    MAX_QUEUE_LEN = 10
    TagRequest = namedtuple("TagRequest", "hostname tags")

    def __init__(self, api_key, logger):
        initialize(api_key=api_key)
        self.dd_api = api

        # Keep a local copy of assigned host tags
        # so that we don't send api requests when we don't have to
        self._known_hosts = {}
        self._request_queue = []


        # Alias for AgentCheck logger
        self.log = logger

    def _are_tags_equivalent(self, host, tags):
        if not host in self._known_hosts:
            return False

        return set(self._known_hosts[host]) == set(tags)

    def _queue_tag_update(self, host, tags):
        self._request_queue.append(
            self.TagRequest(host, tags)
        )

        if len(self._request_queue) >= self.MAX_QUEUE_LEN:
            self.flush()

    def create_host_tags(self, host, tags, blocking=False):
        if not self._are_tags_equivalent(host, tags):
            # Potentially overkill, but dedupe the tags first)
            tags = list(set(tags))

            if blocking:
                # Send the request immediately, rather than queueing it for later
                try:
                    self.dd_api.Tag.create(host, tags=tags)
                except:
                    self.log.warning("Failed to update tags for server %s", req.hostname)
            else:
                self._queue_tag_update(host, tags)

            # Register this host so we know we've seen it
            self._known_hosts[host] = tags

    def flush(self):
        while self._request_queue:
            req = self._request_queue.pop()

            try:
                self.dd_api.Tag.create(req.hostname, tags=req.tags)
            except Exception as e:
                self.log.warning("Failed to update tags for server %s", req.hostname)


