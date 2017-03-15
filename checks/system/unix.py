# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""
Unix system checks.
"""
# stdlib
import operator
import platform
import re
import sys
import time

# 3rd party
import uptime
try:
    import psutil
except ImportError:
    psutil = None

# project
from checks import Check
from utils.hostname import get_hostname
from utils.platform import Platform
from utils.subprocess_output import get_subprocess_output


# locale-resilient float converter
to_float = lambda s: float(s.replace(",", "."))


class IO(Check):

    def __init__(self, logger):
        Check.__init__(self, logger)
        self.header_re = re.compile(r'([%\\/\-_a-zA-Z0-9]+)[\s+]?')
        self.item_re = re.compile(r'^([\-a-zA-Z0-9\/]+)')
        self.value_re = re.compile(r'\d+\.\d+')

    def _parse_linux2(self, output):
        recentStats = output.split('Device:')[2].split('\n')
        header = recentStats[0]
        headerNames = re.findall(self.header_re, header)
        device = None

        ioStats = {}

        for statsIndex in range(1, len(recentStats)):
            row = recentStats[statsIndex]

            if not row:
                # Ignore blank lines.
                continue

            deviceMatch = self.item_re.match(row)

            if deviceMatch is not None:
                # Sometimes device names span two lines.
                device = deviceMatch.groups()[0]
            else:
                continue

            values = re.findall(self.value_re, row)

            if not values:
                # Sometimes values are on the next line so we encounter
                # instances of [].
                continue

            ioStats[device] = {}

            for headerIndex in range(len(headerNames)):
                headerName = headerNames[headerIndex]
                ioStats[device][headerName] = values[headerIndex]

        return ioStats

    def _parse_darwin(self, output):
        lines = [l.split() for l in output.split("\n") if len(l) > 0]
        disks = lines[0]
        lastline = lines[-1]
        io = {}
        for idx, disk in enumerate(disks):
            kb_t, tps, mb_s = map(float, lastline[(3 * idx):(3 * idx) + 3])  # 3 cols at a time
            io[disk] = {
                'system.io.bytes_per_s': mb_s * 2**20,
            }
        return io

    def xlate(self, metric_name, os_name):
        """Standardize on linux metric names"""
        if os_name == "sunos":
            names = {
                "wait": "await",
                "svc_t": "svctm",
                "%b": "%util",
                "kr/s": "rkB/s",
                "kw/s": "wkB/s",
                "actv": "avgqu-sz",
            }
        elif os_name == "freebsd":
            names = {
                "svc_t": "await",
                "%b": "%util",
                "kr/s": "rkB/s",
                "kw/s": "wkB/s",
                "wait": "avgqu-sz",
            }
        # translate if possible
        return names.get(metric_name, metric_name)

    def check(self, agentConfig):
        """Capture io stats.

        @rtype dict
        @return {"device": {"metric": value, "metric": value}, ...}
        """
        io = {}
        try:
            if Platform.is_linux():
                stdout, _, _ = get_subprocess_output(['iostat', '-d', '1', '2', '-x', '-k'], self.logger)

                #                 Linux 2.6.32-343-ec2 (ip-10-35-95-10)   12/11/2012      _x86_64_        (2 CPU)
                #
                # Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
                # sda1              0.00    17.61    0.26   32.63     4.23   201.04    12.48     0.16    4.81   0.53   1.73
                # sdb               0.00     2.68    0.19    3.84     5.79    26.07    15.82     0.02    4.93   0.22   0.09
                # sdg               0.00     0.13    2.29    3.84   100.53    30.61    42.78     0.05    8.41   0.88   0.54
                # sdf               0.00     0.13    2.30    3.84   100.54    30.61    42.78     0.06    9.12   0.90   0.55
                # md0               0.00     0.00    0.05    3.37     1.41    30.01    18.35     0.00    0.00   0.00   0.00
                #
                # Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
                # sda1              0.00     0.00    0.00   10.89     0.00    43.56     8.00     0.03    2.73   2.73   2.97
                # sdb               0.00     0.00    0.00    2.97     0.00    11.88     8.00     0.00    0.00   0.00   0.00
                # sdg               0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00   0.00   0.00
                # sdf               0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00   0.00   0.00
                # md0               0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00   0.00   0.00
                io.update(self._parse_linux2(stdout))

            elif sys.platform == "sunos5":
                output, _, _ = get_subprocess_output(["iostat", "-x", "-d", "1", "2"], self.logger)
                iostat = output.splitlines()

                #                   extended device statistics <-- since boot
                # device      r/s    w/s   kr/s   kw/s wait actv  svc_t  %w  %b
                # ramdisk1    0.0    0.0    0.1    0.1  0.0  0.0    0.0   0   0
                # sd0         0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
                # sd1        79.9  149.9 1237.6 6737.9  0.0  0.5    2.3   0  11
                #                   extended device statistics <-- past second
                # device      r/s    w/s   kr/s   kw/s wait actv  svc_t  %w  %b
                # ramdisk1    0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
                # sd0         0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
                # sd1         0.0  139.0    0.0 1850.6  0.0  0.0    0.1   0   1

                # discard the first half of the display (stats since boot)
                lines = [l for l in iostat if len(l) > 0]
                lines = lines[len(lines)/2:]

                assert "extended device statistics" in lines[0]
                headers = lines[1].split()
                assert "device" in headers
                for l in lines[2:]:
                    cols = l.split()
                    # cols[0] is the device
                    # cols[1:] are the values
                    io[cols[0]] = {}
                    for i in range(1, len(cols)):
                        io[cols[0]][self.xlate(headers[i], "sunos")] = cols[i]

            elif sys.platform.startswith("freebsd"):
                output, _, _ = get_subprocess_output(["iostat", "-x", "-d", "1", "2"], self.logger)
                iostat = output.splitlines()

                # Be careful!
                # It looks like SunOS, but some columms (wait, svc_t) have different meaning
                #                        extended device statistics
                # device     r/s   w/s    kr/s    kw/s wait svc_t  %b
                # ad0        3.1   1.3    49.9    18.8    0   0.7   0
                #                         extended device statistics
                # device     r/s   w/s    kr/s    kw/s wait svc_t  %b
                # ad0        0.0   2.0     0.0    31.8    0   0.2   0

                # discard the first half of the display (stats since boot)
                lines = [l for l in iostat if len(l) > 0]
                lines = lines[len(lines)/2:]

                assert "extended device statistics" in lines[0]
                headers = lines[1].split()
                assert "device" in headers
                for l in lines[2:]:
                    cols = l.split()
                    # cols[0] is the device
                    # cols[1:] are the values
                    io[cols[0]] = {}
                    for i in range(1, len(cols)):
                        io[cols[0]][self.xlate(headers[i], "freebsd")] = cols[i]
            elif sys.platform == 'darwin':
                iostat, _, _ = get_subprocess_output(['iostat', '-d', '-c', '2', '-w', '1'], self.logger)
                #          disk0           disk1          <-- number of disks
                #    KB/t tps  MB/s     KB/t tps  MB/s
                #   21.11  23  0.47    20.01   0  0.00
                #    6.67   3  0.02     0.00   0  0.00    <-- line of interest
                io = self._parse_darwin(iostat)
            else:
                return False

            # If we filter devices, do it know.
            device_blacklist_re = agentConfig.get('device_blacklist_re', None)
            if device_blacklist_re:
                filtered_io = {}
                for device, stats in io.iteritems():
                    if not device_blacklist_re.match(device):
                        filtered_io[device] = stats
            else:
                filtered_io = io
            return filtered_io

        except Exception:
            self.logger.exception("Cannot extract IO statistics")
            return False


class Load(Check):

    def check(self, agentConfig):
        if Platform.is_linux():
            proc_location = agentConfig.get('procfs_path', '/proc').rstrip('/')
            try:
                proc_loadavg = "{}/loadavg".format(proc_location)
                with open(proc_loadavg, 'r') as load_avg:
                    uptime = load_avg.readline().strip()
            except Exception:
                self.logger.exception('Cannot extract load')
                return False

        elif sys.platform in ('darwin', 'sunos5') or sys.platform.startswith("freebsd"):
            # Get output from uptime
            try:
                uptime, _, _ = get_subprocess_output(['uptime'], self.logger)
            except Exception:
                self.logger.exception('Cannot extract load')
                return False

        # Split out the 3 load average values
        load = [res.replace(',', '.') for res in re.findall(r'([0-9]+[\.,]\d+)', uptime)]
        # Normalize load by number of cores
        try:
            cores = int(agentConfig.get('system_stats').get('cpuCores'))
            assert cores >= 1, "Cannot determine number of cores"
            # Compute a normalized load, named .load.norm to make it easy to find next to .load
            return {'system.load.1': float(load[0]),
                    'system.load.5': float(load[1]),
                    'system.load.15': float(load[2]),
                    'system.load.norm.1': float(load[0])/cores,
                    'system.load.norm.5': float(load[1])/cores,
                    'system.load.norm.15': float(load[2])/cores,
                    }
        except Exception:
            # No normalized load available
            return {'system.load.1': float(load[0]),
                    'system.load.5': float(load[1]),
                    'system.load.15': float(load[2])}


class Memory(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        macV = None
        if sys.platform == 'darwin':
            macV = platform.mac_ver()
            macV_minor_version = int(re.match(r'10\.(\d+)\.?.*', macV[0]).group(1))

        # Output from top is slightly modified on OS X 10.6 (case #28239) and greater
        if macV and (macV_minor_version >= 6):
            self.topIndex = 6
        else:
            self.topIndex = 5

        self.pagesize = 0
        if sys.platform == 'sunos5':
            try:
                pgsz, _, _ = get_subprocess_output(['pagesize'], self.logger)
                self.pagesize = int(pgsz.strip())
            except Exception:
                # No page size available
                pass

    def check(self, agentConfig):
        if Platform.is_linux():
            proc_location = agentConfig.get('procfs_path', '/proc').rstrip('/')
            try:
                proc_meminfo = "{}/meminfo".format(proc_location)
                with open(proc_meminfo, 'r') as mem_info:
                    lines = mem_info.readlines()
            except Exception:
                self.logger.exception('Cannot get memory metrics from %s', proc_meminfo)
                return False

            # NOTE: not all of the stats below are present on all systems as
            # not all kernel versions report all of them.
            #
            # $ cat /proc/meminfo
            # MemTotal:        7995360 kB
            # MemFree:         1045120 kB
            # MemAvailable:    1253920 kB
            # Buffers:          226284 kB
            # Cached:           775516 kB
            # SwapCached:       248868 kB
            # Active:          1004816 kB
            # Inactive:        1011948 kB
            # Active(anon):     455152 kB
            # Inactive(anon):   584664 kB
            # Active(file):     549664 kB
            # Inactive(file):   427284 kB
            # Unevictable:     4392476 kB
            # Mlocked:         4392476 kB
            # SwapTotal:      11120632 kB
            # SwapFree:       10555044 kB
            # Dirty:              2948 kB
            # Writeback:             0 kB
            # AnonPages:       5203560 kB
            # Mapped:            50520 kB
            # Shmem:             10108 kB
            # Slab:             161300 kB
            # SReclaimable:     136108 kB
            # SUnreclaim:        25192 kB
            # KernelStack:        3160 kB
            # PageTables:        26776 kB
            # NFS_Unstable:          0 kB
            # Bounce:                0 kB
            # WritebackTmp:          0 kB
            # CommitLimit:    15118312 kB
            # Committed_AS:    6703508 kB
            # VmallocTotal:   34359738367 kB
            # VmallocUsed:      400668 kB
            # VmallocChunk:   34359329524 kB
            # HardwareCorrupted:     0 kB
            # HugePages_Total:       0
            # HugePages_Free:        0
            # HugePages_Rsvd:        0
            # HugePages_Surp:        0
            # Hugepagesize:       2048 kB
            # DirectMap4k:       10112 kB
            # DirectMap2M:     8243200 kB

            regexp = re.compile(r'^(\w+):\s+([0-9]+)')  # We run this several times so one-time compile now
            meminfo = {}

            parse_error = False
            for line in lines:
                try:
                    match = re.search(regexp, line)
                    if match is not None:
                        meminfo[match.group(1)] = match.group(2)
                except Exception:
                    parse_error = True
            if parse_error:
                self.logger.error("Error parsing %s", proc_meminfo)

            memData = {}

            # Physical memory
            # FIXME units are in MB, we should use bytes instead
            try:
                memData['physTotal'] = int(meminfo.get('MemTotal', 0)) / 1024
                memData['physFree'] = int(meminfo.get('MemFree', 0)) / 1024
                memData['physBuffers'] = int(meminfo.get('Buffers', 0)) / 1024
                memData['physCached'] = int(meminfo.get('Cached', 0)) / 1024
                memData['physShared'] = int(meminfo.get('Shmem', 0)) / 1024
                memData['physSlab'] = int(meminfo.get('Slab', 0)) / 1024
                memData['physPageTables'] = int(meminfo.get('PageTables', 0)) / 1024
                memData['physUsed'] = memData['physTotal'] - memData['physFree']

                if 'MemAvailable' in meminfo:
                    memData['physUsable'] = int(meminfo.get('MemAvailable', 0)) / 1024
                else:
                    # Usable is relative since cached and buffers are actually used to speed things up.
                    memData['physUsable'] = memData['physFree'] + memData['physBuffers'] + memData['physCached']

                if memData['physTotal'] > 0:
                    memData['physPctUsable'] = float(memData['physUsable']) / float(memData['physTotal'])
            except Exception:
                self.logger.exception('Cannot compute stats from %s', proc_meminfo)

            # Swap
            # FIXME units are in MB, we should use bytes instead
            try:
                memData['swapTotal'] = int(meminfo.get('SwapTotal', 0)) / 1024
                memData['swapFree'] = int(meminfo.get('SwapFree', 0)) / 1024
                memData['swapCached'] = int(meminfo.get('SwapCached', 0)) / 1024

                memData['swapUsed'] = memData['swapTotal'] - memData['swapFree']

                if memData['swapTotal'] > 0:
                    memData['swapPctFree'] = float(memData['swapFree']) / float(memData['swapTotal'])
            except Exception:
                self.logger.exception('Cannot compute swap stats')

            return memData

        elif sys.platform == 'darwin':
            if psutil is None:
                self.logger.error("psutil must be installed on MacOS to collect memory metrics")
                return False

            phys_memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {'physUsed': phys_memory.used / float(1024**2),
                'physFree': phys_memory.free / float(1024**2),
                'physUsable': phys_memory.available / float(1024**2),
                'physPctUsable': (100 - phys_memory.percent) / 100.0,
                'swapUsed': swap.used / float(1024**2),
                'swapFree': swap.free / float(1024**2)}

        elif sys.platform.startswith("freebsd"):
            try:
                output, _, _ = get_subprocess_output(['sysctl', 'vm.stats.vm'], self.logger)
                sysctl = output.splitlines()
            except Exception:
                self.logger.exception('getMemoryUsage')
                return False

            # ...
            # vm.stats.vm.v_page_size: 4096
            # vm.stats.vm.v_page_count: 759884
            # vm.stats.vm.v_wire_count: 122726
            # vm.stats.vm.v_active_count: 109350
            # vm.stats.vm.v_cache_count: 17437
            # vm.stats.vm.v_inactive_count: 479673
            # vm.stats.vm.v_free_count: 30542
            # ...

            # We run this several times so one-time compile now
            regexp = re.compile(r'^vm\.stats\.vm\.(\w+):\s+([0-9]+)')
            meminfo = {}

            parse_error = False
            for line in sysctl:
                try:
                    match = re.search(regexp, line)
                    if match is not None:
                        meminfo[match.group(1)] = match.group(2)
                except Exception:
                    parse_error = True
            if parse_error:
                self.logger.error("Error parsing vm.stats.vm output: %s", sysctl)

            memData = {}

            # Physical memory
            try:
                pageSize = int(meminfo.get('v_page_size'))

                memData['physTotal'] = (int(meminfo.get('v_page_count', 0))
                                        * pageSize) / 1048576
                memData['physFree'] = (int(meminfo.get('v_free_count', 0))
                                       * pageSize) / 1048576
                memData['physCached'] = (int(meminfo.get('v_cache_count', 0))
                                         * pageSize) / 1048576
                memData['physUsed'] = ((int(meminfo.get('v_active_count'), 0) +
                                        int(meminfo.get('v_wire_count', 0)))
                                       * pageSize) / 1048576
                memData['physUsable'] = ((int(meminfo.get('v_free_count'), 0) +
                                          int(meminfo.get('v_cache_count', 0)) +
                                          int(meminfo.get('v_inactive_count', 0))) *
                                         pageSize) / 1048576

                if memData['physTotal'] > 0:
                    memData['physPctUsable'] = float(memData['physUsable']) / float(memData['physTotal'])
            except Exception:
                self.logger.exception('Cannot compute stats from %s', proc_meminfo)

            # Swap
            try:
                output, _, _ = get_subprocess_output(['swapinfo', '-m'], self.logger)
                sysctl = output.splitlines()
            except Exception:
                self.logger.exception('getMemoryUsage')
                return False

            # ...
            # Device          1M-blocks     Used    Avail Capacity
            # /dev/ad0s1b           570        0      570     0%
            # ...

            assert "Device" in sysctl[0]

            try:
                memData['swapTotal'] = 0
                memData['swapFree'] = 0
                memData['swapUsed'] = 0
                for line in sysctl[1:]:
                    if len(line) > 0:
                        line = line.split()
                        memData['swapTotal'] += int(line[1])
                        memData['swapFree'] += int(line[3])
                        memData['swapUsed'] += int(line[2])
            except Exception:
                self.logger.exception('Cannot compute stats from swapinfo')

            return memData
        elif sys.platform == 'sunos5':
            try:
                memData = {}
                cmd = ["kstat", "-m", "memory_cap", "-c", "zone_memory_cap", "-p"]
                output, _, _ = get_subprocess_output(cmd, self.logger)
                kmem = output.splitlines()

                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:anon_alloc_fail   0
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:anonpgin  0
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:class     zone_memory_cap
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:crtime    16359935.0680834
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:execpgin  185
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:fspgin    2556
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:n_pf_throttle     0
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:n_pf_throttle_usec        0
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:nover     0
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:pagedout  0
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:pgpgin    2741
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:physcap   536870912  <--
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:rss       115544064  <--
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:snaptime  16787393.9439095
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:swap      91828224   <--
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:swapcap   1073741824 <--
                # memory_cap:360:53aa9b7e-48ba-4152-a52b-a6368c:zonename  53aa9b7e-48ba-4152-a52b-a6368c3d9e7c

                # turn memory_cap:360:zone_name:key value
                # into { "key": value, ...}
                kv = [l.strip().split() for l in kmem if len(l) > 0]
                entries = dict([(k.split(":")[-1], v) for (k, v) in kv])
                # extract rss, physcap, swap, swapcap, turn into MB
                convert = lambda v: int(long(v))/2**20
                memData["physTotal"] = convert(entries["physcap"])
                memData["physUsed"] = convert(entries["rss"])
                memData["physFree"] = memData["physTotal"] - memData["physUsed"]
                memData["swapTotal"] = convert(entries["swapcap"])
                memData["swapUsed"] = convert(entries["swap"])
                memData["swapFree"] = memData["swapTotal"] - memData["swapUsed"]

                if memData['swapTotal'] > 0:
                    memData['swapPctFree'] = float(memData['swapFree']) / float(memData['swapTotal'])
                return memData
            except Exception:
                self.logger.exception("Cannot compute mem stats from kstat -c zone_memory_cap")
                return False
        else:
            return False


class Processes(Check):

    def check(self, agentConfig):
        process_exclude_args = agentConfig.get('exclude_process_args', False)
        if process_exclude_args:
            ps_arg = 'aux'
        else:
            ps_arg = 'auxww'
        # Get output from ps
        try:
            output, _, _ = get_subprocess_output(['ps', ps_arg], self.logger)
            processLines = output.splitlines()  # Also removes a trailing empty line

            del processLines[0]  # Removes the headers
        except Exception:
            self.logger.exception('getProcesses')
            return False

        processes = []

        for line in processLines:
            line = line.split(None, 10)
            processes.append(map(lambda s: s.strip(), line))

        return {'processes':   processes,
                'apiKey':      agentConfig['api_key'],
                'host':        get_hostname(agentConfig)}


class Cpu(Check):

    def check(self, agentConfig):
        """Return an aggregate of CPU stats across all CPUs
        When figures are not available, False is sent back.
        """
        def format_results(us, sy, wa, idle, st, guest=None):
            data = {'cpuUser': us, 'cpuSystem': sy, 'cpuWait': wa, 'cpuIdle': idle, 'cpuStolen': st, 'cpuGuest': guest}
            return dict((k, v) for k, v in data.iteritems() if v is not None)

        def get_value(legend, data, name, filter_value=None):
            "Using the legend and a metric name, get the value or None from the data line"
            if name in legend:
                value = to_float(data[legend.index(name)])
                if filter_value is not None:
                    if value > filter_value:
                        return None
                return value

            else:
                # FIXME return a float or False, would trigger type error if not python
                self.logger.debug("Cannot extract cpu value %s from %s (%s)" % (name, data, legend))
                return 0.0
        try:
            if Platform.is_linux():
                output, _, _ = get_subprocess_output(['mpstat', '1', '3'], self.logger)
                mpstat = output.splitlines()
                # topdog@ip:~$ mpstat 1 3
                # Linux 2.6.32-341-ec2 (ip)   01/19/2012  _x86_64_  (2 CPU)
                #
                # 04:22:41 PM  CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest   %idle
                # 04:22:42 PM  all    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00  100.00
                # 04:22:43 PM  all    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00  100.00
                # 04:22:44 PM  all    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00  100.00
                # Average:     all    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00  100.00
                #
                # OR
                #
                # Thanks to Mart Visser to spotting this one.
                # blah:/etc/dd-agent# mpstat
                # Linux 2.6.26-2-xen-amd64 (atira)  02/17/2012  _x86_64_
                #
                # 05:27:03 PM  CPU    %user   %nice   %sys %iowait    %irq   %soft  %steal  %idle   intr/s
                # 05:27:03 PM  all    3.59    0.00    0.68    0.69    0.00   0.00    0.01   95.03    43.65
                #
                legend = [l for l in mpstat if "%usr" in l or "%user" in l]
                avg = [l for l in mpstat if "Average" in l]
                if len(legend) == 1 and len(avg) == 1:
                    headers = [h for h in legend[0].split() if h not in ("AM", "PM")]
                    data = avg[0].split()

                    # Userland
                    # Debian lenny says %user so we look for both
                    # One of them will be 0
                    cpu_metrics = {
                        "%usr": None, "%user": None, "%nice": None,
                        "%iowait": None, "%idle": None, "%sys": None,
                        "%irq": None, "%soft": None, "%steal": None,
                        "%guest": None
                    }

                    for cpu_m in cpu_metrics:
                        cpu_metrics[cpu_m] = get_value(headers, data, cpu_m, filter_value=110)

                    if any([v is None for v in cpu_metrics.values()]):
                        self.logger.warning("Invalid mpstat data: %s" % data)

                    cpu_user = cpu_metrics["%usr"] + cpu_metrics["%user"] + cpu_metrics["%nice"]
                    cpu_system = cpu_metrics["%sys"] + cpu_metrics["%irq"] + cpu_metrics["%soft"]
                    cpu_wait = cpu_metrics["%iowait"]
                    cpu_idle = cpu_metrics["%idle"]
                    cpu_stolen = cpu_metrics["%steal"]
                    cpu_guest = cpu_metrics["%guest"]

                    return format_results(cpu_user,
                                          cpu_system,
                                          cpu_wait,
                                          cpu_idle,
                                          cpu_stolen,
                                          cpu_guest)
                else:
                    return False

            elif sys.platform == 'darwin':
                # generate 3 seconds of data
                # ['          disk0           disk1       cpu     load average', '    KB/t tps  MB/s     KB/t tps  MB/s  us sy id   1m   5m   15m', '   21.23  13  0.27    17.85   7  0.13  14  7 79  1.04 1.27 1.31', '    4.00   3  0.01     5.00   8  0.04  12 10 78  1.04 1.27 1.31', '']
                iostats, _, _ = get_subprocess_output(['iostat', '-C', '-w', '3', '-c', '2'], self.logger)
                lines = [l for l in iostats.splitlines() if len(l) > 0]
                legend = [l for l in lines if "us" in l]
                if len(legend) == 1:
                    headers = legend[0].split()
                    data = lines[-1].split()
                    cpu_user = get_value(headers, data, "us")
                    cpu_sys = get_value(headers, data, "sy")
                    cpu_wait = 0
                    cpu_idle = get_value(headers, data, "id")
                    cpu_st = 0
                    return format_results(cpu_user, cpu_sys, cpu_wait, cpu_idle, cpu_st)
                else:
                    self.logger.warn("Expected to get at least 4 lines of data from iostat instead of just " + str(iostats[:max(80, len(iostats))]))
                    return False

            elif sys.platform.startswith("freebsd"):
                # generate 3 seconds of data
                # tty            ada0              cd0            pass0             cpu
                # tin  tout  KB/t tps  MB/s   KB/t tps  MB/s   KB/t tps  MB/s  us ni sy in id
                # 0    69 26.71   0  0.01   0.00   0  0.00   0.00   0  0.00   2  0  0  1 97
                # 0    78  0.00   0  0.00   0.00   0  0.00   0.00   0  0.00   0  0  0  0 100
                iostats, _, _ = get_subprocess_output(['iostat', '-w', '3', '-c', '2'], self.logger)
                lines = [l for l in iostats.splitlines() if len(l) > 0]
                legend = [l for l in lines if "us" in l]
                if len(legend) == 1:
                    headers = legend[0].split()
                    data = lines[-1].split()
                    cpu_user = get_value(headers, data, "us")
                    cpu_nice = get_value(headers, data, "ni")
                    cpu_sys = get_value(headers, data, "sy")
                    cpu_intr = get_value(headers, data, "in")
                    cpu_wait = 0
                    cpu_idle = get_value(headers, data, "id")
                    cpu_stol = 0
                    return format_results(cpu_user + cpu_nice, cpu_sys + cpu_intr, cpu_wait, cpu_idle, cpu_stol)

                else:
                    self.logger.warn("Expected to get at least 4 lines of data from iostat instead of just " + str(iostats[:max(80, len(iostats))]))
                    return False

            elif sys.platform == 'sunos5':
                # mpstat -aq 1 2
                # SET minf mjf xcal  intr ithr  csw icsw migr smtx  srw syscl  usr sys  wt idl sze
                # 0 5239   0 12857 22969 5523 14628   73  546 4055    1 146856    5   6   0  89  24 <-- since boot
                # 1 ...
                # SET minf mjf xcal  intr ithr  csw icsw migr smtx  srw syscl  usr sys  wt idl sze
                # 0 20374   0 45634 57792 5786 26767   80  876 20036    2 724475   13  13   0  75  24 <-- past 1s
                # 1 ...
                # http://docs.oracle.com/cd/E23824_01/html/821-1462/mpstat-1m.html
                #
                # Will aggregate over all processor sets
                    output, _, _ = get_subprocess_output(['mpstat', '-aq', '1', '2'], self.logger)
                    mpstat = output.splitlines()
                    lines = [l for l in mpstat if len(l) > 0]
                    # discard the first len(lines)/2 lines
                    lines = lines[len(lines)/2:]
                    legend = [l for l in lines if "SET" in l]
                    assert len(legend) == 1
                    if len(legend) == 1:
                        headers = legend[0].split()
                        # collect stats for each processor set
                        # and aggregate them based on the relative set size
                        d_lines = [l for l in lines if "SET" not in l]
                        user = [get_value(headers, l.split(), "usr") for l in d_lines]
                        kern = [get_value(headers, l.split(), "sys") for l in d_lines]
                        wait = [get_value(headers, l.split(), "wt") for l in d_lines]
                        idle = [get_value(headers, l.split(), "idl") for l in d_lines]
                        size = [get_value(headers, l.split(), "sze") for l in d_lines]
                        count = sum(size)
                        rel_size = [s/count for s in size]
                        dot = lambda v1, v2: reduce(operator.add, map(operator.mul, v1, v2))
                        return format_results(dot(user, rel_size),
                                              dot(kern, rel_size),
                                              dot(wait, rel_size),
                                              dot(idle, rel_size),
                                              0.0)
            else:
                self.logger.warn("CPUStats: unsupported platform")
                return False
        except Exception:
            self.logger.exception("Cannot compute CPU stats")
            return False


class System(Check):
    def check(self, agentConfig):
        return {"system.uptime": uptime.uptime()}


def main():
    # 1s loop with results
    import logging

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s %(message)s')
    log = logging.getLogger()
    cpu = Cpu(log)
    io = IO(log)
    load = Load(log)
    mem = Memory(log)
    # proc = Processes(log)
    system = System(log)

    config = {"api_key": "666", "device_blacklist_re": re.compile('.*disk0.*')}
    while True:
        print("=" * 10)
        print("--- IO ---")
        print(io.check(config))
        print("--- CPU ---")
        print(cpu.check(config))
        print("--- Load ---")
        print(load.check(config))
        print("--- Memory ---")
        print(mem.check(config))
        print("--- System ---")
        print(system.check(config))
        print("\n\n\n")
        # print("--- Processes ---")
        # print(proc.check(config))
        time.sleep(1)


if __name__ == '__main__':
    main()
