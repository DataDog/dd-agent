# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# project
from checks import Check

# 3rd party
import uptime
try:
    import psutil
except ImportError:
    psutil = None

try:
    from checks.libs.wmi.sampler import WMISampler
except Exception:
    def WMISampler(*args, **kwargs):
        """
        Fallback with a 'None' callable object.
        """
        return

# datadog
from utils.timeout import TimeoutException


# Device WMI drive types
class DriveType(object):
    UNKNOWN, NOROOT, REMOVEABLE, LOCAL, NETWORK, CD, RAM = (0, 1, 2, 3, 4, 5, 6)
B2MB = float(1048576)
KB2MB = B2KB = float(1024)


def should_ignore_disk(name, blacklist_re):
    # blacklist_re is a compiled regex, compilation done at config loading time
    return name == '_total' or blacklist_re is not None and blacklist_re.match(name)


class Processes(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        # Sampler(s)
        self.wmi_sampler = WMISampler(
            logger,
            "Win32_PerfRawData_PerfOS_System",
            ["ProcessorQueueLength", "Processes"]
        )

        self.gauge('system.proc.queue_length')
        self.gauge('system.proc.count')

    def check(self, agentConfig):
        try:
            self.wmi_sampler.sample()
        except TimeoutException:
            self.logger.warning(
                u"Timeout while querying Win32_PerfRawData_PerfOS_System WMI class."
                u" Processes metrics will be returned at next iteration."
            )
            return []

        if not (len(self.wmi_sampler)):
            self.logger.warning('Missing Win32_PerfRawData_PerfOS_System WMI class.'
                             ' No process metrics will be returned.')
            return []

        os = self.wmi_sampler[0]
        processor_queue_length = os.get('ProcessorQueueLength')
        processes = os.get('Processes')

        if processor_queue_length is not None:
            self.save_sample('system.proc.queue_length', processor_queue_length)
        if processes is not None:
            self.save_sample('system.proc.count', processes)

        return self.get_metrics()


class Memory(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        # Sampler(s)
        self.os_wmi_sampler = WMISampler(
            logger,
            "Win32_OperatingSystem",
            ["TotalVisibleMemorySize", "FreePhysicalMemory"]
        )
        self.mem_wmi_sampler = WMISampler(
            logger,
            "Win32_PerfRawData_PerfOS_Memory",
            ["CacheBytes", "CommittedBytes", "PoolPagedBytes", "PoolNonpagedBytes"])

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
        #  details about the usage of the pagefile.
        self.gauge('system.mem.page_total')
        self.gauge('system.mem.page_used')
        self.gauge('system.mem.page_free')
        self.gauge('system.mem.page_pct_free')

    def check(self, agentConfig):
        try:
            self.os_wmi_sampler.sample()
        except TimeoutException:
            self.logger.warning(
                u"Timeout while querying Win32_OperatingSystem WMI class."
                u" Memory metrics will be returned at next iteration."
            )
            return []

        if not (len(self.os_wmi_sampler)):
            self.logger.warning('Missing Win32_OperatingSystem WMI class.'
                             ' No memory metrics will be returned.')
            return []

        os = self.os_wmi_sampler[0]

        total = 0
        free = 0
        cached = 0

        total_visible_memory_size = os.get('TotalVisibleMemorySize')
        free_physical_memory = os.get('FreePhysicalMemory')

        if total_visible_memory_size is not None and free_physical_memory is not None:
            total = int(total_visible_memory_size) / KB2MB
            free = int(free_physical_memory) / KB2MB
            self.save_sample('system.mem.total', total)
            self.save_sample('system.mem.free', free)
            self.save_sample('system.mem.used', total - free)

        try:
            self.mem_wmi_sampler.sample()
        except TimeoutException:
            self.logger.warning(
                u"Timeout while querying Win32_PerfRawData_PerfOS_Memory WMI class."
                u" Memory metrics will be returned at next iteration."
            )
            return []

        if not (len(self.mem_wmi_sampler)):
            self.logger.info('Missing Win32_PerfRawData_PerfOS_Memory WMI class.'
                             ' No memory metrics will be returned.')
            return self.get_metrics()

        mem = self.mem_wmi_sampler[0]

        cache_bytes = mem.get('CacheBytes')
        committed_bytes = mem.get('CommittedBytes')
        pool_paged_bytes = mem.get('PoolPagedBytes')
        pool_non_paged_bytes = mem.get('PoolNonpagedBytes')

        if cache_bytes is not None:
            cached = int(cache_bytes) / B2MB
            self.save_sample('system.mem.cached', cached)
        if committed_bytes is not None:
            self.save_sample('system.mem.committed', int(committed_bytes) / B2MB)
        if pool_paged_bytes is not None:
            self.save_sample('system.mem.paged', int(pool_paged_bytes) / B2MB)
        if pool_non_paged_bytes is not None:
            self.save_sample('system.mem.nonpaged', int(pool_non_paged_bytes) / B2MB)

        usable = free + cached
        self.save_sample('system.mem.usable', usable)
        if total > 0:
            pct_usable = float(usable) / total
            self.save_sample('system.mem.pct_usable', pct_usable)

        page = psutil.virtual_memory()
        if page.total is not None:
            self.save_sample('system.mem.page_total', page.total / B2MB)
            self.save_sample('system.mem.page_used', page.used / B2MB)
            self.save_sample('system.mem.page_free', page.available / B2MB)
            self.save_sample('system.mem.page_pct_free', (100 - page.percent) / 100)

        return self.get_metrics()


class Cpu(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        # Sampler(s)
        self.wmi_sampler = WMISampler(
            logger,
            "Win32_PerfRawData_PerfOS_Processor",
            ["Name", "PercentInterruptTime"]
        )

        self.counter('system.cpu.user')
        self.counter('system.cpu.idle')
        self.gauge('system.cpu.interrupt')
        self.counter('system.cpu.system')

    def check(self, agentConfig):
        try:
            self.wmi_sampler.sample()
        except TimeoutException:
            self.logger.warning(
                u"Timeout while querying Win32_PerfRawData_PerfOS_Processor WMI class."
                u" CPU metrics will be returned at next iteration."
            )
            return []

        if not (len(self.wmi_sampler)):
            self.logger.warning('Missing Win32_PerfRawData_PerfOS_Processor WMI class.'
                             ' No CPU metrics will be returned')
            return []

        cpu_interrupt = self._average_metric(self.wmi_sampler, 'PercentInterruptTime')
        if cpu_interrupt is not None:
            self.save_sample('system.cpu.interrupt', cpu_interrupt)

        cpu_percent = psutil.cpu_times()

        self.save_sample('system.cpu.user', 100 * cpu_percent.user / psutil.cpu_count())
        self.save_sample('system.cpu.idle', 100 * cpu_percent.idle / psutil.cpu_count())
        self.save_sample('system.cpu.system', 100 * cpu_percent.system / psutil.cpu_count())

        return self.get_metrics()

    def _average_metric(self, sampler, wmi_prop):
        ''' Sum all of the values of a metric from a WMI class object, excluding
            the value for "_Total"
        '''
        val = 0
        counter = 0
        for wmi_object in sampler:
            if wmi_object['Name'] == '_Total':
                # Skip the _Total value
                continue

            wmi_prop_value = wmi_object.get(wmi_prop)
            if wmi_prop_value is not None:
                counter += 1
                val += float(wmi_prop_value)

        if counter > 0:
            return val / counter

        return val


class Network(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        # Sampler(s)
        self.wmi_sampler = WMISampler(
            logger,
            "Win32_PerfRawData_Tcpip_NetworkInterface",
            ["Name", "BytesReceivedPerSec", "BytesSentPerSec"]
        )

        self.gauge('system.net.bytes_rcvd')
        self.gauge('system.net.bytes_sent')

    def check(self, agentConfig):
        try:
            self.wmi_sampler.sample()
        except TimeoutException:
            self.logger.warning(
                u"Timeout while querying Win32_PerfRawData_Tcpip_NetworkInterface WMI class."
                u" Network metrics will be returned at next iteration."
            )
            return []

        if not (len(self.wmi_sampler)):
            self.logger.warning('Missing Win32_PerfRawData_Tcpip_NetworkInterface WMI class.'
                             ' No network metrics will be returned')
            return []

        for iface in self.wmi_sampler:
            name = iface.get('Name')
            bytes_received_per_sec = iface.get('BytesReceivedPerSec')
            bytes_sent_per_sec = iface.get('BytesSentPerSec')

            name = self.normalize_device_name(name)
            if bytes_received_per_sec is not None:
                self.save_sample('system.net.bytes_rcvd', bytes_received_per_sec,
                                 device_name=name)
            if bytes_sent_per_sec is not None:
                self.save_sample('system.net.bytes_sent', bytes_sent_per_sec,
                                 device_name=name)
        return self.get_metrics()


class IO(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        #  Sampler(s)
        self.wmi_sampler = WMISampler(
            logger,
            "Win32_PerfRawData_PerfDisk_LogicalDisk",
            ["Name", "DiskWriteBytesPerSec", "DiskWritesPerSec", "DiskReadBytesPerSec",
             "DiskReadsPerSec", "CurrentDiskQueueLength"]
        )

        self.gauge('system.io.wkb_s')
        self.gauge('system.io.w_s')
        self.gauge('system.io.rkb_s')
        self.gauge('system.io.r_s')
        self.gauge('system.io.avg_q_sz')

    def check(self, agentConfig):
        try:
            self.wmi_sampler.sample()
        except TimeoutException:
            self.logger.warning(
                u"Timeout while querying Win32_PerfRawData_PerfDisk_LogicalDiskUnable WMI class."
                u" I/O metrics will be returned at next iteration."
            )
            return []

        if not (len(self.wmi_sampler)):
            self.logger.warning('Missing Win32_PerfRawData_PerfDisk_LogicalDiskUnable WMI class.'
                             ' No I/O metrics will be returned.')
            return []

        blacklist_re = agentConfig.get('device_blacklist_re', None)
        for device in self.wmi_sampler:
            name = device.get('Name')
            disk_write_bytes_per_sec = device.get('DiskWriteBytesPerSec')
            disk_writes_per_sec = device.get('DiskWritesPerSec')
            disk_read_bytes_per_sec = device.get('DiskReadBytesPerSec')
            disk_reads_per_sec = device.get('DiskReadsPerSec')
            current_disk_queue_length = device.get('CurrentDiskQueueLength')

            name = self.normalize_device_name(name)
            if should_ignore_disk(name, blacklist_re):
                continue
            if disk_write_bytes_per_sec is not None:
                self.save_sample('system.io.wkb_s', int(disk_write_bytes_per_sec) / B2KB,
                                 device_name=name)
            if disk_writes_per_sec is not None:
                self.save_sample('system.io.w_s', int(disk_writes_per_sec),
                                 device_name=name)
            if disk_read_bytes_per_sec is not None:
                self.save_sample('system.io.rkb_s', int(disk_read_bytes_per_sec) / B2KB,
                                 device_name=name)
            if disk_reads_per_sec is not None:
                self.save_sample('system.io.r_s', int(disk_reads_per_sec),
                                 device_name=name)
            if current_disk_queue_length is not None:
                self.save_sample('system.io.avg_q_sz', current_disk_queue_length,
                                 device_name=name)
        return self.get_metrics()


class System(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.gauge('system.uptime')

    def check(self, agentConfig):
        self.save_sample('system.uptime', uptime.uptime())

        return self.get_metrics()
