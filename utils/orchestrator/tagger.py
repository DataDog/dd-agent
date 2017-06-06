# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


from .mesosutil import MesosUtil
from utils.singleton import Singleton


class Tagger():
    """
    Wraps several BaseUtil classes with autodetection and allows to query
    them through the same interface as BaseUtil classes

    See BaseUtil for apidoc
    """
    __metaclass__ = Singleton

    def __init__(self):
        self._utils = []  # [BaseUtil object]
        self._has_detected = False
        self.reset()

    def get_container_tags(self, cid=None, co=None):
        concat_tags = []
        for util in self._utils:
            tags = util.get_container_tags(cid, co)
            if tags:
                concat_tags.extend(tags)

        return concat_tags

    def invalidate_cache(self, events):
        for util in self._utils:
            util.invalidate_cache(events)

    def reset_cache(self):
        for util in self._utils:
            util.reset_cache()

    def reset(self):
        """
        Trigger a new autodetection and reset underlying util classes
        """
        self._utils = []

        if MesosUtil.is_detected():
            m = MesosUtil()
            m.reset_cache()
            self._utils.append(m)

        self._has_detected = bool(self._utils)

    def has_detected(self):
        """
        Returns whether the tagger has detected orchestrators it handles
        If false, calling get_container_tags will return an empty list
        """
        return self._has_detected
