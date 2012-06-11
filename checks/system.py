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


class IO(object):
    def _parse_linux2_iostat_output(self, iostat_output):
        headerRegexp = re.compile(r'([%\\/\-_a-zA-Z0-9]+)[\s+]?')
        itemRegexp = re.compile(r'^([a-zA-Z0-9\/]+)')
        valueRegexp = re.compile(r'\d+\.\d+')

        recentStats = iostat_output.split('Device:')[2].split('\n')
        header = recentStats[0]
        headerNames = re.findall(headerRegexp, header)
        device = None

        ioStats = {}

        for statsIndex in range(1, len(recentStats)):
            row = recentStats[statsIndex]

            if not row:
                # Ignore blank lines.
                continue

            deviceMatch = re.match(itemRegexp, row)

            if deviceMatch is not None:
                # Sometimes device names span two lines.
                device = deviceMatch.groups()[0]

            values = re.findall(valueRegexp, row)

            if not values:
                # Sometimes values are on the next line so we encounter
                # instances of [].
                continue

            ioStats[device] = {}

            for headerIndex in range(0, len(headerNames)):
                headerName = headerNames[headerIndex]
                ioStats[device][headerName] = values[headerIndex]

        return ioStats

    def check(self, logger, agentConfig):
        logger.debug('getIOStats: start')
        
        ioStats = {}
    
        if sys.platform == 'linux2':
            logger.debug('getIOStats: linux2')
            
            try:
                stdout = subprocess.Popen(['iostat', '-d', '1', '2', '-x', '-k'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
                ioStats.update(self._parse_linux2_iostat_output(stdout))
                    
            except:
                logger.exception('getIOStats')
                return False
        else:
            logger.debug('getIOStats: unsupported platform')
            return False
            
        logger.debug('getIOStats: completed, returning')
        return ioStats


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
                self.logger.exception('getLoadAvrgs')
                return False
            
            uptime = uptime[0] # readlines() provides a list but we want a string
        
        elif sys.platform == 'darwin':
            # Get output from uptime
            try:
                uptime = subprocess.Popen(['uptime'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            except:
                self.logger.exception('getLoadAvrgs')
                return False
                
        # Split out the 3 load average values
        loadAvrgs = [res.replace(',', '.') for res in re.findall(r'([0-9]+[\.,]\d+)', uptime)]
        return {'1': loadAvrgs[0], '5': loadAvrgs[1], '15': loadAvrgs[2]}  

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
            except:
                self.logger.exception('Cannot compute stats from /proc/meminfo')
            
            # Swap
            # FIXME units are in MB, we should use bytes instead
            try:
                memData['swapTotal'] = int(meminfo.get('SwapTotal', 0)) / 1024
                memData['swapFree']  = int(meminfo.get('SwapFree', 0)) / 1024

                memData['swapUsed'] =  memData['swapTotal'] - memData['swapFree']
            except:
                self.logger.exception('Cannot compute swap stats')
            
            return memData  
            
        elif sys.platform == 'darwin':
            try:
                top = subprocess.Popen(['top', '-l 1'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
                sysctl = subprocess.Popen(['sysctl', 'vm.swapusage'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            except:
                self.logger.exception('getMemoryUsage')
                return False
            
            # Deal with top
            lines = top.split('\n')
            physParts = re.findall(r'([0-9]\d+)', lines[self.topIndex])
            
            # Deal with sysctl
            swapParts = re.findall(r'([0-9]+\.\d+)', sysctl)
            
            return {'physUsed' : physParts[3], 'physFree' : physParts[4], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2]}
        else:
            return False
    
class Network(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

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
                self.logger.exception('getNetworkTraffic')
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
            if interval == 0:
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
            
        elif sys.platform == "darwin":
            try:
                netstat = subprocess.Popen(["netstat", "-i", "-b"],
                                           stdout=subprocess.PIPE,
                                           close_fds=True)
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
                out, err = netstat.communicate()
                lines = out.split("\n")
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
                self.logger.exception('getNetworkTraffic')
                return False
        
        else:
            self.logger.debug("getNetworkTraffic: unsupported platform")
            return False    

class Processes(object):
    def check(self, logger, agentConfig):
        logger.debug('getProcesses: start')
        
        # Memory logging (case 27152)
        if agentConfig['debugMode'] and sys.platform == 'linux2':
            mem = subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            logger.debug('getProcesses: memory before Popen - ' + str(mem))
        
        # Get output from ps
        try:
            logger.debug('getProcesses: attempting Popen')
            
            ps = subprocess.Popen(['ps', 'auxww'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            
        except:
            logger.exception('getProcesses')
            return False
        
        logger.debug('getProcesses: Popen success, parsing')
        
        # Memory logging (case 27152)
        if agentConfig['debugMode'] and sys.platform == 'linux2':
            mem = subprocess.Popen(['free', '-m'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            logger.debug('getProcesses: memory after Popen - ' + str(mem))
        
        # Split out each process
        processLines = ps.split('\n')
        
        del processLines[0] # Removes the headers
        processLines.pop() # Removes a trailing empty line
        
        processes = []
        
        logger.debug('getProcesses: Popen success, parsing, looping')
        
        for line in processLines:
            line = line.split(None, 10)
            processes.append(map(lambda s: s.strip(), line))
        
        logger.debug('getProcesses: completed, returning')
        
        return { 'processes':   processes,
                 'apiKey':      agentConfig['apiKey'],
                 'host':        gethostname(agentConfig) }
            
class Cpu(object):
    def check(self, logger, agentConfig):
        """Return an aggregate of CPU stats across all CPUs
        When figures are not available, False is sent back.
        """
        logger.debug('getCPUStats: start')
        def format_results(us, sy, wa, idle, st):
            return { 'cpuUser': us, 'cpuSystem': sy, 'cpuWait': wa, 'cpuIdle': idle, 'cpuStolen': st }
                    
        def get_value(legend, data, name):
            "Using the legend and a metric name, get the value or None from the data line"
            if name in legend:
                return float(data[legend.index(name)])
            else:
                # FIXME return a float or False, would trigger type error if not python
                logger.debug("Cannot extract cpu value %s from %s (%s)" % (name, data, legend))
                return 0

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
                logger.warn("Expected to get at least 4 lines of data from iostat instead of just " + str(iostats[:max(80, len(iostats))]))
                return False
        else:
            logger.warn("CPUStats: unsupported platform")
            return False
