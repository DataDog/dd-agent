# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging
from utils.dockerutil import DockerUtil
from utils.singleton import Singleton


log = logging.getLogger(__name__)

NOMAD_TASK_NAME = 'NOMAD_TASK_NAME'
NOMAD_JOB_NAME = 'NOMAD_JOB_NAME'
NOMAD_ALLOC_NAME = 'NOMAD_ALLOC_NAME'


class NomadUtil:
    __metaclass__ = Singleton

    def __init__(self, instance=None):
        self.docker_util = DockerUtil()
        if instance is None:
            log.debug("New NomadUtil instance")
            self._container_tags_cache = {}
            self._enabled = None

    def init_platform(self, agentConfig):
        """
        Enable/disable Nomad support depending on the docker_orchestrator config file entry
        :param agentConfig: dict from config.get_config()
        """
        self._enabled = agentConfig.get('docker_orchestrator', None) == 'nomad'

    def is_enabled(self):
        """
        Allows user classes to check whether nomad is to be activated.
        init_platform has to be called once first
        :return: True/False
        """
        if self._enabled is None:
            log.warning("Calling nomad.is_nomad before init_platform, replying False")
            return False
        else:
            return self._enabled

    def extract_container_tags(self, co):
        """
        Queries docker inspect to get nomad tags in the container's environment vars.
        As this is expensive, it is cached in the self._nomad_tags_cache dict.
        The cache invalidation goes through invalidate_nomad_cache, called by docker_daemon

        :param co: container dict returned by docker-py
        :return: tags as list<string>, cached
        """

        co_id = co.get('Id', 'INVALID')

        if co_id == 'INVALID':
            log.warning("Invalid container object in extract_nomad_tags")
            return

        # Cache lookup on Id, verified on Created timestamp
        if co_id in self._container_tags_cache:
            created, tags = self._container_tags_cache[co_id]
            if created == co.get('Created', -1):
                log.debug("Gettings nomad tags from cache")
                return tags

        tags = []
        try:
            inspect_info = self.docker_util.inspect_container(co_id)
            envvars = inspect_info.get('Config', {}).get('Env', {})
            for var in envvars:
                if var.startswith(NOMAD_TASK_NAME):
                    tags.append('nomad_task:%s' % var[len(NOMAD_TASK_NAME)+1:])
                elif var.startswith(NOMAD_JOB_NAME):
                    tags.append('nomad_job:%s' % var[len(NOMAD_JOB_NAME)+1:])
                elif var.startswith(NOMAD_ALLOC_NAME):
                    try:
                        start = var.index('.', len(NOMAD_ALLOC_NAME)) + 1
                        end = var.index('[')
                        tags.append('nomad_group:%s' % var[start:end])
                        log.debug("Gettings nomad tags from docker")
                    except ValueError:
                        pass
                    self._container_tags_cache[co_id] = (co.get('Created'), tags)
                    log.debug(self._container_tags_cache)
        except Exception as e:
            log.warning("Error while parsing Nomad tags: %s" % str(e))
        finally:
            return tags

    def invalidate_cache(self, events):
        """
        Allows cache invalidation when containers dies
        :param events from self.get_events
        """
        try:
            for ev in events:
                if ev.get('status') == 'die' and ev.get('id') in self._container_tags_cache:
                    log.debug("Invalidating nomad cache for %s" % ev.get('id'))
                    del self._container_tags_cache[ev.get('id')]
                    log.debug(self._container_tags_cache)
        except Exception as e:
            log.warning("Error when invalidating nomad cache: " + str(e))
