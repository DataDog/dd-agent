#!/usr/bin/python
'''
    Datadog
    www.datadoghq.com
    ----
    Make sense of your IT Data

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
    (C) Datadog, Inc. 2010 all rights reserved
'''

# Core modules
import logging
import os
import os.path
import re
import sys
import time
import urllib

# Watchdog implementation
from threading import Timer
WATCHDOG_MULTIPLIER = 10 # will fire if no checks have been collected in N * checkFreq, 150s by default

# Check we're not using an old version of Python. We need 2.4 above because some modules (like subprocess)
# were only introduced in 2.4.
if int(sys.version_info[1]) <= 3:
    sys.stderr.write("Datadog agent requires python 2.4 or later.\n")
    sys.exit(2)
    
# Custom modules
from checks.common import checks
from config import get_config, get_system_stats, get_parsed_args
from daemon import Daemon
from emitter import http_emitter

# Override the generic daemon class to run our checks
class agent(Daemon):    

    EC2_URL = "http://169.254.169.254/latest/meta-data/instance-id"

    @staticmethod
    def get_ec2_instance_id():
        """Fetch EC2 instance ID if possible. If not on EC2 returns None"""
        try:
            url = urllib.urlopen(agent.EC2_URL)
            instanceId = url.read()
            assert instanceId.startswith("i-"), "Malformed instance-id: %s" % instanceId
            return instanceId

        except Exception, e:
            logging.getLogger('agent').exception('Cannot determine instance-id. Is this machine on EC2?')

        return None

    def late(self, cks, threshold, crash=True):
        """Determine whether the agent run is late and optionally kill it if so.
        """
        late_p = cks.lastPostTs() is None or (time.time() - cks.lastPostTs() > threshold)
        if late_p:
            logging.error("Checks are late by at least %s seconds. Killing the agent..." % threshold)
            # Calling sys.exit here only raises an exception that will be caught along the way.
            if crash:
                self.selfdestruct()
        return late_p
    
    def run(self, agentConfig=None, run_forever=True):  
        agentLogger = logging.getLogger('agent')

        agentLogger.debug('Collecting basic system stats')
        systemStats = get_system_stats()
        agentLogger.debug('System: ' + str(systemStats))
                        
        agentLogger.debug('Creating checks instance')
        
        if agentConfig is None:
            agentConfig, rawConfig = get_config()
        else:
            rawConfig = {}

        # Try to fetch instance Id from EC2 if not hostname has been set
        # in the config file
        if agentConfig.get('hostname') is None and agentConfig.get('useEC2InstanceId'):
            instanceId = self.get_ec2_instance_id()
            if instanceId is not None:
                agentLogger.info("Running on EC2, instanceId: %s" % instanceId)
                agentConfig['hostname'] = instanceId
            else:
                agentLogger.info('Not running on EC2')
 
        emitter = http_emitter

        checkFreq = int(agentConfig['checkFreq'])
        lateThresh = checkFreq * WATCHDOG_MULTIPLIER
        
        # Checks instance
        c = checks(agentConfig, rawConfig, emitter)
        
        # Run once
        c.doChecks(True, systemStats)

        while run_forever:
            # Sleep, checkFreq is misleading. It's not really.
            time.sleep(checkFreq)

            if agentConfig.get("watchdog", True):
                # Start the watchdog in a separate thread
                agentLogger.debug("Starting watchdog, waiting %s seconds." % lateThresh)
                t = Timer(lateThresh, self.late, (c, lateThresh, True))
                t.start()

            # Run checks
            c.doChecks()

            if agentConfig.get("watchdog", True):
                # Kill watchdog if it has not fired
                t.cancel()

            agentLogger.debug("Getting ready to sleep for %s seconds." % lateThresh)
        
def setupLogging(agentConfig):
    """Used by ddagent.py as well"""
    if agentConfig['debugMode']:
        logFile = os.path.join(agentConfig['tmpDirectory'], 'dd-agent.log')
        logging.basicConfig(filename=logFile, filemode='w', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.info("Logging to %s" % logFile)
    else:
        try:
            from logging.handlers import SysLogHandler
            rootLog = logging.getLogger()
            rootLog.setLevel(logging.INFO)

            sys_log_addr = "/dev/log"

            # Special-case macs
            if sys.platform == 'darwin':
                sys_log_addr = "/var/run/syslog"
            
            handler = SysLogHandler(address=sys_log_addr, facility=SysLogHandler.LOG_DAEMON)
            formatter = logging.Formatter("dd-agent - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            rootLog.addHandler(handler) 
            logging.info('Logging to syslog is set up')
        except Exception,e:
            sys.stderr.write("Error while setting up syslog logging (%s). No logging available" % str(e))
            logging.disable(logging.ERROR)

def getPidFile(command, agentConfig, clean):
    """Used by ddagent.py as well"""

    if command == 'init': 
        # This path added for newer Linux packages which run under
        # a separate dd-agent user account.
        if os.path.exists('/var/run/dd-agent/'):
            pidFile = '/var/run/dd-agent/dd-agent.pid'
        else:
            pidFile = '/var/run/dd-agent.pid'
            
    else:
        pidFile = os.path.join(agentConfig['pidfileDirectory'], 'dd-agent.pid')

    if clean:
        logging.debug('Agent called with --clean option, removing .pid')
        try:
            os.remove(pidFile)
        except OSError:
            # Did not find pid file
            pass

    return pidFile
 
# Control of daemon     
if __name__ == '__main__':  
 
    options, args = get_parsed_args()
    agentConfig, rawConfig = get_config()
    
    # Logging
    setupLogging(agentConfig)

    # FIXME
    # Ever heard of optparse?

    argLen = len(sys.argv)
    
    if len(args) > 0:
        command = args[0]

        # Daemon instance from agent class
        pidFile = getPidFile(command, agentConfig, options.clean)
        daemon = agent(pidFile)
    
        if 'start' == command:
            logging.info('Start daemon')
            daemon.start()
            
        elif 'stop' == command:
            logging.info('Stop daemon')
            daemon.stop()
            
        elif 'restart' == command:
            logging.info('Restart daemon')
            daemon.restart()
            
        elif 'foreground' == command:
            logging.info('Running in foreground')
            daemon.run()
            
        elif 'status' == command:
            try:
                pf = file(pidFile,'r')
                pid = int(pf.read().strip())
                pf.close()
            except IOError:
                pid = None
            except SystemExit:
                pid = None
                
            if pid:
                sys.stdout.write('dd-agent is running as pid %s.\n' % pid)
                logging.info("dd-agent is running as pid %s." % pid)
            else:
                sys.stdout.write('dd-agent is not running.\n')
                logging.info("dd-agent is not running.")

        else:
            sys.stderr.write('Unknown command: %s.\n' % sys.argv[1])
            sys.exit(2)
            
        sys.exit(0)
        
    else:
        sys.stderr.write('Usage: %s start|stop|restart|foreground|status' % sys.argv[0])
        sys.exit(2)
