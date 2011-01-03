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
import ConfigParser
import logging
import os
import os.path
import re
import sched
import sys
import time

# CONSTANTS
DATADOG_CONF = "datadog.conf"

# General config
agentConfig = {}
agentConfig['debugMode'] = False
agentConfig['checkFreq'] = 15
agentConfig['version'] = '1.9.0'

rawConfig = {}

# Check we're not using an old version of Python. We need 2.4 above because some modules (like subprocess)
# were only introduced in 2.4.
if int(sys.version_info[1]) <= 3:
    sys.stderr.write("Datadog agent requires python 2.4 or later.\n")
    sys.exit(2)
    
# After the version check as this isn't available on older Python versions
# and will error before the message is shown
import subprocess
    
# Custom modules
from checks import checks
from daemon import Daemon

# Config handling
try:
    path = os.path.realpath(__file__)
    path = os.path.dirname(path)
    
    config = ConfigParser.ConfigParser()
    if os.path.exists(os.path.join('/etc/dd-agent', DATADOG_CONF)):
        config.read(os.path.join('/etc/dd-agent', DATADOG_CONF))
    elif os.path.exists(os.path.join(path, DATADOG_CONF)):
        config.read(os.path.join(path, DATADOG_CONF))
    else:
        sys.stderr.write("Please supply a configuration file at /etc/dd-agent/%s or in the directory where the agent is currently deployed.\n" % DATADOG_CONF)
        sys.exit(3)
    
    # Core config
    agentConfig['ddUrl'] = config.get('Main', 'dd_url')
    if agentConfig['ddUrl'].endswith('/'):
        agentConfig['ddUrl'] = agentConfig['ddUrl'][:-1]
    agentConfig['agentKey'] = config.get('Main', 'agent_key')
    agentConfig['apiKey'] = config.get('Main', 'api_key')
    if os.path.exists('/var/log/dd-agent/'):
        agentConfig['tmpDirectory'] = '/var/log/dd-agent/'
    else:
        agentConfig['tmpDirectory'] = '/tmp/' # default which may be overriden in the config later
    agentConfig['pidfileDirectory'] = agentConfig['tmpDirectory']

    agentConfig['debugMode'] = config.get('Main', 'debug_mode')
    # translate yes into True, the rest into False
    if agentConfig['debugMode'].lower() == 'yes':
        agentConfig['debugMode'] = True
    else:
        agentConfig['debugMode'] = False
    
    # Optional config
    # Also do not need to be present in the config file (case 28326).
    if config.has_option('Main', 'apache_status_url'):
        agentConfig['apacheStatusUrl'] = config.get('Main', 'apache_status_url')
        
    if config.has_option('Main', 'mysql_server'):
        agentConfig['MySQLServer'] = config.get('Main', 'mysql_server')
        
    if config.has_option('Main', 'mysql_user'):
        agentConfig['MySQLUser'] = config.get('Main', 'mysql_user')
        
    if config.has_option('Main', 'mysql_pass'):
        agentConfig['MySQLPass'] = config.get('Main', 'mysql_pass')
    
    if config.has_option('Main', 'nginx_status_url'):   
        agentConfig['nginxStatusUrl'] = config.get('Main', 'nginx_status_url')

    if config.has_option('Main', 'tmp_directory'):
        agentConfig['tmpDirectory'] = config.get('Main', 'tmp_directory')

    if config.has_option('Main', 'pidfile_directory'):
        agentConfig['pidfileDirectory'] = config.get('Main', 'pidfile_directory')
        
    if config.has_option('Main', 'plugin_directory'):
        agentConfig['pluginDirectory'] = config.get('Main', 'plugin_directory')

    if config.has_option('Main', 'rabbitmq_status_url'):
        agentConfig['rabbitMQStatusUrl'] = config.get('Main', 'rabbitmq_status_url')

    if config.has_option('Main', 'rabbitmq_user'):
        agentConfig['rabbitMQUser'] = config.get('Main', 'rabbitmq_user')

    if config.has_option('Main', 'rabbitmq_pass'):
        agentConfig['rabbitMQPass'] = config.get('Main', 'rabbitmq_pass')

    if config.has_option('Main', 'mongodb_server'):
        agentConfig['MongoDBServer'] = config.get('Main', 'mongodb_server')

    if config.has_option('Main', 'couchdb_server'):
        agentConfig['CouchDBServer'] = config.get('Main', 'couchdb_server')

    if config.has_option('Main', 'hudson_home'):
        agentConfig['hudson_home'] = config.get('Main', 'hudson_home')

    if config.has_option('Main', 'nagios_log'):
        agentConfig['nagios_log'] = config.get('Main', 'nagios_log')

    if config.has_option('Main', 'ganglia_host'):
        agentConfig['ganglia_host'] = config.get('Main', 'ganglia_host')

    if config.has_option('Main', 'ganglia_port'):
        agentConfig['ganglia_port'] = config.get('Main', 'ganglia_port')

    if config.has_option('datadog', 'rollup_etl_logs'):
        agentConfig['has_datadog'] = True
        agentConfig['datadog_etl_rollup_logs'] = config.get('datadog', 'rollup_etl_logs')


except ConfigParser.NoSectionError, e:
    sys.stderr.write('Config file not found or incorrectly formatted.\n')
    sys.exit(2)
    
