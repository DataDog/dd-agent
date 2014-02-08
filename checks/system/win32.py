from checks import Check

try:
    import wmi
    w = wmi.WMI()
except Exception:
    wmi, w = None, None

# Device WMI drive types
class DriveType(object):
    UNKNOWN, NOROOT, REMOVEABLE, LOCAL, NETWORK, CD, RAM = (0, 1, 2, 3, 4, 5, 6)
IGNORED = ('_total',)
B2MB  = float(1048576)
KB2MB = B2KB = float(1024)

class Processes(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.gauge('system.proc.queue_length')
        self.gauge('system.proc.count')

    def check(self, agentConfig):
        try:
            os = w.Win32_PerfFormattedData_PerfOS_System()[0]
        except AttributeError:
            self.logger.info('Missing Win32_PerfFormattedData_PerfOS_System WMI class.' \
                             ' No process metrics will be returned.')
            return

        try:
            cpu = w.Win32_PerfFormattedData_PerfOS_Processor(name="_Total")[0]
        except AttributeError:
            self.logger.info('Missing Win32_PerfFormattedData_PerfOS_Processor WMI class.' \
                             ' No process metrics will be returned.')
            return
        if os.ProcessorQueueLength is not None:
            self.save_sample('system.proc.queue_length', os.ProcessorQueueLength)
        if os.Processes is not None:
            self.save_sample('system.proc.count', os.Processes)

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
        try:
            os = w.Win32_OperatingSystem()[0]
        except AttributeError:
            self.logger.info('Missing Win32_OperatingSystem. No memory metrics will be returned.')
            return

        if os.TotalVisibleMemorySize is not None and os.FreePhysicalMemory is not None:
            total = int(os.TotalVisibleMemorySize) / KB2MB
            free = int(os.FreePhysicalMemory) / KB2MB
            self.save_sample('system.mem.total', total)
            self.save_sample('system.mem.free', free)
            self.save_sample('system.mem.used', total - free)

        mem = w.Win32_PerfFormattedData_PerfOS_Memory()[0]
        if mem.CacheBytes is not None:
            self.save_sample('system.mem.cached', int(mem.CacheBytes) / B2MB)
        if mem.CommittedBytes is not None:
            self.save_sample('system.mem.committed', int(mem.CommittedBytes) / B2MB)
        if mem.PoolPagedBytes is not None:
            self.save_sample('system.mem.paged', int(mem.PoolPagedBytes) / B2MB)
        if mem.PoolNonpagedBytes is not None:
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
        try:
            cpu = w.Win32_PerfFormattedData_PerfOS_Processor()
        except AttributeError:
            self.logger.info('Missing Win32_PerfFormattedData_PerfOS_Processor WMI class.' \
                             ' No CPU metrics will be returned.')
            return

        cpu_user = self._average_metric(cpu, 'PercentUserTime')
        if cpu_user:
            self.save_sample('system.cpu.user', cpu_user)

        cpu_idle = self._average_metric(cpu, 'PercentIdleTime')
        if cpu_idle:
            self.save_sample('system.cpu.idle', cpu_idle)

        cpu_interrupt = self._average_metric(cpu, 'PercentInterruptTime')
        if cpu_interrupt is not None:
            self.save_sample('system.cpu.interrupt', cpu_interrupt)

        cpu_privileged = self._average_metric(cpu, 'PercentPrivilegedTime')
        if cpu_privileged is not None:
            self.save_sample('system.cpu.system', cpu_privileged)

        return self.get_metrics()

    def _average_metric(self, wmi_class, wmi_prop):
        ''' Sum all of the values of a metric from a WMI class object, excluding
            the value for "_Total"
        '''
        val = 0
        counter = 0
        for wmi_object in wmi_class:
            if wmi_object.Name == '_Total':
                # Skip the _Total value
                continue

            if getattr(wmi_object, wmi_prop) is not None:
                counter += 1
                val += float(getattr(wmi_object, wmi_prop))

        if counter > 0:
            return val / counter

        return val


class Network(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('system.net.bytes_rcvd')
        self.gauge('system.net.bytes_sent')

    def check(self, agentConfig):
        try:
            net = w.Win32_PerfFormattedData_Tcpip_NetworkInterface()
        except AttributeError:
            self.logger.info('Missing Win32_PerfFormattedData_Tcpip_NetworkInterface WMI class.' \
                             ' No network metrics will be returned')
            return

        for iface in net:
            name = self.normalize_device_name(iface.name)
            if iface.BytesReceivedPerSec is not None:
                self.save_sample('system.net.bytes_rcvd', iface.BytesReceivedPerSec,
                    device_name=name)
            if iface.BytesSentPerSec is not None:
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
        try:
            disk = w.Win32_LogicalDisk()
        except AttributeError:
            self.logger.info('Missing Win32_LogicalDisk WMI class.'  \
                             ' No disk metrics will be returned.')
            return

        for device in disk:
            name = self.normalize_device_name(device.name)
            if device.DriveType in (DriveType.CD, DriveType.UNKNOWN) or name in IGNORED:
                continue
            if device.FreeSpace is not None and device.Size is not None:
                free = float(device.FreeSpace) / B2KB
                total = float(device.Size) / B2KB
                used = total - free
                self.save_sample('system.disk.free', free, device_name=name)
                self.save_sample('system.disk.total', total, device_name=name)
                self.save_sample('system.disk.used', used, device_name=name)
                self.save_sample('system.disk.in_use', (used / total),
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
        try:
            disk = w.Win32_PerfFormattedData_PerfDisk_LogicalDisk()
        except AttributeError:
            self.logger.info('Missing Win32_PerfFormattedData_PerfDisk_LogicalDiskUnable WMI class.' \
                             ' No I/O metrics will be returned.')
            return

        for device in disk:
            name = self.normalize_device_name(device.name)
            if name in IGNORED:
                continue
            if device.DiskWriteBytesPerSec is not None:
                self.save_sample('system.io.wkb_s', int(device.DiskWriteBytesPerSec) / B2KB,
                    device_name=name)
            if device.DiskWritesPerSec is not None:
                self.save_sample('system.io.w_s', int(device.DiskWritesPerSec),
                    device_name=name)
            if device.DiskReadBytesPerSec is not None:
                self.save_sample('system.io.rkb_s', int(device.DiskReadBytesPerSec) / B2KB,
                    device_name=name)
            if device.DiskReadsPerSec is not None:
                self.save_sample('system.io.r_s', int(device.DiskReadsPerSec),
                    device_name=name)
            if device.CurrentDiskQueueLength is not None:
                self.save_sample('system.io.avg_q_sz', device.CurrentDiskQueueLength,
                    device_name=name)
        return self.get_metrics()
