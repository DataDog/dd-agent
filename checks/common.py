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

import modules

from config import get_version

from checks import gethostname

from checks.nagios import Nagios
from checks.build import Hudson

from checks.db.mysql import MySql
from checks.db.mongo import MongoDb
from checks.db.redisDb import Redis
from checks.db.couch import CouchDb
from checks.db.pg import PostgreSql
from checks.db.mcache import Memcache

from checks.queue import RabbitMq
from checks.system import Disk, IO, Load, Memory, Network, Processes, Cpu
from checks.web import Apache, Nginx
from checks.ganglia import Ganglia
from checks.cassandra import Cassandra
from checks.datadog import Dogstreams, DdForwarder

from checks.jmx import Jvm, Tomcat, ActiveMQ, Solr
from checks.cacti import Cacti
from checks.varnish import Varnish
from checks.munin import Munin

from checks.db.elastic import ElasticSearch

from checks.ec2 import EC2

from resources.processes import Processes as ResProcesses

def getUuid():
    # Generate a unique name that will stay constant between
    # invocations, such as platform.node() + uuid.getnode()
    # Use uuid5, which does not depend on the clock and is
    # recommended over uuid3.
    # This is important to be able to identify a server even if
    # its drives have been wiped clean.
    # Note that this is not foolproof but we can reconcile servers
    # on the back-end if need be, based on mac addresses.
    return uuid.uuid5(uuid.NAMESPACE_DNS, platform.node() + str(uuid.getnode())).hex

def recordsize(func):
    "Record the size of the response"
    def wrapper(*args, **kwargs):
        logger = logging.getLogger("checks")
        res = func(*args, **kwargs)
        logger.debug("SIZE: %s wrote %d bytes uncompressed" % (func, len(str(res))))
        return res
    return wrapper

