# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging
import requests
import socket

# project
from utils.dockerutil import DockerUtil
from utils.platform import Platform
from utils.singleton import Singleton


log = logging.getLogger(__name__)

ECS_INTROSPECT_DEFAULT_PORT = 51678
ECS_AGENT_CONTAINER_NAME = 'ecs-agent'

class ECSUtil:
    __metaclass__ = Singleton

    def __init__(self):
        self.docker_util = DockerUtil()
        self.ecs_agent_local = None

        self.ecs_tags = {}
        self._populate_ecs_tags()

    def _get_ecs_address(self):
        """Detect how to connect to the ecs-agent"""
        ecs_config = self.docker_util.inspect_container('ecs-agent')
        ip = ecs_config.get('NetworkSettings', {}).get('IPAddress')
        ports = ecs_config.get('NetworkSettings', {}).get('Ports')
        port = ports.keys()[0].split('/')[0] if ports else None
        if not ip:
            port = ECS_INTROSPECT_DEFAULT_PORT
            if self._is_ecs_agent_local():
                ip = "localhost"
            elif Platform.is_containerized():
                ip = self.docker_util.get_gateway()
            else:
                raise Exception("Unable to determine ecs-agent IP address")

        return ip, port

    def _populate_ecs_tags(self, skip_known=False):
        """
        Populate the cache of ecs tags. Can be called with skip_known=True
        If we just want to update new containers quickly (single task api call)
        (because we detected that a new task started for example)
        """
        try:
            ip, port = self._get_ecs_address()
        except Exception as ex:
            log.warning("Failed to connect to ecs-agent, skipping task tagging: %s" % ex)
            return

        try:
            tasks = requests.get('http://%s:%s/v1/tasks' % (ip, port)).json()
            for task in tasks.get('Tasks', []):
                for container in task.get('Containers', []):
                    cid = container['DockerId']

                    if skip_known and cid in self.ecs_tags:
                        continue

                    tags = ['task_name:%s' % task['Family'], 'task_version:%s' % task['Version']]
                    self.ecs_tags[container['DockerId']] = tags
        except requests.exceptions.HTTPError as ex:
            log.warning("Unable to collect ECS task names: %s" % ex)

    def _get_container_tags(self, cid):
        """
        This method triggers a fast fill of the tag cache (useful when a new task starts
        and we want the new containers to be cached with a single api call) and returns
        the tags (or an empty list) from the fresh cache.
        """
        self._populate_ecs_tags(skip_known=True)

        if cid in self.ecs_tags:
            return self.ecs_tags[cid]
        else:
            log.debug("Container %s doesn't seem to be an ECS task, skipping." % cid[:12])
            self.ecs_tags[cid] = []
        return []

    def _is_ecs_agent_local(self):
        """Return True if we can reach the ecs-agent over localhost, False otherwise.
        This is needed because if the ecs-agent is started with --net=host it won't have an IP address attached.
        """
        if self.ecs_agent_local is not None:
            return self.ecs_agent_local

        self.ecs_agent_local = False
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            result = sock.connect_ex(('localhost', ECS_INTROSPECT_DEFAULT_PORT))
        except Exception as e:
            log.debug("Unable to connect to ecs-agent. Exception: {0}".format(e))
        else:
            if result == 0:
                self.ecs_agent_local = True
            else:
                log.debug("ecs-agent is not available locally, encountered error code: {0}".format(result))
        sock.close()
        return self.ecs_agent_local

    def extract_container_tags(self, co):
        """
        Queries the ecs-agent to get ECS tags (task and task version) for a containers.
        As this is expensive, it is cached in the self.ecs_tags dict.
        The cache invalidation goes through invalidate_ecs_cache, called by the docker_daemon check

        :param co: container dict returned by docker-py
        :return: tags as list<string>, cached
        """
        co_id = co.get('Id', None)

        if co_id is None:
            log.warning("Invalid container object in extract_container_tags")
            return []

        if co_id in self.ecs_tags:
            return self.ecs_tags[co_id]
        else:
            return self._get_container_tags(co_id)

    def invalidate_cache(self, events):
        """
        Allows cache invalidation when containers die
        :param events from self.get_events
        """
        try:
            for ev in events:
                if ev.get('status') == 'die' and ev.get('id') in self.ecs_tags:
                    del self.ecs_tags[ev.get('id')]
        except Exception as e:
            log.warning("Error when invalidating ecs cache: " + str(e))
