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
try:
    from datadog_checks.checks.win import WinPDHCounter
except ImportError:
    def WinPDHCounter(*args, **kwargs):
        return

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

        self.gauge('system.proc.queue_length')
        self.gauge('system.proc.count')
        self.numprocs = WinPDHCounter('System', 'Processes', logger)
        self.pql = WinPDHCounter('System', 'Processor Queue Length', logger)

    def check(self, agentConfig):
        processor_queue_length = self.pql.get_single_value()
        processes = self.numprocs.get_single_value()

        if processor_queue_length is not None:
            self.save_sample('system.proc.queue_length', processor_queue_length)
        if processes is not None:
            self.save_sample('system.proc.count', processes)

        return self.get_metrics()


class Memory(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

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
        self.gauge('system.mem.pagefile.total')
        self.gauge('system.mem.pagefile.used')
        self.gauge('system.mem.pagefile.free')
        self.gauge('system.mem.pagefile.pct_free')

        self.cache_bytes_counter = WinPDHCounter('Memory', 'Cache Bytes', logger)
        self.committed_bytes_counter = WinPDHCounter('Memory', 'Committed Bytes', logger)
        self.pool_paged_bytes_counter = WinPDHCounter('Memory', 'Pool Paged Bytes', logger)
        self.pool_non_paged_bytes_counter = WinPDHCounter('Memory', 'Pool Nonpaged Bytes', logger)

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
            self.save_sample('system.mem.total', total)
            self.save_sample('system.mem.free', free)
            self.save_sample('system.mem.used', total - free)

        cache_bytes = self.cache_bytes_counter.get_single_value()
        committed_bytes = self.committed_bytes_counter.get_single_value()
        pool_paged_bytes = self.pool_paged_bytes_counter.get_single_value()
        pool_non_paged_bytes = self.pool_non_paged_bytes_counter.get_single_value()

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

        # swap_memory pulls from the pagefile data,
        # rather than from the whole virtual memory data.
        page = psutil.swap_memory()
        if page.total is not None:
            self.save_sample('system.mem.pagefile.total', page.total)
            self.save_sample('system.mem.pagefile.used', page.used)
            self.save_sample('system.mem.pagefile.free', page.free)
            self.save_sample('system.mem.pagefile.pct_free', (100 - page.percent) / 100)

        return self.get_metrics()


class Cpu(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        self.counter('system.cpu.user')
        self.counter('system.cpu.idle')
        self.counter('system.cpu.system')
        self.counter('system.cpu.interrupt')

    def check(self, agentConfig):
        cpu_percent = psutil.cpu_times()

        self.save_sample('system.cpu.user', 100 * cpu_percent.user / psutil.cpu_count())
        self.save_sample('system.cpu.idle', 100 * cpu_percent.idle / psutil.cpu_count())
        self.save_sample('system.cpu.system', 100 * cpu_percent.system / psutil.cpu_count())
        self.save_sample('system.cpu.interrupt', 100 * cpu_percent.interrupt / psutil.cpu_count())

        return self.get_metrics()


class IO(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

        self.gauge('system.io.wkb_s')
        self.gauge('system.io.w_s')
        self.gauge('system.io.rkb_s')
        self.gauge('system.io.r_s')
        self.gauge('system.io.avg_q_sz')

        self.dwbpscounter = WinPDHCounter('LogicalDisk', 'Disk Write Bytes/sec', logger)
        self.dwpscounter = WinPDHCounter('LogicalDisk', 'Disk Writes/sec', logger)
        self.drbpscounter = WinPDHCounter('LogicalDisk', 'Disk Read Bytes/sec', logger)
        self.drpscounter = WinPDHCounter('LogicalDisk', 'Disk Reads/sec', logger)
        self.qszcounter = WinPDHCounter('LogicalDisk', 'Current Disk Queue Length', logger)

    def check(self, agentConfig):
        dwbps = self.dwbpscounter.get_all_values()
        dwps = self.dwpscounter.get_all_values()
        drbps = self.drbpscounter.get_all_values()
        drps = self.drpscounter.get_all_values()
        qsz = self.qszcounter.get_all_values()

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
