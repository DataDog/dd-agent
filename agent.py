#!/usr/bin/python
'''
    Server Density
    www.serverdensity.com
    ----
    A web based server resource monitoring application

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
'''

# General config
agentConfig = {}
agentConfig['debugMode'] = False
agentConfig['checkFreq'] = 5

agentConfig['version'] = '1.9.0'

rawConfig = {}

# Core modules
import ConfigParser
import logging
import os
import re
import sched
import sys
import time

# Check we're not using an old version of Python. We need 2.4 above because some modules (like subprocess)
# were only introduced in 2.4.
if int(sys.version_info[1]) <= 3:
    print 'You are using an outdated version of Python. Please update to v2.4 or above (v3 is not supported). For newer OSs, you can update Python without affecting your system install. See http://blog.boxedice.com/2010/01/19/updating-python-on-rhelcentos/ If you are running RHEl 4 / CentOS 4 then you will need to compile Python manually.'
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
    if os.path.exists('/etc/dd-agent/config.cfg'):
        config.read('/etc/dd-agent/config.cfg')
    elif os.path.exists('/etc/sd-agent/config.cfg'):
        config.read('/etc/sd-agent/config.cfg')
    elif os.path.exists(path + '/config.cfg'):
        config.read(path + '/config.cfg')
    else:
        #No config file, exit gracegully
        print "Config file not found, not starting"
        sys.exit(0)
    
    # Core config
    agentConfig['sdUrl'] = config.get('Main', 'sd_url')
    if agentConfig['sdUrl'].endswith('/'):
        agentConfig['sdUrl'] = agentConfig['sdUrl'][:-1]
    agentConfig['agentKey'] = config.get('Main', 'agent_key')
    agentConfig['apiKey'] = config.get('Main', 'api_key')
    if os.path.exists('/var/log/sd-agent/'):
        agentConfig['tmpDirectory'] = '/var/log/sd-agent/'
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

except ConfigParser.NoSectionError, e:
    print 'Config file not found or incorrectly formatted'
    sys.exit(2)
    
except ConfigParser.ParsingError, e:
    print 'Config file not found or incorrectly formatted'
    sys.exit(2)
    
except ConfigParser.NoOptionError, e:
    print 'There are some items missing from your config file, but nothing fatal', e
    
# Check apache_status_url is not empty (case 27073)
if 'apacheStatusUrl' in agentConfig and agentConfig['apacheStatusUrl'] == None:
    print 'You must provide a config value for apache_status_url. If you do not wish to use Apache monitoring, leave it as its default value - http://www.example.com/server-status/?auto'
    sys.exit(2) 

if 'nginxStatusUrl' in agentConfig and agentConfig['nginxStatusUrl'] == None:
    print 'You must provide a config value for nginx_status_url. If you do not wish to use Nginx monitoring, leave it as its default value - http://www.example.com/nginx_status'
    sys.exit(2)

if 'MySQLServer' in agentConfig and agentConfig['MySQLServer'] != '' and 'MySQLUser' in agentConfig and agentConfig['MySQLUser'] != '' and 'MySQLPass' in agentConfig:
    try:
        import MySQLdb
    except ImportError:
        print 'You have configured MySQL for monitoring, but the MySQLdb module is not installed.  For more info, see: http://www.serverdensity.com/docs/agent/mysqlstatus/'
        sys.exit(2)

if 'MongoDBServer' in agentConfig and agentConfig['MongoDBServer'] != '':
    try:
        import pymongo
    except ImportError:
        print 'You have configured MongoDB for monitoring, but the pymongo module is not installed.  For more info, see: http://www.serverdensity.com/docs/agent/mongodbstatus/'
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
        logFile = os.path.join(agentConfig['tmpDirectory'], 'sd-agent.log')
        logging.basicConfig(filename=logFile, filemode='w', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        from logging.handlers import SysLogHandler
        rootLog = logging.getLogger()
        rootLog.setLevel(logging.INFO)
        handler = SysLogHandler(address="/dev/log",facility=SysLogHandler.LOG_DAEMON)
        formatter = logging.Formatter("dd-agent - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        rootLog.addHandler(handler) 

    mainLogger = logging.getLogger('main')      
    mainLogger.debug('Agent called')
    mainLogger.debug('Agent version: ' + agentConfig['version'])
    
    argLen = len(sys.argv)
    
    if argLen == 3 or argLen == 4: # needs to accept case when --clean is passed
        if sys.argv[2] == 'init':
            # This path added for newer Linux packages which run under
            # a separate sd-agent user account.
            if os.path.exists('/var/run/sd-agent/'):
                pidFile = '/var/run/sd-agent/sd-agent.pid'
            else:
                pidFile = '/var/run/sd-agent.pid'
            
    else:
        pidFile = os.path.join(agentConfig['pidfileDirectory'], 'sd-agent.pid')
    
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
                print 'sd-agent is running as pid %s.' % pid
            else:
                print 'sd-agent is not running.'

        else:
            print 'Unknown command'
            sys.exit(2)
            
        sys.exit(0)
        
    else:
        print 'usage: %s start|stop|restart|status' % sys.argv[0]
        sys.exit(2)
