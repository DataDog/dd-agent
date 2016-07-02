# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# 3p
import psutil

# project
from checks import AgentCheck
from utils.platform import Platform


class SystemCore(AgentCheck):

    def check(self, instance):

        if Platform.is_linux():
            procfs_path = self.agentConfig.get('procfs_path', '/proc').rstrip('/')
            psutil.PROCFS_PATH = procfs_path

        cpu_times = psutil.cpu_times(percpu=True)
        self.gauge("system.core.count", len(cpu_times))

        for i, cpu in enumerate(cpu_times):
            for key, value in cpu._asdict().iteritems():
                self.rate(
                    "system.core.{0}".format(key),
                    100.0 * value,
                    tags=["core:{0}".format(i)]
                )
