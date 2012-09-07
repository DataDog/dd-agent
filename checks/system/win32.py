from checks import Check

class Disk(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

class Load(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.gague('system.perf.proc_queue_length')

class Memory(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('system.mem.free')
        self.gauge('system.mem.cached')
        self.gauge('system.mem.committed')
        self.gauge('system.mem.paged')
        self.gauge('system.mem.nonpaged')

    def check(self, agentConfig):
        import wmi
        w = wmi.WMI()
        mem = w.Win32_PerfFormattedData_PerfOS_Memory()[0]
        self.save_sample('system.mem.free', int(mem.AvailableMBytes))
        #self.save_sample('system.mem.cached', int(mem.CacheMBytes))
        #self.save_sample('system.mem.committed', int(mem.CommittedMBytes))
        #self.save_sample('system.mem.paged', int(mem.PoolPagedMBytes))
        #self.save_sample('system.mem.nonpaged', int(mem.PoolNonpagedMBytes))

        return self.get_metrics()

class Cpu(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('system.cpu.user')
        self.gauge('system.cpu.idle')
        self.gauge('system.cpu.interrupt')
        self.gauge('system.cpu.privileged')

    def check(self, agentConfig):
        import wmi
        w = wmi.WMI()
        cpu = w.Win32_PerfFormattedData_PerfOS_Processor(name="_Total")[0]

        self.save_sample('system.cpu.user', cpu.PercentUserTime)
        self.save_sample('system.cpu.idle', cpu.PercentIdleTime)
        self.save_sample('system.cpu.interrupt', cpu.PercentInterruptTime)
        self.save_sample('system.cpu.privileged', cpu.PercentPrivilegedTime)

        return self.get_metrics()