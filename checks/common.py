# Core modules
import os
import re
import logging
import platform
import subprocess
import sys
import time
import datetime
import socket

# Needed to identify server uniquely
import uuid
try:
    from hashlib import md5
except ImportError: # Python < 2.5
    from md5 import new as md5

# Konstants
INFINITY = "Inf"
NaN = "NaN"

def recordsize(func):
    def wrapper(*args, **kwargs):
        logger = logging.getLogger("checks")
        res = func(*args, **kwargs)
        logger.debug("SIZE: {0} wrote {1} bytes uncompressed".format(func, len(str(res))))
        return res
    return wrapper

def getOS():
    if sys.platform == 'darwin':
        return 'mac'
    elif sys.platform.find('freebsd') != -1:
        return 'freebsd'
    elif sys.platform.find('linux') != -1:
        return 'linux'
    else:
        return sys.platform

def getTopIndex():
    macV = None
    if sys.platform == 'darwin':
        macV = platform.mac_ver()
        
    # Output from top is slightly modified on OS X 10.6 (case #28239)
    if macV and macV[0].startswith('10.6.'):
        return 6
    else:
        return 5

class Check(object):
    """
    (Abstract) class for all checks with the ability to:
    * compute rates for counters
    """
    def __init__(self):
        # where to store samples, indexed by metric_name
        # metric_name: [(ts, value), (ts, value)]
        self._sample_store = {}
        self._counters = {} # metric_name: bool

    def counter(self, metric_name):
        """
        Treats the metric as a counter, i.e. computes its per second derivative
        """
        self._counters[metric_name] = True

    def is_counter(self, metric_name):
        "Is this metric a counter?"
        return metric_name in self._counters

    def gauge(self, metric_name):
        """
        Treats the metric as a guage, i.e. keep the data as is
        """
        pass

    def is_gauge(self, metric_name):
        return not self.is_counter(metric_name)

    def save_sample(self, metric_name, value, timestamp=None):
        """Save a simple sample"""
        if timestamp is None:
            timestamp = time.time()
        if metric_name not in self._sample_store:
            self._sample_store[metric_name] = []
        self._sample_store[metric_name].append((timestamp, value))

    def save_samples(self, pairs_or_triplets):
        pass
    
    @classmethod
    def _rate(cls, sample1, sample2):
        "Simple rate"
        interval = sample2[0] - sample1[0]
        if interval == 0:
            return INFINITY
        delta = sample2[1] - sample1[1]
        return delta / interval

    def get_sample(self, metric_name):
        if metric_name not in self._sample_store:
            return None
        elif self.is_counter(metric_name) and len(self._sample_store[metric_name]) < 2:
            return None
        elif self.is_counter(metric_name) and len(self._sample_store[metric_name]) >= 2:
            return self._rate(self._sample_store[metric_name][-2], self._sample_store[metric_name][-1])
        elif self.is_gauge(metric_name) and len(self._sample_store[metric_name]) >= 1:
            return self._sample_store[metric_name][-1]
        else:
            return NaN

    def get_samples(self):
        values = []
        for m in self._metric_store:
            values.append(self.get_sample(m))
        return values

