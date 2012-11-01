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

from util import getOS
from config import get_version
from checks import gethostname

import checks.system.unix as u
import checks.system.win32 as w32

from checks.nagios import Nagios
from checks.build import Hudson

from checks.db.mysql import MySql
from checks.db.mongo import MongoDb
from checks.db.couch import CouchDb
from checks.db.mcache import Memcache

from checks.queue import RabbitMq
from checks.web import Apache, Nginx
from checks.ganglia import Ganglia
from checks.cassandra import Cassandra
from checks.datadog import Dogstreams, DdForwarder

from checks.jmx import Jvm, Tomcat, ActiveMQ, Solr
from checks.varnish import Varnish

from checks.db.elastic import ElasticSearch, ElasticSearchClusterStatus

from checks.wmi_check import WMICheck

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

class checks(object):
    def __init__(self, agentConfig, emitters):
        self.agentConfig = agentConfig
        self.os = getOS()
        self.plugins = None
        self.emitters = emitters            
        self.checksLogger = logging.getLogger('checks')
        self.metadata_interval = int(agentConfig.get('metadata_interval', 5 * 60 * 60))
        self.metadata_start = time.time()
        socket.setdefaulttimeout(15)
        
        # Unix System Checks
        self._unix_system_checks = {
            'disk': u.Disk(self.checksLogger),
            'io': u.IO(),
            'load': u.Load(self.checksLogger),
            'memory': u.Memory(self.checksLogger),
            'network': u.Network(self.checksLogger),
            'processes': u.Processes(),
            'cpu': u.Cpu()
        }

        # Win32 System Checks
        self._win32_system_checks = {
            'disk': w32.Disk(self.checksLogger),
            'io': w32.IO(self.checksLogger),
            'proc': w32.Processes(self.checksLogger),
            'memory': w32.Memory(self.checksLogger),
            'network': w32.Network(self.checksLogger),
            'cpu': w32.Cpu(self.checksLogger)
        }

        # Old-style metric checks
        self._apache = Apache(self.checksLogger)
        self._couchdb = CouchDb(self.checksLogger)
        self._mongodb = MongoDb(self.checksLogger)
        self._mysql = MySql(self.checksLogger)
        self._rabbitmq = RabbitMq()
        self._ganglia = Ganglia(self.checksLogger)
        self._cassandra = Cassandra()
        self._dogstream = Dogstreams.init(self.checksLogger, self.agentConfig)
        self._ddforwarder = DdForwarder(self.checksLogger, self.agentConfig)
        self._ec2 = EC2(self.checksLogger)

        # Metric Checks
        self._metrics_checks = [
            Varnish(self.checksLogger),
            ElasticSearch(self.checksLogger),
            Jvm(self.checksLogger),
            Tomcat(self.checksLogger),
            ActiveMQ(self.checksLogger),
            Solr(self.checksLogger),
            WMICheck(self.checksLogger),
            Nginx(self.checksLogger),
            Memcache(self.checksLogger),
        ]

        # Custom metric checks
        for module_spec in [s.strip() for s in self.agentConfig.get('custom_checks', '').split(',')]:
            if len(module_spec) == 0: continue
            try:
                self._metrics_checks.append(modules.load(module_spec, 'Check')(self.checksLogger))
                self.checksLogger.info("Registered custom check %s" % module_spec)
            except Exception, e:
                self.checksLogger.exception('Unable to load custom check module %s' % module_spec)

        # Event Checks
        self._event_checks = [
            ElasticSearchClusterStatus(self.checksLogger),
            Nagios(socket.gethostname())
        ]

        # Resource Checks
        self._resources_checks = [
            ResProcesses(self.checksLogger,self.agentConfig)
        ]
    
    def get_metadata(self):
        metadata = self._ec2.get_metadata()
        if metadata.get('hostname'):
            metadata['ec2-hostname'] = metadata.get('hostname')

        # if hostname is set in the configuration file
        # use that instead of gethostname
        # gethostname is vulnerable to 2 hosts: x.domain1, x.domain2
        # will cause both to be aliased (see #157)
        if self.agentConfig.get('hostname'):
            metadata['agent-hostname'] = self.agentConfig.get('hostname')
            metadata['hostname'] = metadata['agent-hostname']
        else:
            try:
                metadata["hostname"] = socket.gethostname()
            except:
                pass
        try:
            metadata["fqdn"] = socket.getfqdn()
        except:
            pass

        return metadata

    def should_send_metadata(self):
        # If the interval has passed, send the metadata again
        now = time.time()
        if now - self.metadata_start >= self.metadata_interval:
            self.checksLogger.debug('Metadata interval has passed. Sending metadata.')
            self.metadata_start = now
            return True

        return False

    def doChecks(self, firstRun=False, systemStats=False, checksd=None):
        """Actual work
        """
        self.checksLogger.info("Starting checks")
        checksData = {
            'collection_timestamp': time.time(),
            'os' : self.os,
            'python': sys.version,
            'agentVersion' : self.agentConfig['version'],             
            'apiKey': self.agentConfig['api_key'],
            'events': {},
            'resources': {}
        }
        metrics = []
        events = {}

        # Run the system checks. Checks will depend on the OS
        if self.os == 'windows':
            # Win32 system checks
            metrics.extend(self._win32_system_checks['disk'].check(self.agentConfig))
            metrics.extend(self._win32_system_checks['memory'].check(self.agentConfig))
            metrics.extend(self._win32_system_checks['cpu'].check(self.agentConfig))
            metrics.extend(self._win32_system_checks['network'].check(self.agentConfig))
            metrics.extend(self._win32_system_checks['io'].check(self.agentConfig))
            metrics.extend(self._win32_system_checks['proc'].check(self.agentConfig))
        else:
            # Unix system checks
            sys_checks = self._unix_system_checks

            diskUsage = sys_checks['disk'].check(self.agentConfig)
            if diskUsage is not False and len(diskUsage) == 2:
                checksData["diskUsage"] = diskUsage[0]
                checksData["inodes"] = diskUsage[1]

            loadAvrgs = sys_checks['load'].check(self.agentConfig)
            checksData.update({
                'loadAvrg1': loadAvrgs['1'],
                'loadAvrg5': loadAvrgs['5'],
                'loadAvrg15': loadAvrgs['15']
            })

            memory = sys_checks['memory'].check(self.agentConfig)
            checksData.update({
                'memPhysUsed' : memory.get('physUsed'), 
                'memPhysFree' : memory.get('physFree'), 
                'memPhysTotal' : memory.get('physTotal'), 
                'memPhysUsable' : memory.get('physUsable'), 
                'memSwapUsed' : memory.get('swapUsed'), 
                'memSwapFree' : memory.get('swapFree'), 
                'memSwapTotal' : memory.get('swapTotal'), 
                'memCached' : memory.get('physCached'), 
                'memBuffers': memory.get('physBuffers'),
                'memShared': memory.get('physShared')
            })

            ioStats = sys_checks['io'].check(self.checksLogger, self.agentConfig)
            if ioStats:
                checksData['ioStats'] = ioStats

            processes = sys_checks['processes'].check(self.checksLogger, self.agentConfig)
            checksData.update({'processes': processes})

            networkTraffic = sys_checks['network'].check(self.agentConfig)
            checksData.update({'networkTraffic': networkTraffic})

            cpuStats = sys_checks['cpu'].check(self.checksLogger, self.agentConfig)
            if cpuStats is not False and cpuStats is not None:
                checksData.update(cpuStats)

        # Run old-style checks
        apacheStatus = self._apache.check(self.agentConfig)
        mysqlStatus = self._mysql.check(self.agentConfig)
        rabbitmq = self._rabbitmq.check(self.checksLogger, self.agentConfig)
        mongodb = self._mongodb.check(self.agentConfig)
        couchdb = self._couchdb.check(self.agentConfig)
        gangliaData = self._ganglia.check(self.agentConfig)
        cassandraData = self._cassandra.check(self.checksLogger, self.agentConfig)
        dogstreamData = self._dogstream.check(self.agentConfig)
        ddforwarderData = self._ddforwarder.check(self.agentConfig)

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
       
        # RabbitMQ
        if rabbitmq:
            checksData['rabbitMQ'] = rabbitmq
        
        # MongoDB
        if mongodb:
            if mongodb.has_key('events'):
                events['Mongo'] = mongodb['events']['Mongo']
                del mongodb['events']
            checksData['mongoDB'] = mongodb
            
        # CouchDB
        if couchdb:
            checksData['couchDB'] = couchdb
            
        if dogstreamData:
            dogstreamEvents = dogstreamData.get('dogstreamEvents', None)
            if dogstreamEvents:
                if 'dogstream' in checksData['events']:
                    events['dogstream'].extend(dogstreamEvents)
                else:
                    events['dogstream'] = dogstreamEvents
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
                events[event_check.key] = event_data
       
        # Include system stats on first postback
        if firstRun:
            checksData['systemStats'] = systemStats
            # Also post an event in the newsfeed
            events['System'] = [{'api_key': self.agentConfig['api_key'],
                                               'host': checksData['internalHostname'],
                                               'timestamp': int(time.mktime(datetime.datetime.now().timetuple())),
                                               'event_type':'Agent Startup',
                                               'msg_text': 'Version %s' % get_version()
                                            }]

        if firstRun or self.should_send_metadata():
            # Collect metadata
            checksData['meta'] = self.get_metadata()
            # Add static tags from the configuration file
            if self.agentConfig['tags'] is not None:
                checksData['tags'] = self.agentConfig['tags']

        # Resources checks
        if self.os != 'windows':
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

        for metrics_check in self._metrics_checks:
            res = metrics_check.check(self.agentConfig)
            if res:
                metrics.extend(res)

        # checks.d checks
        checksd = checksd or []
        for check in checksd:
            check_cls = check['class']
            for instance in check['instances']:
                try:
                    # Run the check for each configuration
                    check_cls.check(instance)
                    metrics.extend(check_cls.get_metrics())
                    if check_cls.has_events():
                        if check['name'] not in events:
                            events[check['name']] = []
                        for ev in check_cls.get_events():
                            events[check['name']].append(ev)
                except Exception:
                    self.checksLogger.exception("Check %s failed" % check_cls.name)


        # Store the metrics in the payload
        checksData['metrics'] = metrics

        # Store the events in the payload
        checksData['events'] = events

        # Send back data
        self.checksLogger.debug("checksData: %s" % checksData)
        for emitter in self.emitters:
            emitter(checksData, self.checksLogger, self.agentConfig)
        self.checksLogger.info("Checks done")