except ConfigParser.ParsingError, e:
    sys.stderr.write('Config file not found or incorrectly formatted.\n')
    sys.exit(2)
    
except ConfigParser.NoOptionError, e:
    sys.stderr.write('There are some items missing from your config file, but nothing fatal [%s]' % e)
    
if 'apacheStatusUrl' in agentConfig and agentConfig['apacheStatusUrl'] == None:
    sys.stderr.write('You must provide a config value for apache_status_url. If you do not wish to use Apache monitoring, leave it as its default value - http://www.example.com/server-status/?auto.\n')
    sys.exit(2) 

if 'nginxStatusUrl' in agentConfig and agentConfig['nginxStatusUrl'] == None:
    sys.stderr.write('You must provide a config value for nginx_status_url. If you do not wish to use Nginx monitoring, leave it as its default value - http://www.example.com/nginx_status.\n')
    sys.exit(2)

if 'MySQLServer' in agentConfig and agentConfig['MySQLServer'] != '' and 'MySQLUser' in agentConfig and agentConfig['MySQLUser'] != '' and 'MySQLPass' in agentConfig:
    try:
        import MySQLdb
    except ImportError:
        sys.stderr.write('You have configured MySQL for monitoring, but the MySQLdb module is not installed. For more info, see: http://help.datadoghq.com.\n')
        sys.exit(2)

if 'MongoDBServer' in agentConfig and agentConfig['MongoDBServer'] != '':
    try:
        import pymongo
    except ImportError:
        sys.stderr.write('You have configured MongoDB for monitoring, but the pymongo module is not installed.\n')
        sys.exit(2)

for section in config.sections():
    rawConfig[section] = {}
    
    for option in config.options(section):
        rawConfig[section][option] = config.get(section, option)

# Override the generic daemon class to run our checks
class agent(Daemon):    
    
    def run(self):  
        agentLogger = logging.getLogger('agent')
        
        agentLogger.debug('Collecting basic system stats')
        
        # Get some basic system stats to post back for development/testing
        import platform
        systemStats = {'machine': platform.machine(), 'platform': sys.platform, 'processor': platform.processor(), 'pythonV': platform.python_version(), 'cpuCores': self.cpuCores()}
        
        if sys.platform == 'linux2':
            systemStats['nixV'] = platform.dist()
            
        elif sys.platform == 'darwin':
            systemStats['macV'] = platform.mac_ver()
            
        elif sys.platform.find('freebsd') != -1:
            version = platform.uname()[2]
            systemStats['fbsdV'] = ('freebsd', version, '') # no codename for FreeBSD
        
        agentLogger.debug('System: ' + str(systemStats))
                        
        agentLogger.debug('Creating checks instance')
        
        # Checks instance
        c = checks(agentConfig, rawConfig)
        
        # Schedule the checks
        agentLogger.debug('Scheduling checks every ' + str(agentConfig['checkFreq']) + ' seconds')
        s = sched.scheduler(time.time, time.sleep)
        c.doChecks(s, True, systemStats) # start immediately (case 28315)
        s.run()
        
    def cpuCores(self):
        if sys.platform == 'linux2':
            grep = subprocess.Popen(['grep', 'model name', '/proc/cpuinfo'], stdout=subprocess.PIPE, close_fds=True)
            wc = subprocess.Popen(['wc', '-l'], stdin=grep.stdout, stdout=subprocess.PIPE, close_fds=True)
            output = wc.communicate()[0]
            return int(output)
            
        if sys.platform == 'darwin':
            output = subprocess.Popen(['sysctl', 'hw.ncpu'], stdout=subprocess.PIPE, close_fds=True).communicate()[0].split(': ')[1]
            return int(output)

# Control of daemon     
if __name__ == '__main__':  
    # Logging
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
    
    argLen = len(sys.argv)
    
    if argLen in (3, 4): # needs to accept case when --clean is passed
        if sys.argv[2] == 'init':
            # This path added for newer Linux packages which run under
            # a separate dd-agent user account.
            if os.path.exists('/var/run/dd-agent/'):
                pidFile = '/var/run/dd-agent/dd-agent.pid'
            else:
                pidFile = '/var/run/dd-agent.pid'
            
    else:
        pidFile = os.path.join(agentConfig['pidfileDirectory'], 'dd-agent.pid')
    
    if argLen == 4 and sys.argv[3] == '--clean':
        mainLogger.debug('Agent called with --clean option, removing .pid')
        try:
            os.remove(pidFile)
        except OSError:
            # Did not find pid file
            pass
    
    # Daemon instance from agent class
    daemon = agent(pidFile)
    
    # Control options
    if argLen == 2 or argLen == 3 or argLen == 4:
        if 'start' == sys.argv[1]:
            mainLogger.debug('Start daemon')
            daemon.start()
            
        elif 'stop' == sys.argv[1]:
            mainLogger.debug('Stop daemon')
            daemon.stop()
            
        elif 'restart' == sys.argv[1]:
            mainLogger.debug('Restart daemon')
            daemon.restart()
            
        elif 'foreground' == sys.argv[1]:
            mainLogger.debug('Running in foreground')
            daemon.run()
            
        elif 'status' == sys.argv[1]:
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
        sys.stderr.write('Usage: %s start|stop|restart|status' % sys.argv[0])
        sys.exit(2)
