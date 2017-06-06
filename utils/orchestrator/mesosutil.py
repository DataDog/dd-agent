# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

from .baseutil import BaseUtil

CHRONOS_JOB_NAME = "CHRONOS_JOB_NAME"
MARATHON_APP_ID = "MARATHON_APP_ID"
MESOS_TASK_ID = "MESOS_TASK_ID"


class MesosUtil(BaseUtil):
    def __init__(self):
        BaseUtil.__init__(self)
        self.needs_inspect = True
        self.needs_env = True

    def _get_cacheable_tags(self, cid, co=None):
        tags = []

        self.log.warning("called")

        envvars = co.get('Config', {}).get('Env', {})
        self.log.warning(envvars)

        for var in envvars:
            if var.startswith(CHRONOS_JOB_NAME):
                tags.append('chronos_job:%s' % var[len(CHRONOS_JOB_NAME) + 1:])
            elif var.startswith(MARATHON_APP_ID):
                tags.append('marathon_app:%s' % var[len(MARATHON_APP_ID) + 1:])
            elif var.startswith(MESOS_TASK_ID):
                tags.append('mesos_task:%s' % var[len(MESOS_TASK_ID) + 1:])

        return tags

    @staticmethod
    def is_detected():
        return MESOS_TASK_ID in os.environ
