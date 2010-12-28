'''
    Server Density
    www.serverdensity.com
    ----
    A web based server resource monitoring application

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
'''

# SO references
# http://stackoverflow.com/questions/446209/possible-values-from-sys-platform/446210#446210
# http://stackoverflow.com/questions/682446/splitting-out-the-output-of-ps-using-python/682464#682464
# http://stackoverflow.com/questions/1052589/how-can-i-parse-the-output-of-proc-net-dev-into-keyvalue-pairs-per-interface-us

# Core modules
import httplib # Used only for handling httplib.HTTPException (case #26701)
import logging
import logging.handlers
import os
import platform
import re
import subprocess
import sys
import urllib
import urllib2

# Needed to identify server uniquely
import uuid
try:
    from hashlib import md5
except ImportError: # Python < 2.5
    from md5 import new as md5

from .nagios import Nagios
from .build import Hudson
from .db import CouchDb, MongoDb, MySql
from .queue import RabbitMq
from .system import Disk, IO, Load, Memory, Network, Processes, Cpu
from .web import Apache, Nginx
from .ganglia import Ganglia

# We need to return the data using JSON. As of Python 2.6+, there is a core JSON
# module. We have a 2.4/2.5 compatible lib included with the agent but if we're
# on 2.6 or above, we should use the core module which will be faster
pythonVersion = platform.python_version_tuple()

if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
    import json
else:
    import minjson

def recordsize(func):
    def wrapper(*args, **kwargs):
        logger = logging.getLogger("checks")
        res = func(*args, **kwargs)
        logger.debug("SIZE: {0} wrote {1} bytes uncompressed".format(func, len(str(res))))
        return res
    return wrapper

