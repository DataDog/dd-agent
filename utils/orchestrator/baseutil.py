# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging

# project
from utils.dockerutil import DockerUtil
from utils.singleton import Singleton


class BaseUtil:
    """
    Base class for orchestrator utils. Only handles container tags for now.
    Users should go through the orchestrator.Tagger class to simplify the code

    Children classes can implement:
      - __init__: to change self.needs_inspect
      - _get_cacheable_tags: tags will be cached for reuse
      - _get_transient_tags: tags can change and won't be cached (TODO)
      - invalidate_cache: custom cache invalidation logic
      - is_detected (staticmethod)
    """
    __metaclass__ = Singleton

    def __init__(self):
        # Whether your get___tags methods need the inspect result
        self.needs_inspect = False
        # Whether your methods need the env portion (not in partial inspect)
        self.needs_env = False

        self.log = logging.getLogger(__name__)
        self.docker_util = DockerUtil()

        # Tags cache as a dict {co_id: [tags]}
        self._container_tags_cache = {}

    def get_container_tags(self, cid=None, co=None):
        """
        Returns container tags for the given container, inspecting the container if needed
        :param container: either the container id or container dict returned by docker-py
        :return: tags as list<string>, cached
        """

        if (cid is not None) and (co is not None):
            self.log.error("Can only pass either a container id or object, not both, returning empty tags")
            return []
        if (cid is None) and (co is None):
            self.log.error("Need one container id or container object, returning empty tags")
            return []
        elif co is not None:
            if 'Id' in co:
                cid = co.get('Id')
            else:
                self.log.warning("Invalid container dict, returning empty tags")
                return []

        if cid in self._container_tags_cache:
            return self._container_tags_cache[cid]
        else:
            if (self.needs_inspect or self.needs_env) and co is None:
                co = self.docker_util.inspect_container(cid)
            if self.needs_env and 'Env' not in co.get('Config', {}):
                co = self.docker_util.inspect_container(cid)
            self._container_tags_cache[cid] = self._get_cacheable_tags(cid, co)
            return self._container_tags_cache[cid]

    def invalidate_cache(self, events):
        """
        Allows cache invalidation when containers die
        :param events from self.get_events
        """
        try:
            for ev in events:
                if ev.get('status') == 'die' and ev.get('id') in self._container_tags_cache:
                    del self._container_tags_cache[ev.get('id')]
        except Exception as e:
            self.log.warning("Error when invalidating tag cache: " + str(e))

    def reset_cache(self):
        """
        Empties all caches to reset the singleton to initial state
        """
        self._container_tags_cache = {}
