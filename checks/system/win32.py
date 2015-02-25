# project
from checks import Check

# 3rd party
try:
    import psutil
except ImportError:
    psutil = None

try:
    import wmi
    w = wmi.WMI()
except Exception:
    wmi, w = None, None

# Device WMI drive types
class DriveType(object):
    UNKNOWN, NOROOT, REMOVEABLE, LOCAL, NETWORK, CD, RAM = (0, 1, 2, 3, 4, 5, 6)
B2MB  = float(1048576)
KB2MB = B2KB = float(1024)

def should_ignore_disk(name, blacklist_re):
    # blacklist_re is a compiled regex, compilation done at config loading time
    return name =='_total' or blacklist_re is not None and blacklist_re.match(name)

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
        # area of physical memory that stores recently used pages of data
        # for applications
        self.gauge('system.mem.cached')
        # Committed memory is physical memory for which space has been
        # reserved on the disk paging file in case it must be written
        # back to disk
        self.gauge('system.mem.committed')
        # physical memory used by the operating system, for objects
        # that can be written to disk when they are not being used
        self.gauge('system.mem.paged')
        # physical memory used by the operating system for objects that
        # cannot be written to disk, but must remain in physical memory
        # as long as they are allocated.
        self.gauge('system.mem.nonpaged')
        # usable = free + cached
        self.gauge('system.mem.usable')
        self.gauge('system.mem.pct_usable')

    def check(self, agentConfig):
        try:
            os = w.Win32_OperatingSystem()[0]
        except AttributeError:
            self.logger.info('Missing Win32_OperatingSystem. No memory metrics will be returned.')
            return

        total = 0
        free = 0
        cached = 0

        if os.TotalVisibleMemorySize is not None and os.FreePhysicalMemory is not None:
            total = int(os.TotalVisibleMemorySize) / KB2MB
            free = int(os.FreePhysicalMemory) / KB2MB
            self.save_sample('system.mem.total', total)
            self.save_sample('system.mem.free', free)
            self.save_sample('system.mem.used', total - free)


        mem = w.Win32_PerfFormattedData_PerfOS_Memory()[0]
        if mem.CacheBytes is not None:
            cached = int(mem.CacheBytes) / B2MB
            self.save_sample('system.mem.cached', cached)
        if mem.CommittedBytes is not None:
            self.save_sample('system.mem.committed', int(mem.CommittedBytes) / B2MB)
        if mem.PoolPagedBytes is not None:
            self.save_sample('system.mem.paged', int(mem.PoolPagedBytes) / B2MB)
        if mem.PoolNonpagedBytes is not None:
            self.save_sample('system.mem.nonpaged', int(mem.PoolNonpagedBytes) / B2MB)

        usable = free + cached
        self.save_sample('system.mem.usable', usable)
        if total > 0:
            pct_usable = float(usable) / total
            self.save_sample('system.mem.pct_usable', pct_usable)

        return self.get_metrics()

class Cpu(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.counter('system.cpu.user')
        self.counter('system.cpu.idle')
        self.gauge('system.cpu.interrupt')
        self.counter('system.cpu.system')

    def check(self, agentConfig):
        try:
            cpu = w.Win32_PerfFormattedData_PerfOS_Processor()
        except AttributeError:
            self.logger.info('Missing Win32_PerfFormattedData_PerfOS_Processor WMI class.' \
                             ' No CPU metrics will be returned.')
            return

        cpu_interrupt = self._average_metric(cpu, 'PercentInterruptTime')
        if cpu_interrupt is not None:
            self.save_sample('system.cpu.interrupt', cpu_interrupt)

        cpu_percent = psutil.cpu_times()

        self.save_sample('system.cpu.user', 100 * cpu_percent.user / psutil.NUM_CPUS)
        self.save_sample('system.cpu.idle', 100 * cpu_percent.idle / psutil.NUM_CPUS)
        self.save_sample('system.cpu.system', 100 * cpu_percent.system/ psutil.NUM_CPUS)

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
        self.counter("system.disk.read_time_pct")
        self.counter("system.disk.write_time_pct")

    def check_disk_usage(self, agentConfig):
        try:
            disk = w.Win32_LogicalDisk()
        except AttributeError:
            self.logger.info('Missing Win32_LogicalDisk WMI class.'  \
                             ' No disk metrics will be returned.')
            return

        blacklist_re = agentConfig.get('device_blacklist_re', None)
        for device in disk:
            name = self.normalize_device_name(device.name)
            if device.DriveType in (DriveType.CD, DriveType.UNKNOWN) or should_ignore_disk(name, blacklist_re):
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

    def check_disk_latency(self, agentConfig):
        try:
            disk_io_counters = psutil.disk_io_counters(True)
            for disk_name, disk in disk_io_counters.iteritems():
                read_time_pct = disk.read_time * 100.0 / 1000.0 # x100 to have it as a percentage, /1000 as psutil returns the value in ms
                write_time_pct = disk.write_time * 100.0 / 1000.0 # x100 to have it as a percentage, /1000 as psutil returns the value in ms
                self.save_sample("system.disk.read_time_pct", read_time_pct, device_name=disk_name)
                self.save_sample("system.disk.write_time_pct", write_time_pct, device_name=disk_name)
        except RuntimeError:
            self.logger.warning("Unable to fetch disk latency metrics")


    def check(self, agentConfig):
        self.check_disk_usage(agentConfig)
        self.check_disk_latency(agentConfig)
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
        blacklist_re = agentConfig.get('device_blacklist_re', None)
        for device in disk:
            name = self.normalize_device_name(device.name)
            if should_ignore_disk(name, blacklist_re):
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
