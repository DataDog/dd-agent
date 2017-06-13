# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

from .baseutil import BaseUtil

NOMAD_TASK_NAME = 'NOMAD_TASK_NAME'
NOMAD_JOB_NAME = 'NOMAD_JOB_NAME'
NOMAD_ALLOC_NAME = 'NOMAD_ALLOC_NAME'
NOMAD_ALLOC_ID = 'NOMAD_ALLOC_ID'

NOMAD_AGENT_URL = "http://%s:4646/v1/agent/self"


class NomadUtil(BaseUtil):
    def __init__(self):
        BaseUtil.__init__(self)
        self.needs_inspect_config = True

    def _get_cacheable_tags(self, cid, co=None):
        tags = []
        envvars = co.get('Config', {}).get('Env', {})
        for var in envvars:
            if var.startswith(NOMAD_TASK_NAME):
                tags.append('nomad_task:%s' % var[len(NOMAD_TASK_NAME) + 1:])
            elif var.startswith(NOMAD_JOB_NAME):
                tags.append('nomad_job:%s' % var[len(NOMAD_JOB_NAME) + 1:])
            elif var.startswith(NOMAD_ALLOC_NAME):
                try:
                    start = var.index('.', len(NOMAD_ALLOC_NAME)) + 1
                    end = var.index('[')
                    if end <= start:
                        raise ValueError("Error extracting group from %s, check format" % var)
                    tags.append('nomad_group:%s' % var[start:end])
                except ValueError:
                    pass
        return tags

    @staticmethod
    def is_detected():
        return NOMAD_ALLOC_ID in os.environ