class checks:
    
    def __init__(self, agentConfig, rawConfig):
        self.agentConfig = agentConfig
        self.rawConfig = rawConfig
        self.plugins = None
        
        macV = None
        if sys.platform == 'darwin':
            macV = platform.mac_ver()
        
        # Output from top is slightly modified on OS X 10.6 (case #28239)
        if macV and macV[0].startswith('10.6.'):
            self.topIndex = 6
        else:
            self.topIndex = 5
    
        self.os = None
        
        self.checksLogger = logging.getLogger('checks')
        # Set global timeout to 15 seconds for all sockets (case 31033). Should be long enough
        import socket
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
        self._event_checks = [Hudson(), Nagios(socket.gethostname())]
        
        # Build the request headers
        self.headers = {
            'User-Agent': 'Datadog Agent/%s' % self.agentConfig['version'],
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html, */*',
        }
    
    #
    # Checks
    #
    @recordsize 
    def getApacheStatus(self):
        return self._apache.check(self.checksLogger, self.agentConfig, self.headers)

    @recordsize 
    def getCouchDBStatus(self):
        return self._couchdb.check(self.checksLogger, self.agentConfig, self.headers)
    
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
    def getVMStat(self):
        """Provide the same data that vmstat on linux provides"""
        # on mac, try top -S -n0 -l1
        pass
    
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
        return self._nginx.check(self.checksLogger, self.agentConfig, self.headers)
        
    @recordsize
    def getProcesses(self):
        return self._processes.check(self.checksLogger, self.agentConfig)
        
    @recordsize
    def getRabbitMQStatus(self):
        return self._rabbitmq.check(self.checksLogger, self.agentConfig)

    @recordsize
    def getGangliaData(self):
        return self._ganglia.check(self.checksLogger, self.agentConfig)

    #
    # CPU Stats
    #
    @recordsize
    def getCPUStats(self):
        return self._cpu.check(self.checksLogger, self.agentConfig)
        
    #
    # Plugins
    #
        
    def getPlugins(self):
        self.checksLogger.debug('getPlugins: start')
        
        if 'pluginDirectory' in self.agentConfig:
            if os.path.exists(self.agentConfig['pluginDirectory']) == False:
                self.checksLogger.debug('getPlugins: ' + self.agentConfig['pluginDirectory'] + ' directory does not exist')
                return False
        else:
            return False
        
        # Have we already imported the plugins?
        # Only load the plugins once
        if self.plugins == None:
            self.checksLogger.debug('getPlugins: initial load from ' + self.agentConfig['pluginDirectory'])
            
            sys.path.append(self.agentConfig['pluginDirectory'])
            
            self.plugins = []
            plugins = []
            
            # Loop through all the plugin files
            for root, dirs, files in os.walk(self.agentConfig['pluginDirectory']):
                for name in files:
                    self.checksLogger.debug('getPlugins: considering: ' + name)
                
                    name = name.split('.', 1)
                    
                    # Only pull in .py files (ignores others, inc .pyc files)
                    try:
                        if name[1] == 'py':
                            
                            self.checksLogger.debug('getPlugins: ' + name[0] + '.' + name[1] + ' is a plugin')
                            
                            plugins.append(name[0])
                            
                    except IndexError, e:
                        
                        continue
            
            # Loop through all the found plugins, import them then create new objects
            for pluginName in plugins:
                self.checksLogger.debug('getPlugins: importing ' + pluginName)
                
                # Import the plugin, but only from the pluginDirectory (ensures no conflicts with other module names elsehwhere in the sys.path
                import imp
                importedPlugin = imp.load_source(pluginName, os.path.join(self.agentConfig['pluginDirectory'], '%s.py' % pluginName))
                
                self.checksLogger.debug('getPlugins: imported ' + pluginName)
                
                try:
                    # Find out the class name and then instantiate it
                    pluginClass = getattr(importedPlugin, pluginName)
                    
                    try:
                        pluginObj = pluginClass(self.agentConfig, self.checksLogger, self.rawConfig)
                    except TypeError:
                        
                        try:
                            pluginObj = pluginClass(self.agentConfig, self.checksLogger)
                        except TypeError:
                            # Support older plugins.
                            pluginObj = pluginClass()
                
                    self.checksLogger.debug('getPlugins: instantiated ' + pluginName)
                
                    # Store in class var so we can execute it again on the next cycle
                    self.plugins.append(pluginObj)
                except Exception, ex:
                    import traceback
                    self.checksLogger.error('getPlugins: exception = ' + traceback.format_exc())
                    
        # Now execute the objects previously created
        if self.plugins != None:            
            self.checksLogger.debug('getPlugins: executing plugins')
            
            # Execute the plugins
            output = {}
                    
            for plugin in self.plugins:             
                self.checksLogger.debug('getPlugins: executing ' + plugin.__class__.__name__)
                
                output[plugin.__class__.__name__] = plugin.run()
                
                self.checksLogger.debug('getPlugins: executed ' + plugin.__class__.__name__)
            
            self.checksLogger.debug('getPlugins: returning')
            
            # Each plugin should output a dictionary so we can convert it to JSON later 
            return output
            
        else:           
            self.checksLogger.debug('getPlugins: no plugins, returning false')
            
            return False
    
    #
    # Postback
    #
    
    def doPostBack(self, postBackData):
        self.checksLogger.debug('doPostBack: start')    
        
        try: 
            self.checksLogger.debug('doPostBack: attempting postback: ' + self.agentConfig['sdUrl'])
            
            # Build the request handler
            request = urllib2.Request(self.agentConfig['sdUrl'] + '/intake/', postBackData, self.headers)
            
            # Do the request, log any errors
            response = urllib2.urlopen(request)
            
            self.checksLogger.debug('doPostBack: postback response: ' + str(response.read()))
                
        except urllib2.HTTPError, e:
            self.checksLogger.error('doPostBack: HTTPError = ' + str(e))
            return False
            
        except urllib2.URLError, e:
            self.checksLogger.error('doPostBack: URLError = ' + str(e))
            return False
            
        except httplib.HTTPException, e: # Added for case #26701
            self.checksLogger.error('doPostBack: HTTPException')
            return False
                
        except Exception, e:
            import traceback
            self.checksLogger.error('doPostBack: Exception = ' + traceback.format_exc())
            return False
            
        self.checksLogger.debug('doPostBack: completed')
        return True
    
    def doChecks(self, sc, firstRun, systemStats=False):
        macV = None
        if sys.platform == 'darwin':
            macV = platform.mac_ver()
        
        if not self.os:
            if macV:
                self.os = 'mac'
            elif sys.platform.find('freebsd') != -1:
                self.os = 'freebsd'
            else:
                self.os = 'linux'
        
        self.checksLogger.debug('doChecks: start')
        
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
        
        self.checksLogger.debug('doChecks: checks success, build payload')
        
        checksData = {
            'os' : self.os, 
            'agentKey' : self.agentConfig['agentKey'], 
            'agentVersion' : self.agentConfig['version'], 
            'diskUsage' : diskUsage, 
            'loadAvrg'   : loadAvrgs['1'], 
            'loadAvrg5'  : loadAvrgs['5'], 
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

        if cpuStats != False and cpuStats is not None:
            checksData.update(cpuStats)

        if gangliaData != False:
            checksData['ganglia'] = gangliaData
            
        self.checksLogger.debug('doChecks: payload built, build optional payloads')
        
        # Apache Status
        if apacheStatus != False:           
            checksData['apacheReqPerSec'] = apacheStatus['reqPerSec']
            checksData['apacheBusyWorkers'] = apacheStatus['busyWorkers']
            checksData['apacheIdleWorkers'] = apacheStatus['idleWorkers']
            
            self.checksLogger.debug('doChecks: built optional payload apacheStatus')
        
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
            self.checksLogger.debug('doChecks: built optional payload systemStats')
            
        # Include server indentifiers
        import socket   
        
        try:
            checksData['internalHostname'] = socket.gethostname()
            
        except socket.error, e:
            self.checksLogger.debug('Unable to get hostname: ' + str(e))
        
        self.checksLogger.debug('doChecks: payloads built, convert to json')
                    
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
        
        # Post back the data
        if int(pythonVersion[1]) >= 6:
            self.checksLogger.debug('doChecks: json convert')
            payload = json.dumps(checksData)
        
        else:
            self.checksLogger.debug('doChecks: minjson convert')
            payload = minjson.write(checksData)
            
        self.checksLogger.debug('doChecks: json converted, hash')
        self.checksLogger.debug('Payload: %s...' % payload[:min(len(payload), 132)])
        
        payloadHash = md5(payload).hexdigest()
        postBackData = urllib.urlencode({'payload' : payload, 'hash' : payloadHash})

        self.checksLogger.debug('doChecks: hashed, doPostBack')

        # For tests, no need to post data back
        if self.doPostBack(postBackData):
            self.checksLogger.debug('doChecks: posted back, reschedule')
        else:
            self.checksLogger.error('doChecks: could not send data back')
        
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
