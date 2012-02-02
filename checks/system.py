import re
import socket
import string
import subprocess
import sys
import time
from checks import gethostname

class Disk(object):

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
                logger.exception("Cannot parse %s" % (parts,))

            usageData.append(parts)
        return usageData
    
    def check(self, logger, agentConfig):
        """Get disk space/inode stats"""

        # Check test_system for some examples of output
        try:
            df = subprocess.Popen(['df', '-k'],
                                  stdout=subprocess.PIPE,
                                  close_fds=True)

            use_mount = "use_mount" in agentConfig
            disks =  self._parse_df(df.stdout.read(), use_mount=use_mount)

            df = subprocess.Popen(['df', '-i'],
                                  stdout=subprocess.PIPE,
                                  close_fds=True)
            inodes = self._parse_df(df.stdout.read(), inodes=True, use_mount=use_mount)
            return (disks, inodes)
        except:
            logger.exception('getDiskUsage')
            return False


class IO(object):
    def check(self, logger, agentConfig):
        logger.debug('getIOStats: start')
        
        ioStats = {}
    
        if sys.platform == 'linux2':
            logger.debug('getIOStats: linux2')
            
            headerRegexp = re.compile(r'([%\\/\-a-zA-Z0-9]+)[\s+]?')
            itemRegexp = re.compile(r'^([a-zA-Z0-9\/]+)')
            valueRegexp = re.compile(r'\d+\.\d+')
            
            try:
                stats = subprocess.Popen(['iostat', '-d', '1', '2', '-x', '-k'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
                recentStats = stats.split('Device:')[2].split('\n')
                header = recentStats[0]
                headerNames = re.findall(headerRegexp, header)
                device = None
                
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
                    
            except:
                logger.exception('getIOStats')
                return False
        else:
            logger.debug('getIOStats: unsupported platform')
            return False
            
        logger.debug('getIOStats: completed, returning')
        return ioStats


class Load(object):
    def __init__(self, linuxProcFsLocation):
        self.linuxProcFsLocation = linuxProcFsLocation
    
    def check(self, logger, agentConfig):
        logger.debug('getLoadAvrgs: start')
        
        # If Linux like procfs system is present and mounted we use loadavg, else we use uptime
        if sys.platform == 'linux2' or (sys.platform.find('freebsd') != -1 and self.linuxProcFsLocation != False):
            
            try:
                logger.debug('getLoadAvrgs: attempting open')
                
                if sys.platform == 'linux2':
                    loadAvrgProc = open('/proc/loadavg', 'r')
                else:
                    loadAvrgProc = open(self.linuxProcFsLocation + '/loadavg', 'r')
                    
                uptime = loadAvrgProc.readlines()
                
            except IOError, e:
                logger.error('getLoadAvrgs: exception = ' + str(e))
                return False
            
            logger.debug('getLoadAvrgs: open success')
                
            loadAvrgProc.close()
            
            uptime = uptime[0] # readlines() provides a list but we want a string
        
        elif sys.platform.find('freebsd') != -1 and self.linuxProcFsLocation == False:
            logger.debug('getLoadAvrgs: freebsd (uptime)')
            
            try:
                logger.debug('getLoadAvrgs: attempting Popen')
                
                uptime = subprocess.Popen(['uptime'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
                
            except:
                logger.exception('getLoadAvrgs')
                return False
                
            logger.debug('getLoadAvrgs: Popen success')
            
        elif sys.platform == 'darwin':
            logger.debug('getLoadAvrgs: darwin')
            
            # Get output from uptime
            try:
                logger.debug('getLoadAvrgs: attempting Popen')
                
                uptime = subprocess.Popen(['uptime'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
                
            except Exception, e:
                logger.exception('getLoadAvrgs')
                return False
                
            logger.debug('getLoadAvrgs: Popen success')
        
        logger.debug('getLoadAvrgs: parsing')
                
        # Split out the 3 load average values
        loadAvrgs = [res.replace(',', '.') for res in re.findall(r'([0-9]+[\.,]\d+)', uptime)]
        loadAvrgs = {'1': loadAvrgs[0], '5': loadAvrgs[1], '15': loadAvrgs[2]}  
    
        logger.debug('getLoadAvrgs: completed, returning')
    
        return loadAvrgs


class Memory(object):
    def __init__(self, linuxProcFsLocation, topIndex):
        self.linuxProcFsLocation = linuxProcFsLocation
        self.topIndex = topIndex
    
    def check(self, logger, agentConfig):
        logger.debug('getMemoryUsage: start')
        
        # If Linux like procfs system is present and mounted we use meminfo, else we use "native" mode (vmstat and swapinfo)
        if sys.platform == 'linux2' or (sys.platform.find('freebsd') != -1 and self.linuxProcFsLocation != False):
            
            if sys.platform == 'linux2':
                logger.debug('getMemoryUsage: linux2')
            else:
                logger.debug('getMemoryUsage: freebsd (meminfo)')
            
            try:
                logger.debug('getMemoryUsage: attempting open')
                
                if sys.platform == 'linux2':
                    meminfoProc = open('/proc/meminfo', 'r')
                else:
                    meminfoProc = open(self.linuxProcFsLocation + '/meminfo', 'r')
                
                lines = meminfoProc.readlines()
                
            except IOError, e:
                logger.error('getMemoryUsage: exception = ' + str(e))
                return False
                
            logger.debug('getMemoryUsage: Popen success, parsing')
            
            meminfoProc.close()
            
            logger.debug('getMemoryUsage: open success, parsing')
            
            regexp = re.compile(r'([0-9]+)') # We run this several times so one-time compile now
            
            meminfo = {}
            
            logger.debug('getMemoryUsage: parsing, looping')
            
            # Loop through and extract the numerical values
            for line in lines:
                values = line.split(':')
                
                try:
                    # Picks out the key (values[0]) and makes a list with the value as the meminfo value (values[1])
                    # We are only interested in the KB data so regexp that out
                    match = re.search(regexp, values[1])
    
                    if match != None:
                        meminfo[str(values[0])] = match.group(0)
                    
                except IndexError:
                    break
                    
            logger.debug('getMemoryUsage: parsing, looped')
            
            memData = {}
            
            # Phys
            try:
                logger.debug('getMemoryUsage: formatting (phys)')
                
                physTotal = int(meminfo['MemTotal'])
                physFree = int(meminfo['MemFree'])
                physUsed = physTotal - physFree
                
                # Convert to MB
                memData['physFree'] = physFree / 1024
                memData['physUsed'] = physUsed / 1024
                memData['cached'] = int(meminfo['Cached']) / 1024
                                
            # Stops the agent crashing if one of the meminfo elements isn't set
            except IndexError:
                logger.debug('getMemoryUsage: formatting (phys) IndexError - Cached, MemTotal or MemFree not present')
                
            except KeyError:
                logger.debug('getMemoryUsage: formatting (phys) KeyError - Cached, MemTotal or MemFree not present')
            
            logger.debug('getMemoryUsage: formatted (phys)')
            
            # Swap
            try:
                logger.debug('getMemoryUsage: formatting (swap)')
                
                swapTotal = int(meminfo['SwapTotal'])
                swapFree = int(meminfo['SwapFree'])
                swapUsed = swapTotal - swapFree
                
                # Convert to MB
                memData['swapFree'] = swapFree / 1024
                memData['swapUsed'] = swapUsed / 1024
                                
            # Stops the agent crashing if one of the meminfo elements isn't set
            except IndexError:
                logger.debug('getMemoryUsage: formatting (swap) IndexErro) - SwapTotal or SwapFree not present')
                
            except KeyError:
                logger.debug('getMemoryUsage: formatting (swap) KeyError - SwapTotal or SwapFree not present')
            
            logger.debug('getMemoryUsage: formatted (swap), completed, returning')
            
            return memData  
            
        elif sys.platform.find('freebsd') != -1 and self.linuxProcFsLocation == False:
            logger.debug('getMemoryUsage: freebsd (native)')
            
            try:
                logger.debug('getMemoryUsage: attempting Popen (sysctl)')
                physTotal = subprocess.Popen(['sysctl', '-n', 'hw.physmem'], stdout = subprocess.PIPE, close_fds = True).communicate()[0]
                
                logger.debug('getMemoryUsage: attempting Popen (vmstat)')
                vmstat = subprocess.Popen(['vmstat', '-H'], stdout = subprocess.PIPE, close_fds = True).communicate()[0]
                
                logger.debug('getMemoryUsage: attempting Popen (swapinfo)')
                swapinfo = subprocess.Popen(['swapinfo', '-k'], stdout = subprocess.PIPE, close_fds = True).communicate()[0]

            except:
                logger.exception('getMemoryUsage')
                
                return False
                
            logger.debug('getMemoryUsage: Popen success, parsing')

            # First we parse the information about the real memory
            lines = vmstat.split('\n')
            physParts = re.findall(r'([0-9]\d+)', lines[2])
    
            physTotal = int(physTotal.strip()) / 1024 # physFree is returned in B, but we need KB so we convert it
            physFree = int(physParts[1])
            physUsed = int(physTotal - physFree)
    
            logger.debug('getMemoryUsage: parsed vmstat')
    
            # And then swap
            lines = swapinfo.split('\n')
            swapParts = re.findall(r'(\d+)', lines[1])
            
            # Convert evrything to MB
            physUsed = int(physUsed) / 1024
            physFree = int(physFree) / 1024
            swapUsed = int(swapParts[3]) / 1024
            swapFree = int(swapParts[4]) / 1024
    
            logger.debug('getMemoryUsage: parsed swapinfo, completed, returning')
    
            return {'physUsed' : physUsed, 'physFree' : physFree, 'swapUsed' : swapUsed, 'swapFree' : swapFree, 'cached' : None}
            
        elif sys.platform == 'darwin':
            logger.debug('getMemoryUsage: darwin')
            
            try:
                logger.debug('getMemoryUsage: attempting Popen (top)')              
                top = subprocess.Popen(['top', '-l 1'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
                
                logger.debug('getMemoryUsage: attempting Popen (sysctl)')
                sysctl = subprocess.Popen(['sysctl', 'vm.swapusage'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
                
            except:
                logger.exception('getMemoryUsage')
                return False
            
            logger.debug('getMemoryUsage: Popen success, parsing')
            
            # Deal with top
            lines = top.split('\n')
            physParts = re.findall(r'([0-9]\d+)', lines[self.topIndex])
            
            logger.debug('getMemoryUsage: parsed top')
            
            # Deal with sysctl
            swapParts = re.findall(r'([0-9]+\.\d+)', sysctl)
            
            logger.debug('getMemoryUsage: parsed sysctl, completed, returning')
            
            return {'physUsed' : physParts[3], 'physFree' : physParts[4], 'swapUsed' : swapParts[1], 'swapFree' : swapParts[2], 'cached' : None}    
            
        else:
            return False
    
class Network(object):
    def __init__(self):
        self.networkTrafficStore = {}
        self.networkTrafficStore["last_ts"] = time.time()
        self.networkTrafficStore["current_ts"] = self.networkTrafficStore["last_ts"]
    
    def check(self, logger, agentConfig):
        logger.debug('getNetworkTraffic: start')
        
        if sys.platform == 'linux2':
            logger.debug('getNetworkTraffic: linux2')
            
            try:
                logger.debug('getNetworkTraffic: attempting open')
                
                proc = open('/proc/net/dev', 'r')
                lines = proc.readlines()
                self.networkTrafficStore["current_ts"] = time.time()
                
            except IOError, e:
                logger.exception('getNetworkTraffic')
                return False
            
            proc.close()
            
            logger.debug('getNetworkTraffic: open success, parsing')
            
            columnLine = lines[1]
            _, receiveCols , transmitCols = columnLine.split('|')
            receiveCols = map(lambda a:'recv_' + a, receiveCols.split())
            transmitCols = map(lambda a:'trans_' + a, transmitCols.split())
            
            cols = receiveCols + transmitCols
            
            logger.debug('getNetworkTraffic: parsing, looping')
            
            faces = {}
            for line in lines[2:]:
                if line.find(':') < 0: continue
                face, data = line.split(':')
                faceData = dict(zip(cols, data.split()))
                faces[face] = faceData
            
            
            interfaces = {}
            
            interval = self.networkTrafficStore["current_ts"] - self.networkTrafficStore["last_ts"]
            logger.debug('getNetworkTraffic: interval (s) %s' % interval)
            if interval == 0:
                logger.warn('0-sample interval, skipping network checks')
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
        
            logger.debug('getNetworkTraffic: completed, returning')
                    
            return interfaces
            
        elif sys.platform.find('freebsd') != -1:
            logger.debug('getNetworkTraffic: freebsd')
            
            try:
                logger.debug('getNetworkTraffic: attempting Popen (netstat)')
                netstat = subprocess.Popen(['netstat', '-nbid', ' grep Link'], stdout=subprocess.PIPE, close_fds=True)
                
                logger.debug('getNetworkTraffic: attempting Popen (grep)')
                grep = subprocess.Popen(['grep', 'Link'], stdin = netstat.stdout, stdout=subprocess.PIPE, close_fds=True).communicate()[0]
                
            except:
                logger.exception('getNetworkTraffic')
                
                return False
            
            logger.debug('getNetworkTraffic: open success, parsing')
            
            lines = grep.split('\n')
            
            # Loop over available data for each inteface
            faces = {}
            for line in lines:
                line = re.split(r'\s+', line)
                length = len(line)
                
                if length == 13:
                    faceData = {'recv_bytes': line[6], 'trans_bytes': line[9], 'drops': line[10], 'errors': long(line[5]) + long(line[8])}
                elif length == 12:
                    faceData = {'recv_bytes': line[5], 'trans_bytes': line[8], 'drops': line[9], 'errors': long(line[4]) + long(line[7])}
                else:
                    # Malformed or not enough data for this interface, so we skip it
                    continue
                
                face = line[0]
                faces[face] = faceData
                
            logger.debug('getNetworkTraffic: parsed, looping')
                
            interfaces = {}
            
            # Now loop through each interface
            for face in faces:
                key = face.strip()
                
                # We need to work out the traffic since the last check so first time we store the current value
                # then the next time we can calculate the difference
                if key in self.networkTrafficStore:
                    interfaces[key] = {}
                    interfaces[key]['recv_bytes'] = long(faces[face]['recv_bytes']) - long(self.networkTrafficStore[key]['recv_bytes'])
                    interfaces[key]['trans_bytes'] = long(faces[face]['trans_bytes']) - long(self.networkTrafficStore[key]['trans_bytes'])
                    
                    interfaces[key]['recv_bytes'] = str(interfaces[key]['recv_bytes'])
                    interfaces[key]['trans_bytes'] = str(interfaces[key]['trans_bytes'])
                    
                    # And update the stored value to subtract next time round
                    self.networkTrafficStore[key]['recv_bytes'] = faces[face]['recv_bytes']
                    self.networkTrafficStore[key]['trans_bytes'] = faces[face]['trans_bytes']
                    
                else:
                    self.networkTrafficStore[key] = {}
                    self.networkTrafficStore[key]['recv_bytes'] = faces[face]['recv_bytes']
                    self.networkTrafficStore[key]['trans_bytes'] = faces[face]['trans_bytes']
        
            logger.debug('getNetworkTraffic: completed, returning')
    
            return interfaces
        
        else:       
            logger.debug('getNetworkTraffic: other platform, returning')
        
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
                logger.warn("Cannot extract cpu value %s from %s (%s)" % (name, data, legend))
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
            lines = mpstat.split("\n")
            legend = [l for l in lines if "%usr" in l]
            avg =    [l for l in lines if "Average" in l]
            if len(legend) == 1 and len(avg) == 1:
                headers = [h for h in legend[0].split() if h not in ("AM", "PM")]
                data    = avg[0].split()

                # Userland
                cpu_user = get_value(headers, data, "%usr")
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

                return format_results(cpu_user + cpu_nice,
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
