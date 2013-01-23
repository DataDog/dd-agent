import operator
import platform
import re
import socket
import string
import subprocess
import sys
import time
from checks import Check, gethostname, UnknownValue

class Disk(Check):

    def __init__(self, logger):
        Check.__init__(self, logger)

    def _parse_df(self, lines, inodes = False, use_mount=False):
        """Multi-platform df output parser
        
        If use_volume is true the volume rather than the mount point is used
        to anchor the metric. If false the mount point is used.

        e.g. /dev/sda1 .... /my_mount
        _parse_df picks /dev/sda1 if use_volume, /my_mount if not

        If inodes is True, count inodes instead
        """

        # Simple list-oriented processing
        # No exec-time optimal but simpler code
        # 1. filter out the header line (once)
        # 2. ditch fake volumes (dev fs, etc.) starting with a none volume
        #    when the volume is too long it sits on a line by itself so collate back
        # 3. if we want to use the mount point, replace the volume name on each line
        # 4. extract interesting metrics

        usageData = []

        # 1.
        lines = map(string.strip, lines.split("\n"))[1:]

        numbers = re.compile(r'([0-9]+)')
        previous = None
        
        for line in lines:
            parts = line.split()

            # skip empty lines
            if len(parts) == 0: continue

            try:

                # 2.
                if len(parts) == 1:
                    # volume on a line by itself
                    previous = parts[0]
                    continue
                elif parts[0] == "none":
                    # this is a "fake" volume
                    continue
                elif not numbers.match(parts[1]):
                    # this is a volume like "map auto_home"
                    continue
                else:
                    if previous and numbers.match(parts[0]):
                        # collate with previous line
                        parts.insert(0, previous)
                        previous = None
                # 3.
                if use_mount:
                    parts[0] = parts[-1]
            
                # 4.
                if inodes:
                    if sys.platform == "darwin":
                        # Filesystem 512-blocks Used Available Capacity iused ifree %iused  Mounted
                        # Inodes are in position 5, 6 and we need to compute the total
                        # Total
                        parts[1] = int(parts[5]) + int(parts[6])
                        # Used
                        parts[2] = int(parts[5])
                        # Available
                        parts[3] = int(parts[6])
                    elif sys.platform.startswith("freebsd"):
                        # Filesystem 1K-blocks Used Avail Capacity iused ifree %iused Mounted
                        # Inodes are in position 5, 6 and we need to compute the total
                        # Total
                        parts[1] = int(parts[5]) + int(parts[6])
                        # Used
                        parts[2] = int(parts[5])
                        # Available
                        parts[3] = int(parts[6])
                    else:
                        # Total
                        parts[1] = int(parts[1])
                        # Used
                        parts[2] = int(parts[2])
                        # Available
                        parts[3] = int(parts[3])
                else:
                    # Total
                    parts[1] = int(parts[1])
                    # Used
                    parts[2] = int(parts[2])
                    # Available
                    parts[3] = int(parts[3])
            except IndexError:
                self.logger.exception("Cannot parse %s" % (parts,))

            usageData.append(parts)
        return usageData
    
    def check(self, agentConfig):
        """Get disk space/inode stats"""

        # Check test_system for some examples of output
        try:
            df = subprocess.Popen(['df', '-k'],
                                  stdout=subprocess.PIPE,
                                  close_fds=True)

            use_mount = agentConfig.get("use_mount", False)
            disks =  self._parse_df(df.stdout.read(), use_mount=use_mount)

            df = subprocess.Popen(['df', '-i'],
                                  stdout=subprocess.PIPE,
                                  close_fds=True)
            inodes = self._parse_df(df.stdout.read(), inodes=True, use_mount=use_mount)
            return (disks, inodes)
        except:
            self.logger.exception('getDiskUsage')
            return False


