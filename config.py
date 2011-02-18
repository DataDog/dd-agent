import ConfigParser
import os
import platform
import subprocess
import sys
from optparse import OptionParser, Values

# CONSTANTS
DATADOG_CONF = "datadog.conf"

def get_parsed_args():
    parser = OptionParser()
    parser.add_option('-d', '--dd_url', action='store', default=None, 
                        dest='dd_url')
    parser.add_option('-c', '--clean', action='store_true', default=False, 
                        dest='clean')
    try:
        options, args = parser.parse_args()
    except SystemExit:
        options, args = Values({'dd_url': None, 'clean': False}), [] # Ignore parse errors
    return options, args

def get_version():
    return "1.9.2"

def get_config():
    options, args = get_parsed_args()

    # General config
    agentConfig = {}
    agentConfig['debugMode'] = False
    agentConfig['checkFreq'] = 60
    agentConfig['version'] = get_version()

    rawConfig = {}

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
        if options.dd_url:
            agentConfig['ddUrl'] = options.dd_url
        else:
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
        
        if config.has_option('Main', 'check_freq'):
            agentConfig['checkFreq'] = int(config.get('Main', 'check_freq'))
        
        # Optional config
        # Also do not need to be present in the config file (case 28326).
        # FIXME not the prettiest code ever...
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

        # Cassandra config
        if config.has_option('Main', 'cassandra_nodetool'):
            agentConfig['cassandra_nodetool'] = config.get('Main', 'cassandra_nodetool')
        if config.has_option('Main', 'cassandra_host'):
            agentConfig['cassandra_host'] = config.get('Main', 'cassandra_host')
        if config.has_option('Main', 'cassandra_nodetool'):
            agentConfig['cassandra_port'] = config.get('Main', 'cassandra_port')

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
    
    return agentConfig, rawConfig


def get_system_stats():
    systemStats = {
        'machine': platform.machine(), 
        'platform': sys.platform, 
        'processor': platform.processor(), 
        'pythonV': platform.python_version()
    }
    
    if sys.platform == 'linux2':
        grep = subprocess.Popen(['grep', 'model name', '/proc/cpuinfo'], stdout=subprocess.PIPE, close_fds=True)
        wc = subprocess.Popen(['wc', '-l'], stdin=grep.stdout, stdout=subprocess.PIPE, close_fds=True)
        systemStats['cpuCores'] = int(wc.communicate()[0])
        
    if sys.platform == 'darwin':
        systemStats['cpuCores'] = int(subprocess.Popen(['sysctl', 'hw.ncpu'], stdout=subprocess.PIPE, close_fds=True).communicate()[0].split(': ')[1])

    if sys.platform == 'linux2':
        systemStats['nixV'] = platform.dist()
        
    elif sys.platform == 'darwin':
        systemStats['macV'] = platform.mac_ver()
        
    elif sys.platform.find('freebsd') != -1:
        version = platform.uname()[2]
        systemStats['fbsdV'] = ('freebsd', version, '') # no codename for FreeBSD
        
    return systemStats
    
    
