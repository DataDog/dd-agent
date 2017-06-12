# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import requests

from .baseutil import BaseUtil

CHRONOS_JOB_NAME = "CHRONOS_JOB_NAME"
MARATHON_APP_ID = "MARATHON_APP_ID"
MESOS_TASK_ID = "MESOS_TASK_ID"

MESOS_AGENT_IP_ENV = ["LIBPROCESS_IP", "HOST", "HOSTNAME"]
MESOS_AGENT_HTTP_PORT = 5051
DCOS_AGENT_HTTP_PORT = 61001
DOCS_AGENT_HTTPS_PORT = 61002


def MESOS_AGENT_VALIDATION(r):
    return "version" in r.json()


def DCOS_AGENT_VALIDATION(r):
    return "dcos_version" in r.json()


class MesosUtil(BaseUtil):
    def __init__(self):
        BaseUtil.__init__(self)
        self.needs_inspect_config = True
        self.mesos_agent_url, self.dcos_agent_url = self._detect_agents()

    def _get_cacheable_tags(self, cid, co=None):
        tags = []
        envvars = co.get('Config', {}).get('Env', {})

        for var in envvars:
            if var.startswith(CHRONOS_JOB_NAME):
                tags.append('chronos_job:%s' % var[len(CHRONOS_JOB_NAME) + 1:])
            elif var.startswith(MARATHON_APP_ID):
                tags.append('marathon_app:%s' % var[len(MARATHON_APP_ID) + 1:])
            elif var.startswith(MESOS_TASK_ID):
                tags.append('mesos_task:%s' % var[len(MESOS_TASK_ID) + 1:])

        return tags

    def _detect_agents(self):
        """
        The Mesos agent runs on every node and listens to http port 5051
        See https://mesos.apache.org/documentation/latest/endpoints/
        We'll use the unauthenticated endpoint /version

        The DCOS agent runs on every node and listens to ports 61001 or 61002
        See https://dcos.io/docs/1.9/api/agent-routes/
        We'll use the unauthenticated endpoint /system/health/v1
        """
        mesos_urls = []
        dcos_urls = []
        for var in MESOS_AGENT_IP_ENV:
            if var in os.environ:
                mesos_urls.append("http://%s:%d/version" %
                                  (os.environ.get(var), MESOS_AGENT_HTTP_PORT))
                dcos_urls.append("http://%s:%d/system/health/v1" %
                                 (os.environ.get(var), DCOS_AGENT_HTTP_PORT))
                dcos_urls.append("https://%s:%d/system/health/v1" %
                                 (os.environ.get(var), DOCS_AGENT_HTTPS_PORT))
        # Try network gateway last
        gw = self.docker_util.get_gateway()
        if gw:
            mesos_urls.append("http://%s:%d/version" % (gw, MESOS_AGENT_HTTP_PORT))
            dcos_urls.append("http://%s:%d/system/health/v1" % (gw, DCOS_AGENT_HTTP_PORT))
            dcos_urls.append("https://%s:%d/system/health/v1" % (gw, DOCS_AGENT_HTTPS_PORT))

        mesos_url = self._try_urls(mesos_urls, validation_lambda=MESOS_AGENT_VALIDATION)
        if mesos_url:
            self.log.debug("Found Mesos agent at " + mesos_url)
        else:
            self.log.debug("Count not find Mesos agent at urls " + str(mesos_urls))
        dcos_url = self._try_urls(dcos_urls, validation_lambda=DCOS_AGENT_VALIDATION)
        if dcos_url:
            self.log.debug("Found DCOS agent at " + dcos_url)
        else:
            self.log.debug("Count not find DCOS agent at urls " + str(dcos_urls))

        return (mesos_url, dcos_url)

    @staticmethod
    def is_detected():
        return MESOS_TASK_ID in os.environ

    def get_host_tags(self):
        tags = []
        if self.mesos_agent_url:
            try:
                resp = requests.get(self.mesos_agent_url, timeout=1).json()
                if "version" in resp:
                    tags.append('mesos_version:%s' % resp.get("version"))
            except Exception as e:
                self.log.debug("Error getting Mesos version: %s" % str(e))

        if self.dcos_agent_url:
            try:
                resp = requests.get(self.dcos_agent_url, timeout=1).json()
                if "dcos_version" in resp:
                    tags.append('dcos_version:%s' % resp.get("dcos_version"))
            except Exception as e:
                self.log.debug("Error getting DCOS version: %s" % str(e))

        return tags