class checks:
    def __init__(self, agentConfig, rawConfig, emitter):
        self.checksLogger = logging.getLogger('checks')
        self.agentConfig = agentConfig
        self.rawConfig = rawConfig
        self.plugins = None
        self.emitter = emitter
        self.os = getOS()
        self.topIndex = getTopIndex()
    
        # Set global timeout to 15 seconds for all sockets (case 31033). Should be long enough
        socket.setdefaulttimeout(15)
        
        self.linuxProcFsLocation = self.getMountedLinuxProcFsLocation()
        
        self._apache = Apache()
        self._nginx = Nginx()
        self._disk = Disk()
        self._io = IO()
        self._load = Load(self.linuxProcFsLocation)
        self._memory = Memory(self.linuxProcFsLocation, self.topIndex)
        self._network = Network()
        self._processes = Processes()
        self._cpu = Cpu()
        self._couchdb = CouchDb()
        self._mongodb = MongoDb()
        self._mysql = MySql()
        self._rabbitmq = RabbitMq()
        self._ganglia = Ganglia()
        self._cassandra = Cassandra()

        if agentConfig.get('has_datadog',False):
            self._datadogs = [ddRollupLP()]
        else:
            self._datadogs = None

        self._event_checks = [Hudson(), Nagios(socket.gethostname())]
            
    #
    # Checks
    #
    @recordsize 
    def getApacheStatus(self):
        return self._apache.check(self.checksLogger, self.agentConfig)

    @recordsize 
    def getCouchDBStatus(self):
        return self._couchdb.check(self.checksLogger, self.agentConfig)
    
    @recordsize
    def getDiskUsage(self):
        return self._disk.check(self.checksLogger, self.agentConfig)

    @recordsize
    def getIOStats(self):
        return self._io.check(self.checksLogger, self.agentConfig)
            
    @recordsize
    def getLoadAvrgs(self):
        return self._load.check(self.checksLogger, self.agentConfig)

    @recordsize 
    def getMemoryUsage(self):
        return self._memory.check(self.checksLogger, self.agentConfig)
        
    @recordsize     
    def getMongoDBStatus(self):
        return self._mongodb.check(self.checksLogger, self.agentConfig)

    @recordsize
    def getMySQLStatus(self):
        return self._mysql.check(self.checksLogger, self.agentConfig)
        
    @recordsize
    def getNetworkTraffic(self):
        return self._network.check(self.checksLogger, self.agentConfig)
    
    @recordsize
    def getNginxStatus(self):
        return self._nginx.check(self.checksLogger, self.agentConfig)
        
    @recordsize
    def getProcesses(self):
        return self._processes.check(self.checksLogger, self.agentConfig)
        
    @recordsize
    def getRabbitMQStatus(self):
        return self._rabbitmq.check(self.checksLogger, self.agentConfig)

    @recordsize
    def getGangliaData(self):
        return self._ganglia.check(self.checksLogger, self.agentConfig)

    @recordsize
    def getDatadogData(self):
        result = {}
        if self._datadogs is not None:
            for dd in self._datadogs:
                result[dd.key] = dd.check(self.checksLogger, self.agentConfig)

        return result
        
    @recordsize
    def getCassandraData(self):
        return self._cassandra.check(self.checksLogger, self.agentConfig)

    #
    # CPU Stats
    #
    @recordsize
    def getCPUStats(self):
        return self._cpu.check(self.checksLogger, self.agentConfig)

    #
    # Postback
    #
    def doChecks(self, sc, firstRun, systemStats=False):
        # Do the checks
        apacheStatus = self.getApacheStatus()
        diskUsage = self.getDiskUsage()
        loadAvrgs = self.getLoadAvrgs()
        memory = self.getMemoryUsage()
        mysqlStatus = self.getMySQLStatus()
        networkTraffic = self.getNetworkTraffic()
        nginxStatus = self.getNginxStatus()
        processes = self.getProcesses()
        rabbitmq = self.getRabbitMQStatus()
        mongodb = self.getMongoDBStatus()
        couchdb = self.getCouchDBStatus()
        plugins = self.getPlugins()
        ioStats = self.getIOStats()
        cpuStats = self.getCPUStats()
        gangliaData = self.getGangliaData()
        datadogData = self.getDatadogData()
        cassandraData = self.getCassandraData()
 
        checksData = {
            'collection_timestamp': time.time(),
            'os' : self.os, 
            'agentKey' : self.agentConfig['agentKey'], 
            'agentVersion' : self.agentConfig['version'], 
            'diskUsage' : diskUsage, 
            'loadAvrg1' : loadAvrgs['1'], 
            'loadAvrg5' : loadAvrgs['5'], 
            'loadAvrg15' : loadAvrgs['15'], 
            'memPhysUsed' : memory['physUsed'], 
            'memPhysFree' : memory['physFree'], 
            'memSwapUsed' : memory['swapUsed'], 
            'memSwapFree' : memory['swapFree'], 
            'memCached' : memory['cached'], 
            'networkTraffic' : networkTraffic, 
            'processes' : processes,
            'apiKey': self.agentConfig['apiKey'],
            'events': {},
        }

        if cpuStats is not False and cpuStats is not None:
            checksData.update(cpuStats)

        if gangliaData is not False and gangliaData is not None:
            checksData['ganglia'] = gangliaData
           
        if datadogData is not False and datadogData is not None:
            checksData['datadog'] = datadogData
            
        if cassandraData is not False and cassandraData is not None:
            checksData['cassandra'] = cassandraData
 
        # Apache Status
        if apacheStatus != False:           
            checksData['apacheReqPerSec'] = apacheStatus['reqPerSec']
            checksData['apacheBusyWorkers'] = apacheStatus['busyWorkers']
            checksData['apacheIdleWorkers'] = apacheStatus['idleWorkers']
            
        # MySQL Status
        if mysqlStatus != False:
            
            checksData['mysqlConnections'] = mysqlStatus['connections']
            checksData['mysqlCreatedTmpDiskTables'] = mysqlStatus['createdTmpDiskTables']
            checksData['mysqlMaxUsedConnections'] = mysqlStatus['maxUsedConnections']
            checksData['mysqlOpenFiles'] = mysqlStatus['openFiles']
            checksData['mysqlSlowQueries'] = mysqlStatus['slowQueries']
            checksData['mysqlTableLocksWaited'] = mysqlStatus['tableLocksWaited']
            checksData['mysqlThreadsConnected'] = mysqlStatus['threadsConnected']
            
            if mysqlStatus['secondsBehindMaster'] != None:
                checksData['mysqlSecondsBehindMaster'] = mysqlStatus['secondsBehindMaster']
        
        # Nginx Status
        if nginxStatus != False:
            checksData['nginxConnections'] = nginxStatus['connections']
            checksData['nginxReqPerSec'] = nginxStatus['reqPerSec']
            
        # RabbitMQ
        if rabbitmq != False:
            checksData['rabbitMQ'] = rabbitmq
        
        # MongoDB
        if mongodb != False:
            checksData['mongoDB'] = mongodb
            
        # CouchDB
        if couchdb != False:
            checksData['couchDB'] = couchdb
        
        # Plugins
        if plugins != False:
            checksData['plugins'] = plugins
        
        if ioStats != False:
            checksData['ioStats'] = ioStats
            
        # Include system stats on first postback
        if firstRun == True:
            checksData['systemStats'] = systemStats
            
        # Include server indentifiers
        try:
            checksData['internalHostname'] = socket.gethostname()
        except socket.error:
            self.checksLogger.exception('Unable to get hostname')
        
        # Generate a unique name that will stay constant between
        # invocations, such as platform.node() + uuid.getnode()
        # Use uuid5, which does not depend on the clock and is
        # recommended over uuid3.
        # This is important to be able to identify a server even if
        # its drives have been wiped clean.
        # Note that this is not foolproof but we can reconcile servers
        # on the back-end if need be, based on mac addresses.
        checksData['uuid'] = uuid.uuid5(uuid.NAMESPACE_DNS, platform.node() + str(uuid.getnode())).hex
        self.checksLogger.debug('doChecks: added uuid %s' % checksData['uuid'])
        
        # Process the event checks. 
        for event_check in self._event_checks:
            event_data = event_check.check(self.checksLogger, self.agentConfig)
            if event_data:
                checksData['events'][event_check.key] = event_data
       
        if firstRun:
            checksData['events']['System'] = [{'api_key': self.agentConfig['apiKey'],
                                              'host': checksData['internalHostname'],
                                              'timestamp': int(time.mktime(datetime.datetime.now().timetuple())),
                                              'event_type':'agent startup',
                                            }]
        
        self.emitter(checksData, self.checksLogger, self.agentConfig)
        
        sc.enter(self.agentConfig['checkFreq'], 1, self.doChecks, (sc, False))  
        
    def getMountedLinuxProcFsLocation(self):
        self.checksLogger.debug('getMountedLinuxProcFsLocation: attempting to fetch mounted partitions')
        
        # Lets check if the Linux like style procfs is mounted
        mountedPartitions = subprocess.Popen(['mount'], stdout = subprocess.PIPE, close_fds = True).communicate()[0]
        location = re.search(r'linprocfs on (.*?) \(.*?\)', mountedPartitions)
        
        # Linux like procfs file system is not mounted so we return False, else we return mount point location
        if location == None:
            return False

        location = location.group(1)
        return location