class checks(object):
    def __init__(self, agentConfig, emitters):
        self.agentConfig = agentConfig
        self.plugins = None
        self.emitters = emitters
        self.os = None
        
        self.checksLogger = logging.getLogger('checks')
        socket.setdefaulttimeout(15)
        
        self._apache = Apache(self.checksLogger)
        self._nginx = Nginx(self.checksLogger)
        self._disk = Disk(self.checksLogger)
        self._io = IO()
        self._load = Load(self.checksLogger)
        self._memory = Memory(self.checksLogger)
        self._network = Network(self.checksLogger)
        self._processes = Processes()
        self._cpu = Cpu()
        self._couchdb = CouchDb(self.checksLogger)
        self._mongodb = MongoDb(self.checksLogger)
        self._mysql = MySql(self.checksLogger)
        self._pgsql = PostgreSql(self.checksLogger)
        self._rabbitmq = RabbitMq()
        self._ganglia = Ganglia(self.checksLogger)
        self._cassandra = Cassandra()
        self._redis = Redis(self.checksLogger)
        self._jvm = Jvm(self.checksLogger)
        self._tomcat = Tomcat(self.checksLogger)
        self._activemq = ActiveMQ(self.checksLogger)
        self._solr = Solr(self.checksLogger)
        self._memcache = Memcache(self.checksLogger)
        self._dogstream = Dogstreams.init(self.checksLogger, self.agentConfig)
        self._ddforwarder = DdForwarder(self.checksLogger, self.agentConfig)

        # All new checks should be metrics checks:
        self._metrics_checks = [
            Cacti(self.checksLogger),
            Redis(self.checksLogger),
            Varnish(self.checksLogger),
            ElasticSearch(self.checksLogger),
            Munin(self.checksLogger)
            ]
        for module_spec in [s.strip() for s in self.agentConfig.get('custom_checks', '').split(',')]:
            if len(module_spec) == 0: continue
            try:
                self._metrics_checks.append(modules.load(module_spec, 'Check')(self.checksLogger))
            except Exception:
                self.checksLogger.error('Unable to load custom check module %r', module_spec, exc_info=True)

        self._event_checks = [Hudson(), Nagios(socket.gethostname())]
        self._resources_checks = [ResProcesses(self.checksLogger,self.agentConfig)]

        self._ec2 = EC2(self.checksLogger)
    
    #
    # Checks - FIXME migrating to the new Check interface is a WIP
    #
    @recordsize 
    def getApacheStatus(self):
        return self._apache.check(self.agentConfig)

    @recordsize 
    def getCouchDBStatus(self):
        return self._couchdb.check(self.agentConfig)
    
    @recordsize
    def getDiskUsage(self):
        return self._disk.check(self.agentConfig)

    @recordsize
    def getIOStats(self):
        return self._io.check(self.checksLogger, self.agentConfig)
            
    @recordsize
    def getLoadAvrgs(self):
        return self._load.check(self.agentConfig)

    @recordsize 
    def getMemoryUsage(self):
        return self._memory.check(self.agentConfig)
        
    @recordsize     
    def getMongoDBStatus(self):
        return self._mongodb.check(self.agentConfig)

    @recordsize
    def getMySQLStatus(self):
        return self._mysql.check(self.agentConfig)
   
    @recordsize
    def getPgSQLStatus(self):
        return self._pgsql.check(self.agentConfig)
 
    @recordsize
    def getNetworkTraffic(self):
        return self._network.check(self.agentConfig)
    
    @recordsize
    def getNginxStatus(self):
        return self._nginx.check(self.agentConfig)
        
    @recordsize
    def getProcesses(self):
        return self._processes.check(self.checksLogger, self.agentConfig)
        
    @recordsize
    def getRabbitMQStatus(self):
        return self._rabbitmq.check(self.checksLogger, self.agentConfig)

    @recordsize
    def getGangliaData(self):
        return self._ganglia.check(self.agentConfig)

    @recordsize
    def getCassandraData(self):
        return self._cassandra.check(self.checksLogger, self.agentConfig)

    @recordsize
    def getJvmData(self):
        return self._jvm.check(self.agentConfig)

    @recordsize
    def getTomcatData(self):
        return self._tomcat.check(self.agentConfig)

    @recordsize
    def getActiveMQData(self):
        return self._activemq.check(self.agentConfig)

    @recordsize
    def getSolrData(self):
        return self._solr.check(self.agentConfig)

    @recordsize
    def getMemcacheData(self):
        return self._memcache.check(self.agentConfig)

    @recordsize
    def getDogstreamData(self):
        return self._dogstream.check(self.agentConfig)

    @recordsize
    def getDdforwarderData(self):
        return self._ddforwarder.check(self.agentConfig)

    @recordsize
    def getCPUStats(self):
        return self._cpu.check(self.checksLogger, self.agentConfig)

    @recordsize
    def get_metadata(self):
        metadata = self._ec2.get_metadata()
        if metadata.get('hostname'):
            metadata['ec2-hostname'] = metadata.get('hostname')

        if self.agentConfig.get('hostname'):
            metadata['agent-hostname'] = self.agentConfig.get('hostname')

        try:
            metadata["hostname"] = socket.gethostname()
        except:
            pass
        try:
            metadata["fqdn"] = socket.getfqdn()
        except:
            pass

        return metadata

    def doChecks(self, firstRun=False, systemStats=False):
        """Actual work
        """
        self.checksLogger.info("Starting checks")

        apacheStatus = self.getApacheStatus()
        diskUsage = self.getDiskUsage()
        loadAvrgs = self.getLoadAvrgs()
        memory = self.getMemoryUsage()
        mysqlStatus = self.getMySQLStatus()
        pgsqlStatus = self.getPgSQLStatus()
        networkTraffic = self.getNetworkTraffic()
        nginxStatus = self.getNginxStatus()
        processes = self.getProcesses()
        rabbitmq = self.getRabbitMQStatus()
        mongodb = self.getMongoDBStatus()
        couchdb = self.getCouchDBStatus()
        ioStats = self.getIOStats()
        cpuStats = self.getCPUStats()
        gangliaData = self.getGangliaData()
        cassandraData = self.getCassandraData()
        jvmData = self.getJvmData()
        tomcatData = self.getTomcatData()
        activeMQData = self.getActiveMQData()
        solrData = self.getSolrData()
        memcacheData = self.getMemcacheData()
        dogstreamData = self.getDogstreamData()
        ddforwarderData = self.getDdforwarderData()

        checksData = {
            'collection_timestamp': time.time(),
            'os' : self.os,
            'python': sys.version,
            'agentVersion' : self.agentConfig['version'], 
            'loadAvrg1' : loadAvrgs['1'], 
            'loadAvrg5' : loadAvrgs['5'], 
            'loadAvrg15' : loadAvrgs['15'], 
            'memPhysUsed' : memory.get('physUsed'), 
            'memPhysFree' : memory.get('physFree'), 
            'memPhysTotal' : memory.get('physTotal'), 
            'memPhysUsable' : memory.get('physUsable'), 
            'memSwapUsed' : memory.get('swapUsed'), 
            'memSwapFree' : memory.get('swapFree'), 
            'memSwapTotal' : memory.get('swapTotal'), 
            'memCached' : memory.get('physCached'), 
            'memBuffers': memory.get('physBuffers'),
            'memShared': memory.get('physShared'),
            'networkTraffic' : networkTraffic, 
            'processes' : processes,
            'apiKey': self.agentConfig['api_key'],
            'events': {},
            'resources': {},
        }

        if diskUsage is not False and len(diskUsage) == 2:
            checksData["diskUsage"] = diskUsage[0]
            checksData["inodes"] = diskUsage[1]
            
        if cpuStats is not False and cpuStats is not None:
            checksData.update(cpuStats)

        if gangliaData is not False and gangliaData is not None:
            checksData['ganglia'] = gangliaData
           
        if cassandraData is not False and cassandraData is not None:
            checksData['cassandra'] = cassandraData
 
        # Apache Status
        if apacheStatus: 
            checksData.update(apacheStatus)
            
        # MySQL Status
        if mysqlStatus:
            checksData.update(mysqlStatus)
       
        # PostgreSQL status
        if pgsqlStatus: 
            checksData['postgresql'] = pgsqlStatus

        # Nginx Status
        if nginxStatus:
            checksData.update(nginxStatus)
            
        # RabbitMQ
        if rabbitmq:
            checksData['rabbitMQ'] = rabbitmq
        
        # MongoDB
        if mongodb:
            if mongodb.has_key('events'):
                checksData['events']['Mongo'] = mongodb['events']['Mongo']
                del mongodb['events']
            checksData['mongoDB'] = mongodb
            
        # CouchDB
        if couchdb:
            checksData['couchDB'] = couchdb
        
        if ioStats:
            checksData['ioStats'] = ioStats
            
        if jvmData:
            checksData['jvm'] = jvmData

        if tomcatData:
            checksData['tomcat'] = tomcatData

        if activeMQData:
            checksData['activemq'] = activeMQData

        if solrData:
            checksData['solr'] = solrData

        if memcacheData:
            checksData['memcache'] = memcacheData
        
        if dogstreamData:
            dogstreamEvents = dogstreamData.get('dogstreamEvents', None)
            if dogstreamEvents:
                if 'dogstream' in checksData['events']:
                    checksData['events']['dogstream'].extend(dogstreamEvents)
                else:
                    checksData['events']['dogstream'] = dogstreamEvents
                del dogstreamData['dogstreamEvents']

            checksData.update(dogstreamData)

        if ddforwarderData:
            checksData['datadog'] = ddforwarderData
 
        # Include server indentifiers
        checksData['internalHostname'] = gethostname(self.agentConfig)
        checksData['uuid'] = getUuid()
        self.checksLogger.debug('doChecks: added uuid %s' % checksData['uuid'])
        
        # Process the event checks. 
        for event_check in self._event_checks:
            event_data = event_check.check(self.checksLogger, self.agentConfig)
            if event_data:
                checksData['events'][event_check.key] = event_data
       
       # Include system stats on first postback
        if firstRun:
            checksData['systemStats'] = systemStats
            # Add static tags from the configuration file
            if self.agentConfig['tags'] is not None:
                checksData['tags'] = self.agentConfig['tags']
            # Also post an event in the newsfeed
            checksData['events']['System'] = [{'api_key': self.agentConfig['api_key'],
                                               'host': checksData['internalHostname'],
                                               'timestamp': int(time.mktime(datetime.datetime.now().timetuple())),
                                               'event_type':'Agent Startup',
                                               'msg_text': 'Version %s' % get_version()
                                            }]

            # Collect metadata
            checksData['meta'] = self.get_metadata()

        # Resources checks
        has_resource = False
        for resources_check in self._resources_checks:
            resources_check.check()
            snaps = resources_check.pop_snapshots()
            if snaps:
                has_resource = True
                res_value = { 'snaps': snaps,
                              'format_version': resources_check.get_format_version() }                              
                res_format = resources_check.describe_format_if_needed()
                if res_format is not None:
                    res_value['format_description'] = res_format
                checksData['resources'][resources_check.RESOURCE_KEY] = res_value
 
        if has_resource:
            checksData['resources']['meta'] = {
                        'api_key': self.agentConfig['api_key'],
                        'host': checksData['internalHostname'],
                    }

        metrics = []
        for metrics_check in self._metrics_checks:
            res = metrics_check.check(self.agentConfig)
            if res:
                metrics.extend(res)
        checksData['metrics'] = metrics

        # Send back data
        self.checksLogger.debug("checksData: %s" % checksData)
        for emitter in self.emitters:
            emitter(checksData, self.checksLogger, self.agentConfig)
        self.checksLogger.info("Checks done")
