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


# datadog
from utils.timeout import TimeoutException
from checks.libs.win.winpdh import WinPDHCounter


# Device WMI drive types
class DriveType(object):
    UNKNOWN, NOROOT, REMOVEABLE, LOCAL, NETWORK, CD, RAM = (0, 1, 2, 3, 4, 5, 6)
B2MB = float(1048576)
KB2MB = B2KB = float(1024)


def should_ignore_disk(name, blacklist_re):
    # blacklist_re is a compiled regex, compilation done at config loading time
    return name == '_total' or blacklist_re is not None and blacklist_re.match(name)


class ProcessesNew(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

       
        self.gauge('system.new.proc.queue_length')
        self.gauge('system.new.proc.count')

    def check(self, agentConfig):
        numprocs = WinPDHCounter('System', 'Processes')
        pql = WinPDHCounter('System', 'Processor Queue Length')
        
        processor_queue_length = pql.get_single_value()
        processes = numprocs.get_single_value()

        if processor_queue_length is not None:
            self.save_sample('system.new.proc.queue_length', processor_queue_length)
        if processes is not None:
            self.save_sample('system.new.proc.count', processes)

        return self.get_metrics()


class MemoryNew(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        self.gauge('system.new.mem.free')
        self.gauge('system.new.mem.used')
        self.gauge('system.new.mem.total')
        # area of physical memory that stores recently used pages of data
        # for applications
        self.gauge('system.new.mem.cached')
        # Committed memory is physical memory for which space has been
        # reserved on the disk paging file in case it must be written
        # back to disk
        self.gauge('system.new.mem.committed')
        # physical memory used by the operating system, for objects
        # that can be written to disk when they are not being used
        self.gauge('system.new.mem.paged')
        # physical memory used by the operating system for objects that
        # cannot be written to disk, but must remain in physical memory
        # as long as they are allocated.
        self.gauge('system.new.mem.nonpaged')
        # usable = free + cached
        self.gauge('system.new.mem.usable')
        self.gauge('system.new.mem.pct_usable')
        #  details about the usage of the pagefile.
        self.gauge('system.new.mem.page_total')
        self.gauge('system.new.mem.page_used')
        self.gauge('system.new.mem.page_free')
        self.gauge('system.new.mem.page_pct_free')

    def check(self, agentConfig):
        
        total = 0
        free = 0
        cached = 0
        mem = psutil.virtual_memory()
        total_visible_memory_size = mem.total / B2KB
        free_physical_memory = mem.available / B2KB

        if total_visible_memory_size is not None and free_physical_memory is not None:
            total = int(total_visible_memory_size) / KB2MB
            free = int(free_physical_memory) / KB2MB
            self.save_sample('system.new.mem.total', total)
            self.save_sample('system.new.mem.free', free)
            self.save_sample('system.new.mem.used', total - free)

        cache_bytes = WinPDHCounter('Memory', 'Cache Bytes').get_single_value()
        committed_bytes = WinPDHCounter('Memory', 'Committed Bytes').get_single_value()
        pool_paged_bytes = WinPDHCounter('Memory', 'Pool Paged Bytes').get_single_value()
        pool_non_paged_bytes = WinPDHCounter('Memory', 'Pool Nonpaged Bytes').get_single_value()

        if cache_bytes is not None:
            cached = int(cache_bytes) / B2MB
            self.save_sample('system.new.mem.cached', cached)
        if committed_bytes is not None:
            self.save_sample('system.new.mem.committed', int(committed_bytes) / B2MB)
        if pool_paged_bytes is not None:
            self.save_sample('system.new.mem.paged', int(pool_paged_bytes) / B2MB)
        if pool_non_paged_bytes is not None:
            self.save_sample('system.new.mem.nonpaged', int(pool_non_paged_bytes) / B2MB)

        usable = free + cached
        self.save_sample('system.new.mem.usable', usable)
        if total > 0:
            pct_usable = float(usable) / total
            self.save_sample('system.new.mem.pct_usable', pct_usable)

        page = psutil.virtual_memory()
        if page.total is not None:
            self.save_sample('system.new.mem.page_total', page.total / B2MB)
            self.save_sample('system.new.mem.page_used', page.used / B2MB)
            self.save_sample('system.new.mem.page_free', page.available / B2MB)
            self.save_sample('system.new.mem.page_pct_free', (100 - page.percent) / 100)

        return self.get_metrics()


class CpuNew(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        self.counter('system.new.cpu.user')
        self.counter('system.new.cpu.idle')
        self.counter('system.new.cpu.system')
        self.counter('system.new.cpu.interrupt')

    def check(self, agentConfig):
        cpu_percent = psutil.cpu_times()

        self.save_sample('system.new.cpu.user', 100 * cpu_percent.user / psutil.cpu_count())
        self.save_sample('system.new.cpu.idle', 100 * cpu_percent.idle / psutil.cpu_count())
        self.save_sample('system.new.cpu.system', 100 * cpu_percent.system / psutil.cpu_count())
        self.save_sample('system.new.cpu.interrupt', 100 * cpu_percent.interrupt / psutil.cpu_count())

        return self.get_metrics()


class NetworkNew(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        self.gauge('system.new.net.bytes_rcvd')
        self.gauge('system.new.net.bytes_sent')

    def check(self, agentConfig):
        rcvd = WinPDHCounter('Network Interface', 'Bytes Received/sec').get_all_values()
        sent = WinPDHCounter('Network Interface', 'Bytes Sent/sec').get_all_values()

        for devname, rate in rcvd.iteritems():
            name = self.normalize_device_name(devname)
            self.save_sample('system.new.net.bytes_rcvd', rate, device_name = name)

        for devname, rate in sent.iteritems():
            name = self.normalize_device_name(devname)
            self.save_sample('system.new.net.bytes_sent', rate, device_name = name)

        return self.get_metrics()


class IONew(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        self.gauge('system.new.io.wkb_s')
        self.gauge('system.new.io.w_s')
        self.gauge('system.new.io.rkb_s')
        self.gauge('system.new.io.r_s')
        self.gauge('system.new.io.avg_q_sz')

    def check(self, agentConfig):
        dwbps = WinPDHCounter('LogicalDisk', 'Disk Write Bytes/sec').get_all_values()
        dwps = WinPDHCounter('LogicalDisk', 'Disk Writes/sec').get_all_values()
        drbps = WinPDHCounter('LogicalDisk', 'Disk Read Bytes/sec').get_all_values()
        drps = WinPDHCounter('LogicalDisk', 'Disk Reads/sec').get_all_values()
        qsz = WinPDHCounter('LogicalDisk', 'Current Disk Queue Length').get_all_values()

        # all of the maps should have the same keys (since there's only one
        # set of disks
        blacklist_re = agentConfig.get('device_blacklist_re', None)
        for device in dwbps:
            name = self.normalize_device_name(device)
            if should_ignore_disk(name, blacklist_re):
                continue

            disk_write_bytes_per_sec = dwbps[device]
            disk_writes_per_sec = dwps[device]
            disk_read_bytes_per_sec = drbps[device]
            disk_reads_per_sec = drps[device]
            current_disk_queue_length = qsz[device]

            if disk_write_bytes_per_sec is not None:
                self.save_sample('system.new.io.wkb_s', int(disk_write_bytes_per_sec) / B2KB,
                                 device_name=name)
            if disk_writes_per_sec is not None:
                self.save_sample('system.new.io.w_s', int(disk_writes_per_sec),
                                 device_name=name)
            if disk_read_bytes_per_sec is not None:
                self.save_sample('system.new.io.rkb_s', int(disk_read_bytes_per_sec) / B2KB,
                                 device_name=name)
            if disk_reads_per_sec is not None:
                self.save_sample('system.new.io.r_s', int(disk_reads_per_sec),
                                 device_name=name)
            if current_disk_queue_length is not None:
                self.save_sample('system.new.io.avg_q_sz', current_disk_queue_length,
                                 device_name=name)
        return self.get_metrics()


class SystemNew(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.gauge('system.new.uptime')

    def check(self, agentConfig):
        self.save_sample('system.new.uptime', uptime.uptime())

        return self.get_metrics()
