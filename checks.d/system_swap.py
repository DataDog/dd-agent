# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# 3p
import psutil

# project
from checks import AgentCheck
from utils.platform import Platform


class SystemSwap(AgentCheck):

    def check(self, instance):

        if Platform.is_linux():
            procfs_path = self.agentConfig.get('procfs_path', '/proc').rstrip('/')
            psutil.PROCFS_PATH = procfs_path

        swap_mem = psutil.swap_memory()
        self.rate('system.swap.swapped_in', swap_mem.sin)
        self.rate('system.swap.swapped_out', swap_mem.sout)
