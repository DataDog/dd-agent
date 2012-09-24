from checks import Check

# Device WMI drive types
class DriveType(object):
    UNKNOWN, NOROOT, REMOVEABLE, LOCAL, NETWORK, CD, RAM = (0, 1, 2, 3, 4, 5, 6)
IGNORED = ('_total',)
B2MB  = 1048576
KB2MB = B2KB = 1024

class Processes(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.gauge('system.proc.queue_length')
        self.gauge('system.proc.count')

    def check(self, agentConfig):
        import wmi
        w = wmi.WMI()
        os = w.Win32_PerfFormattedData_PerfOS_System()[0]
        self.save_sample('system.proc.queue_length', int(os.ProcessorQueueLength))
        self.save_sample('system.proc.count', int(os.Processes))

        return self.get_metrics()

class Memory(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('system.mem.free')
        self.gauge('system.mem.used')
        self.gauge('system.mem.total')
        self.gauge('system.mem.cached')
        self.gauge('system.mem.committed')
        self.gauge('system.mem.paged')
        self.gauge('system.mem.nonpaged')

    def check(self, agentConfig):
        import wmi
        w = wmi.WMI()
        os = w.Win32_OperatingSystem()[0]
        mem = w.Win32_PerfFormattedData_PerfOS_Memory()[0]
        total = int(os.TotalVisibleMemorySize) / KB2MB
        free = int(os.FreePhysicalMemory) / KB2MB
        self.save_sample('system.mem.total', total)
        self.save_sample('system.mem.free', free)
        self.save_sample('system.mem.used', total - free)
        self.save_sample('system.mem.cached', int(mem.CacheBytes) / B2MB)
        self.save_sample('system.mem.committed', int(mem.CommittedBytes) / B2MB)
        self.save_sample('system.mem.paged', int(mem.PoolPagedBytes) / B2MB)
        self.save_sample('system.mem.nonpaged', int(mem.PoolNonpagedBytes) / B2MB)

        return self.get_metrics()

class Cpu(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('system.cpu.user')
        self.gauge('system.cpu.idle')
        self.gauge('system.cpu.interrupt')
        self.gauge('system.cpu.system')

    def check(self, agentConfig):
        import wmi
        w = wmi.WMI()
        cpu = w.Win32_PerfFormattedData_PerfOS_Processor(name="_Total")[0]

        self.save_sample('system.cpu.user', cpu.PercentUserTime)
        self.save_sample('system.cpu.idle', cpu.PercentIdleTime)
        self.save_sample('system.cpu.interrupt', cpu.PercentInterruptTime)
        self.save_sample('system.cpu.system', cpu.PercentPrivilegedTime)

        return self.get_metrics()

class Network(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('system.net.bytes_rcvd')
        self.gauge('system.net.bytes_sent')

    def check(self, agentConfig):
        import wmi
        w = wmi.WMI()
        net = w.Win32_PerfFormattedData_Tcpip_NetworkInterface()

        for iface in net:
            name = self.normalize_device_name(iface.name)
            self.save_sample('system.net.bytes_rcvd', iface.BytesReceivedPerSec,
                device_name=name)
            self.save_sample('system.net.bytes_sent', iface.BytesSentPerSec,
                device_name=name)
        return self.get_metrics()

class Disk(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('system.disk.free')
        self.gauge('system.disk.total')
        self.gauge('system.disk.in_use')
        self.gauge('system.disk.used')

    def check(self, agentConfig):
        import wmi
        w = wmi.WMI()
        disk = w.Win32_LogicalDisk()

        for device in disk:
            name = self.normalize_device_name(device.name)
            if device.DriveType in (DriveType.CD, DriveType.UNKNOWN) or name in IGNORED:
                continue
            free = int(device.FreeSpace) / KB2MB
            total = int(device.Size) / KB2MB
            self.save_sample('system.disk.free', free, device_name=name)
            self.save_sample('system.disk.total', total, device_name=name)
            self.save_sample('system.disk.used', total - free, device_name=name)
            self.save_sample('system.disk.in_use', (free / total) * 100,
                device_name=name)
        return self.get_metrics()

class IO(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('system.io.wkb_s')
        self.gauge('system.io.w_s')
        self.gauge('system.io.rkb_s')
        self.gauge('system.io.r_s')
        self.gauge('system.io.avg_q_sz')

    def check(self, agentConfig):
        import wmi
        w = wmi.WMI()
        disk = w.Win32_PerfFormattedData_PerfDisk_LogicalDisk()

        for device in disk:
            name = self.normalize_device_name(device.name)
            if name in IGNORED:
                continue
            self.save_sample('system.io.wkb_s', int(device.DiskWriteBytesPerSec) / B2KB,
                device_name=name)
            self.save_sample('system.io.w_s', int(device.DiskWritesPerSec),
                device_name=name)
            self.save_sample('system.io.rkb_s', int(device.DiskReadBytesPerSec) / B2KB,
                device_name=name)
            self.save_sample('system.io.r_s', int(device.DiskReadsPerSec),
                device_name=name)
            self.save_sample('system.io.avg_q_sz', device.CurrentDiskQueueLength,
                device_name=name)
        return self.get_metrics()