class IO(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.header_re = re.compile(r'([%\\/\-_a-zA-Z0-9]+)[\s+]?')
        self.item_re   = re.compile(r'^([a-zA-Z0-9\/]+)')
        self.value_re  = re.compile(r'\d+\.\d+')

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

    def xlate(self, metric_name):
        """Standardize on linux metric names"""
        names = {
            "wait": "await",
            "svc_t": "svctm",
            "%b": "%util",
            "kr/s": "rkB/s",
            "kw/s": "wkB/s",
            "actv": "avgqu-sz",
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
            if sys.platform == 'linux2':
                stdout = subprocess.Popen(['iostat', '-d', '1', '2', '-x', '-k'],
                                          stdout=subprocess.PIPE,
                                          close_fds=True).communicate()[0]

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
                iostat = subprocess.Popen(["iostat", "-x", "-d", "1", "2"],
                                          stdout=subprocess.PIPE,
                                          close_fds=True).communicate()[0]

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
                lines = [l for l in iostat.split("\n") if len(l) > 0]
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
                        io[cols[0]][self.xlate(headers[i])] = cols[i]
            else:
                return False
            return io
        except:
            self.logger.exception("Cannot extract IO statistics")
            return False

class Load(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
    
    def check(self, agentConfig):
        if sys.platform == 'linux2':
            try:
                loadAvrgProc = open('/proc/loadavg', 'r')
                uptime = loadAvrgProc.readlines()
                loadAvrgProc.close()
            except:
                self.logger.exception('Cannot extract load')
                return False
            
            uptime = uptime[0] # readlines() provides a list but we want a string
        
        elif sys.platform in ('darwin', 'sunos5') or sys.platform.startswith("freebsd"):
            # Get output from uptime
            try:
                uptime = subprocess.Popen(['uptime'],
                                          stdout=subprocess.PIPE,
                                          close_fds=True).communicate()[0]
            except:
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
        except:
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
                pgsz = subprocess.Popen(['pagesize'],
                                        stdout=subprocess.PIPE,
                                        close_fds=True).communicate()[0]
                self.pagesize = int(pgsz.strip())
            except:
                # No page size available
                pass
    
    def check(self, agentConfig):
        if sys.platform == 'linux2':
            try:
                meminfoProc = open('/proc/meminfo', 'r')
                lines = meminfoProc.readlines()
                meminfoProc.close()
            except:
                self.logger.exception('Cannot get memory metrics from /proc/meminfo')
                return False
            
            # $ cat /proc/meminfo
            # MemTotal:        7995360 kB
            # MemFree:         1045120 kB
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
            
            regexp = re.compile(r'^(\w+):\s+([0-9]+)') # We run this several times so one-time compile now
            meminfo = {}

            for line in lines:
                try:
                    match = re.search(regexp, line)
                    if match is not None:
                        meminfo[match.group(1)] = match.group(2)
                except:
                    self.logger.exception("Cannot parse /proc/meminfo")
                    
            memData = {}
            
            # Physical memory
            # FIXME units are in MB, we should use bytes instead
            try:
                memData['physTotal'] = int(meminfo.get('MemTotal', 0)) / 1024
                memData['physFree'] = int(meminfo.get('MemFree', 0)) / 1024
                memData['physBuffers'] = int(meminfo.get('Buffers', 0)) / 1024
                memData['physCached'] = int(meminfo.get('Cached', 0)) / 1024
                memData['physShared'] = int(meminfo.get('Shmem', 0)) / 1024

                memData['physUsed'] = memData['physTotal'] - memData['physFree']
                # Usable is relative since cached and buffers are actually used to speed things up.
                memData['physUsable'] = memData['physFree'] + memData['physBuffers'] + memData['physCached']
                # Make PctUsable an integer value for precision
                memData['physPctUsable'] = float(memData['physUsable']) / float(memData['physTotal'])
            except:
                self.logger.exception('Cannot compute stats from /proc/meminfo')
            
            # Swap
            # FIXME units are in MB, we should use bytes instead
            try:
                memData['swapTotal'] = int(meminfo.get('SwapTotal', 0)) / 1024
                memData['swapFree']  = int(meminfo.get('SwapFree', 0)) / 1024

                memData['swapUsed'] =  memData['swapTotal'] - memData['swapFree']
                # Make PctFree an integer value for precision
                memData['swapPctFree'] = float(memData['swapFree']) / float(memData['swapTotal'])
            except:
                self.logger.exception('Cannot compute swap stats')
            
            return memData  
            
        elif sys.platform == 'darwin':
            try:
                top = subprocess.Popen(['top', '-l 1'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
                sysctl = subprocess.Popen(['sysctl', 'vm.swapusage'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            except StandardError:
                self.logger.exception('getMemoryUsage')
                return False
            
            # Deal with top
            lines = top.split('\n')
            physParts = re.findall(r'([0-9]\d+)', lines[self.topIndex])
            
            # Deal with sysctl
            swapParts = re.findall(r'([0-9]+\.\d+)', sysctl)
            
            return {'physUsed' : physParts[3], 'physFree' : physParts[4], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2]}
            
        elif sys.platform.startswith("freebsd"):
            try:
                sysctl = subprocess.Popen(['sysctl', 'vm.stats.vm'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            except:
                self.logger.exception('getMemoryUsage')
                return False

            lines = sysctl.split('\n')

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

            for line in lines:
                try:
                    match = re.search(regexp, line)
                    if match is not None:
                        meminfo[match.group(1)] = match.group(2)
                except:
                    self.logger.exception("Cannot parse sysctl vm.stats.vm output")

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
                # Make PctUsable an integer value for precision
                memData['physPctUsable'] = float(memData['physUsable']) / float(memData['physTotal'])
            except:
                self.logger.exception('Cannot compute stats from /proc/meminfo')
            
            return memData;
        elif sys.platform == 'sunos5':
            try:
                memData = {}
                kmem = subprocess.Popen(["kstat", "-c", "zone_memory_cap", "-p"],
                                        stdout=subprocess.PIPE,
                                        close_fds=True).communicate()[0]

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
                kv = [l.strip().split() for l in kmem.split("\n") if len(l) > 0]
                entries = dict([(k.split(":")[-1], v) for (k, v) in kv])
                # extract rss, physcap, swap, swapcap, turn into MB
                convert = lambda v: int(long(v))/2**20
                memData["physTotal"] = convert(entries["physcap"])
                memData["physUsed"]  = convert(entries["rss"])
                memData["physFree"]  = memData["physTotal"] - memData["physUsed"]
                memData["swapTotal"] = convert(entries["swapcap"])
                memData["swapUsed"]  = convert(entries["swap"])
                memData["swapFree"]  = memData["swapTotal"] - memData["swapUsed"]
                # Make PctFree an integer value for precision
                memData['swapPctFree'] = float(memData['swapFree']) / float(memData['swapTotal'])
                return memData
            except:
                self.logger.exception("Cannot compute mem stats from kstat -c zone_memory_cap")
                return False
        else:
            return False
    
class Network(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.solaris_re = re.compile("([ro]bytes64)|errors|collisions")

        # FIXME rework linux support to use the built-in Check logic
        self.networkTrafficStore = {}
        self.networkTrafficStore["last_ts"] = time.time()
        self.networkTrafficStore["current_ts"] = self.networkTrafficStore["last_ts"]

    def _parse_value(self, v):
        if v == "-":
            return 0
        else:
            try:
                return long(v)
            except ValueError:
                return 0

    def check(self, agentConfig):
        """Report network traffic in bytes by interface

        @rtype dict
        @return {"en0": {"recv_bytes": 123, "trans_bytes": 234}, ...}
        """
        # FIXME rework linux support to use the built-in Check logic
        if sys.platform == 'linux2':
            try:
                proc = open('/proc/net/dev', 'r')
                lines = proc.readlines()
                self.networkTrafficStore["current_ts"] = time.time()
                
            except:
                self.logger.exception("Cannot extract network statistics")
                return False
            
            proc.close()
            
            columnLine = lines[1]
            _, receiveCols , transmitCols = columnLine.split('|')
            receiveCols = map(lambda a:'recv_' + a, receiveCols.split())
            transmitCols = map(lambda a:'trans_' + a, transmitCols.split())
            
            cols = receiveCols + transmitCols
            
            faces = {}
            for line in lines[2:]:
                if line.find(':') < 0: continue
                face, data = line.split(':')
                faceData = dict(zip(cols, data.split()))
                faces[face] = faceData
            
            interfaces = {}
            
            interval = self.networkTrafficStore["current_ts"] - self.networkTrafficStore["last_ts"]
            self.logger.debug('getNetworkTraffic: interval (s) %s' % interval)
            if interval <= 0.001:
                self.logger.warn('0-sample interval, skipping network checks')
                return False
            self.networkTrafficStore["last_ts"] = self.networkTrafficStore["current_ts"]

            # Now loop through each interface
            for face in faces:
                key = face.strip()
                
                # We need to work out the traffic since the last check so first time we store the current value
                # then the next time we can calculate the difference
                if key in self.networkTrafficStore:
                    interfaces[key] = {}
                    interfaces[key]['recv_bytes'] = (long(faces[face]['recv_bytes']) - long(self.networkTrafficStore[key]['recv_bytes']))/interval
                    interfaces[key]['trans_bytes'] = (long(faces[face]['trans_bytes']) - long(self.networkTrafficStore[key]['trans_bytes']))/interval
                    
                    interfaces[key]['recv_bytes'] = str(interfaces[key]['recv_bytes'])
                    interfaces[key]['trans_bytes'] = str(interfaces[key]['trans_bytes'])
                    
                    # And update the stored value to subtract next time round
                    self.networkTrafficStore[key]['recv_bytes'] = faces[face]['recv_bytes']
                    self.networkTrafficStore[key]['trans_bytes'] = faces[face]['trans_bytes']
                    
                else:
                    self.networkTrafficStore[key] = {}
                    self.networkTrafficStore[key]['recv_bytes'] = faces[face]['recv_bytes']
                    self.networkTrafficStore[key]['trans_bytes'] = faces[face]['trans_bytes']
        
            return interfaces
            
        elif sys.platform == "darwin" or sys.platform.startswith("freebsd"):
            try:
                netstat = subprocess.Popen(["netstat", "-i", "-b"],
                                           stdout=subprocess.PIPE,
                                           close_fds=True).communicate()[0]
                # Name  Mtu   Network       Address            Ipkts Ierrs     Ibytes    Opkts Oerrs     Obytes  Coll
                # lo0   16384 <Link#1>                        318258     0  428252203   318258     0  428252203     0
                # lo0   16384 localhost   fe80:1::1           318258     -  428252203   318258     -  428252203     -
                # lo0   16384 127           localhost         318258     -  428252203   318258     -  428252203     -
                # lo0   16384 localhost   ::1                 318258     -  428252203   318258     -  428252203     -
                # gif0* 1280  <Link#2>                             0     0          0        0     0          0     0
                # stf0* 1280  <Link#3>                             0     0          0        0     0          0     0
                # en0   1500  <Link#4>    04:0c:ce:db:4e:fa 20801309     0 13835457425 15149389     0 11508790198     0
                # en0   1500  seneca.loca fe80:4::60c:ceff: 20801309     - 13835457425 15149389     - 11508790198     -
                # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
                # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
                # en0   1500  192.168.1     192.168.1.63    20801309     - 13835457425 15149389     - 11508790198     -
                # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
                # p2p0  2304  <Link#5>    06:0c:ce:db:4e:fa        0     0          0        0     0          0     0
                # ham0  1404  <Link#6>    7a:79:05:4d:bf:f5    30100     0    6815204    18742     0    8494811     0
                # ham0  1404  5             5.77.191.245       30100     -    6815204    18742     -    8494811     -
                # ham0  1404  seneca.loca fe80:6::7879:5ff:    30100     -    6815204    18742     -    8494811     -
                # ham0  1404  2620:9b::54 2620:9b::54d:bff5    30100     -    6815204    18742     -    8494811     -

                lines = netstat.split("\n")
                headers = lines[0].split()

                # Given the irregular structure of the table above, better to parse from the end of each line
                # Verify headers first
                #          -7       -6       -5        -4       -3       -2        -1
                for h in ("Ipkts", "Ierrs", "Ibytes", "Opkts", "Oerrs", "Obytes", "Coll"):
                    if h not in headers:
                        self.logger.error("%s not found in %s; cannot parse" % (h, headers))
                        return False
                    
                current = None
                for l in lines[1:]:
                    # Another header row, abort now, this is IPv6 land
                    if "Name" in l:
                        break

                    x = l.split()
                    if len(x) == 0:
                        break

                    iface = x[0]
                    if iface.endswith("*"):
                        iface = iface[:-1]
                    if iface == current:
                        # skip multiple lines of same interface
                        continue
                    else:
                        current = iface

                    if not self.is_counter("%s.recv_bytes" % iface):
                        self.counter("%s.recv_bytes" % iface)
                    value = self._parse_value(x[-5])
                    self.save_sample("%s.recv_bytes" % iface, value)

                    if not self.is_counter("%s.trans_bytes" % iface):
                        self.counter("%s.trans_bytes" % iface)
                    value = self._parse_value(x[-2])
                    self.save_sample("%s.trans_bytes" % iface, value)
                
                # now make a dictionary {"iface": {"recv_bytes": value, "trans_bytes": value}}
                interfaces = {}
                for m in self.get_metric_names():
                    # m should be a counter
                    if not self.is_counter(m):
                        continue
                    # metric name iface.recv|trans_bytes
                    i, n = m.split(".")
                    try:
                        sample  = self.get_sample(m)
                        # will raise if no value, thus skipping what's next
                        if interfaces.get(i) is None:
                            interfaces[i] = {}
                        interfaces[i][n] = sample
                    except UnknownValue:
                        pass
                if len(interfaces) > 0:
                    return interfaces
                else:
                    return False
            except:
                self.logger.exception("Cannot gather network stats")
                return False

        elif sys.platform == "sunos5":
            # Can't get bytes sent and received via netstat
            # Default to kstat -p link:0:
            netstat = subprocess.Popen(["kstat", "-p", "link:0:"],
                                       stdout=subprocess.PIPE,
                                       close_fds=True).communicate()[0]
            # link:0:net0:brdcstrcv   527336
            # link:0:net0:brdcstxmt   1595
            # link:0:net0:class       net
            # link:0:net0:collisions  0
            # link:0:net0:crtime      16359935.2637943
            # link:0:net0:ierrors     0
            # link:0:net0:ifspeed     10000000000
            # link:0:net0:ipackets    682834
            # link:0:net0:ipackets64  682834
            # link:0:net0:link_duplex 0
            # link:0:net0:link_state  1
            # link:0:net0:multircv    0
            # link:0:net0:multixmt    1595
            # link:0:net0:norcvbuf    0
            # link:0:net0:noxmtbuf    0
            # link:0:net0:obytes      12820668
            # link:0:net0:obytes64    12820668
            # link:0:net0:oerrors     0
            # link:0:net0:opackets    105445
            # link:0:net0:opackets64  105445
            # link:0:net0:rbytes      113983614
            # link:0:net0:rbytes64    113983614
            # link:0:net0:snaptime    16834735.1607669
            # link:0:net0:unknowns    0
            # link:0:net0:zonename    53aa9b7e-48ba-4152-a52b-a6368c3d9e7c
            # link:0:net1:brdcstrcv   4947620
            # link:0:net1:brdcstxmt   1594
            # link:0:net1:class       net
            # link:0:net1:collisions  0
            # link:0:net1:crtime      16359935.2839167
            # link:0:net1:ierrors     0
            # link:0:net1:ifspeed     10000000000
            # link:0:net1:ipackets    4947620
            # link:0:net1:ipackets64  4947620
            # link:0:net1:link_duplex 0
            # link:0:net1:link_state  1
            # link:0:net1:multircv    0
            # link:0:net1:multixmt    1594
            # link:0:net1:norcvbuf    0
            # link:0:net1:noxmtbuf    0
            # link:0:net1:obytes      73324
            # link:0:net1:obytes64    73324
            # link:0:net1:oerrors     0
            # link:0:net1:opackets    1594
            # link:0:net1:opackets64  1594
            # link:0:net1:rbytes      304384894
            # link:0:net1:rbytes64    304384894
            # link:0:net1:snaptime    16834735.1613302
            # link:0:net1:unknowns    0
            # link:0:net1:zonename    53aa9b7e-48ba-4152-a52b-a6368c3d9e7c

            lines = [l for l in netstat.split("\n") if len(l) > 0]
            for l in lines:
                k, v = l.split()
                # only pick certain counters 
                if self.solaris_re.search(k) is not None:
                    if not self.is_counter(k):
                        self.counter(k)
                    self.save_sample(k, long(v))

            # now turn that into {iface: {recv_bytes: xxx, trans_bytes: yyy}, ...}
            interfaces = {}
            for m in self.get_metric_names():
                if not self.is_counter(m):
                    continue
                try:
                    sample = self.get_sample(m)
                    
                    link, n, i, name = m.split(":")
                    assert link == "link"

                    # translate metric names
                    if name == "rbytes64": name = "recv_bytes"
                    elif name == "obytes64": name = "trans_bytes"

                    # populate result dictionary
                    if interfaces.get(i) is None:
                        interfaces[i] = {}
                    interfaces[i][name] = sample
                except UnknownValue:
                    pass
            return interfaces
        else:
            return False    

class Processes(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

    def check(self, agentConfig):
        # Get output from ps
        try:
            ps = subprocess.Popen(['ps', 'auxww'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
        except StandardError:
            self.logger.exception('getProcesses')
            return False
        
        # Split out each process
        processLines = ps.split('\n')
        
        del processLines[0] # Removes the headers
        processLines.pop() # Removes a trailing empty line
        
        processes = []
        
        for line in processLines:
            line = line.split(None, 10)
            processes.append(map(lambda s: s.strip(), line))
        
        return { 'processes':   processes,
                 'apiKey':      agentConfig['api_key'],
                 'host':        gethostname(agentConfig) }
            
class Cpu(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

    def check(self, agentConfig):
        """Return an aggregate of CPU stats across all CPUs
        When figures are not available, False is sent back.
        """
        def format_results(us, sy, wa, idle, st):
            return { 'cpuUser': us, 'cpuSystem': sy, 'cpuWait': wa, 'cpuIdle': idle, 'cpuStolen': st }
                    
        def get_value(legend, data, name):
            "Using the legend and a metric name, get the value or None from the data line"
            if name in legend:
                return float(data[legend.index(name)])
            else:
                # FIXME return a float or False, would trigger type error if not python
                self.logger.debug("Cannot extract cpu value %s from %s (%s)" % (name, data, legend))
                return 0.0

        if sys.platform == 'linux2':
            mpstat = subprocess.Popen(['mpstat', '1', '3'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            # topdog@ip:~$ mpstat 1 3
            # Linux 2.6.32-341-ec2 (ip) 	01/19/2012 	_x86_64_	(2 CPU)
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
            lines = mpstat.split("\n")
            legend = [l for l in lines if "%usr" in l or "%user" in l]
            avg =    [l for l in lines if "Average" in l]
            if len(legend) == 1 and len(avg) == 1:
                headers = [h for h in legend[0].split() if h not in ("AM", "PM")]
                data    = avg[0].split()

                # Userland
                # Debian lenny says %user so we look for both 
                # One of them will be 0
                cpu_usr = get_value(headers, data, "%usr")
                cpu_usr2 = get_value(headers, data, "%user")
                cpu_nice = get_value(headers, data, "%nice")
                # I/O
                cpu_wait = get_value(headers, data, "%iowait")
                # Idling
                cpu_idle = get_value(headers, data, "%idle")
                # Kernel + Interrupts, soft and hard
                cpu_sys = get_value(headers, data, "%sys")
                cpu_hirq = get_value(headers, data, "%irq")
                cpu_sirq = get_value(headers, data, "%soft")
                # VM-related
                cpu_st = get_value(headers, data, "%steal")
                cpu_guest = get_value(headers, data, "%guest")

                # (cpu_user & cpu_usr) == 0
                return format_results(cpu_usr + cpu_usr2 + cpu_nice,
                                      cpu_sys + cpu_hirq + cpu_sirq,
                                      cpu_wait, cpu_idle,
                                      cpu_st)
            else:
                return False
            
        elif sys.platform == 'darwin':
            # generate 3 seconds of data
            # ['          disk0           disk1       cpu     load average', '    KB/t tps  MB/s     KB/t tps  MB/s  us sy id   1m   5m   15m', '   21.23  13  0.27    17.85   7  0.13  14  7 79  1.04 1.27 1.31', '    4.00   3  0.01     5.00   8  0.04  12 10 78  1.04 1.27 1.31', '']   
            iostats = subprocess.Popen(['iostat', '-C', '-w', '3', '-c', '2'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            lines = [l for l in iostats.split("\n") if len(l) > 0]
            legend = [l for l in lines if "us" in l]
            if len(legend) == 1:
                headers = legend[0].split()
                data = lines[-1].split()
                cpu_user = get_value(headers, data, "us")
                cpu_sys  = get_value(headers, data, "sy")
                cpu_wait = 0
                cpu_idle = get_value(headers, data, "id")
                cpu_st   = 0
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
            iostats = subprocess.Popen(['iostat', '-w', '3', '-c', '2'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            lines = [l for l in iostats.split("\n") if len(l) > 0]
            legend = [l for l in lines if "us" in l]
            if len(legend) == 1:
                headers = legend[0].split()
                data = lines[-1].split()
                cpu_user = get_value(headers, data, "us")
                cpu_nice = get_value(headers, data, "ni")
                cpu_sys  = get_value(headers, data, "sy")
                cpu_intr = get_value(headers, data, "in")
                cpu_wait = 0
                cpu_idle = get_value(headers, data, "id")
                cpu_stol = 0
                return format_results(cpu_user + cpu_nice, cpu_sys + cpu_intr, cpu_wait, cpu_idle, cpu_stol);

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
            try:
                mpstat = subprocess.Popen(['mpstat', '-aq', '1', '2'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
                lines = [l for l in mpstat.split("\n") if len(l) > 0]
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
                    wait = [get_value(headers, l.split(), "wt")  for l in d_lines]
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
            except:
                self.logger.exception("Cannot compute CPU stats")
                return False
        else:
            self.logger.warn("CPUStats: unsupported platform")
            return False

if __name__ == '__main__':
    # 1s loop with results
    import logging
    import time
    import pprint
    
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s %(message)s')
    log = logging.getLogger()
    cpu = Cpu(log)
    disk = Disk(log)
    io = IO(log)
    load = Load(log)
    mem = Memory(log)
    proc = Processes(log)
    net = Network(log)

    config = {"api_key": "666"}
    while True:
        print("--- CPU ---")
        print(cpu.check(config))
        print("--- Load ---")
        print(load.check(config))
        print("--- Memory ---")
        print(mem.check(config))
        print("--- Network ---")
        print(net.check(config))
        print("--- Disk ---")
        print(disk.check(config))
        print("--- IO ---")
        print(io.check(config))
        print("--- Processes ---")
        print(proc.check(config))
        time.sleep(1)
