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
import sched
import sys
import time

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
            if url.getcode() == 200:
                instanceId = url.read()
                return instanceId

        except Exception, e:
            pass

        return None

    
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
        if agentConfig.get('hostname') is None:
            instanceId = self.get_ec2_instance_id()
            if instanceId is not None:
                agentLogger.info("Running on EC2, instanceId: %s" % instanceId)
                agentConfig['hostname'] = instanceId
            else:
                agentLogger.info('Not running on EC2')
 
        emitter = http_emitter
        
        # Checks instance
        c = checks(agentConfig, rawConfig, emitter)
        
        # Schedule the checks
        agentLogger.debug('Scheduling checks every ' + str(agentConfig['checkFreq']) + ' seconds')
        s = sched.scheduler(time.time, time.sleep)
        c.doChecks(s, True, systemStats) # start immediately (case 28315)
        if run_forever:
            s.run()
        
def setupLogging(agentConfig):
    """Used by ddagent.py as well"""
    if agentConfig['debugMode']:
        logFile = os.path.join(agentConfig['tmpDirectory'], 'dd-agent.log')
        logging.basicConfig(filename=logFile, filemode='w', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        try:
            from logging.handlers import SysLogHandler
            rootLog = logging.getLogger()
            rootLog.setLevel(logging.INFO)
            if sys.platform == 'darwin':
                sys_log_addr = "/var/run/syslog"
            else:
                sys_log_addr = "/dev/log"
        
            handler = SysLogHandler(address=sys_log_addr,facility=SysLogHandler.LOG_DAEMON)
            formatter = logging.Formatter("dd-agent - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            rootLog.addHandler(handler) 
        except Exception,e:
            sys.stdout.write("Error while setting up syslog logging (%s), no logging will be done" % str(e))
            logging.disable(logging.ERROR)

    mainLogger = logging.getLogger('main')      
    mainLogger.debug('Agent called')
    mainLogger.debug('Agent version: ' + agentConfig['version'])


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
        mainLogger.debug('Agent called with --clean option, removing .pid')
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

    mainLogger = logging.getLogger('main')      
    
    # FIXME
    # Ever heard of optparse?

    argLen = len(sys.argv)
    
    if len(args) > 0:
        command = args[0]

        # Daemon instance from agent class
        pidFile = getPidFile(command, agentConfig, options.clean)
        daemon = agent(pidFile)
    
        if 'start' == command:
            mainLogger.debug('Start daemon')
            daemon.start()
            
        elif 'stop' == command:
            mainLogger.debug('Stop daemon')
            daemon.stop()
            
        elif 'restart' == command:
            mainLogger.debug('Restart daemon')
            daemon.restart()
            
        elif 'foreground' == command:
            mainLogger.debug('Running in foreground')
            daemon.run()
            
        elif 'status' == command:
            mainLogger.debug('Checking agent status')
            
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
            else:
                sys.stdout.write('dd-agent is not running.\n')

        else:
            sys.stderr.write('Unknown command: %s.\n' % sys.argv[1])
            sys.exit(2)
            
        sys.exit(0)
        
    else:
        sys.stderr.write('Usage: %s start|stop|restart|foreground|status' % sys.argv[0])
        sys.exit(2)
