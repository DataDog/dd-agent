import ConfigParser
import os
import logging
import logging.config
import platform
import string
import subprocess
import sys
from optparse import OptionParser, Values
from cStringIO import StringIO

# CONSTANTS
DATADOG_CONF = "datadog.conf"
DEFAULT_CHECK_FREQUENCY = 15 # seconds

def get_parsed_args():
    parser = OptionParser()
    parser.add_option('-d', '--dd_url', action='store', default=None,
                        dest='dd_url')
    parser.add_option('-c', '--clean', action='store_true', default=False,
                        dest='clean')
    parser.add_option('-u', '--use-local-forwarder', action='store_true',
                        default=False,dest='use_forwarder')
    try:
        options, args = parser.parse_args()
    except SystemExit:
        options, args = Values({'dd_url': None, 'clean': False, 'use_forwarder':False}), [] # Ignore parse errors
    return options, args

def get_version():
    return "3.0.3"

def skip_leading_wsp(f):
    "Works on a file, returns a file-like object"
    return StringIO("\n".join(map(string.strip, f.readlines())))

def initialize_logging(config_path):
    try:
        logging.config.fileConfig(config_path)
    except Exception, e:
        sys.stderr.write("Couldn't initialize logging: %s" % str(e))
    

def get_config_path(cfg_path=None):
    # Find the right config file
    path = os.path.realpath(__file__)
    path = os.path.dirname(path)

    config_path = None
    if cfg_path is not None and os.path.exists(cfg_path):
        config_path = cfg_path
    elif os.path.exists(os.path.join('/etc/dd-agent', DATADOG_CONF)):
        config_path = os.path.join('/etc/dd-agent', DATADOG_CONF)
    elif os.path.exists(os.path.join(path, DATADOG_CONF)):
        config_path = os.path.join(path, DATADOG_CONF)
    else:
        sys.stderr.write("Please supply a configuration file at /etc/dd-agent/%s or in the directory where the agent is currently deployed.\n" % DATADOG_CONF)
        sys.exit(3)
    return config_path


def get_config(parse_args = True, cfg_path=None, init_logging=False):
    if parse_args:
        options, args = get_parsed_args()
    else:
        options = None
        args = None

    # General config
    agentConfig = {}
    agentConfig['debug_mode'] = False
    # not really a frequency, but the time to sleep between checks
    agentConfig['check_freq'] = DEFAULT_CHECK_FREQUENCY
    agentConfig['version'] = get_version()

    # Config handling
    try:
        # Find the right config file
        path = os.path.realpath(__file__)
        path = os.path.dirname(path)

        config_path = get_config_path(cfg_path)
        config = ConfigParser.ConfigParser()
        config.readfp(skip_leading_wsp(open(config_path)))

        if init_logging:
            initialize_logging(config_path)

        #
        # Core config
        #

        # Where to send the data
        if options is not None and options.use_forwarder:
            listen_port = 17123
            if config.has_option('Main','listen_port'):
                listen_port = config.get('Main','listen_port')
            agentConfig['dd_url'] = "http://localhost:" + str(listen_port)
        elif options is not None and options.dd_url:
            agentConfig['dd_url'] = options.dd_url
        else:
            agentConfig['dd_url'] = config.get('Main', 'dd_url')
        if agentConfig['dd_url'].endswith('/'):
            agentConfig['dd_url'] = agentConfig['dd_url'][:-1]

        # Which API key to use
        agentConfig['api_key'] = config.get('Main', 'api_key')

        # Debug mode
        agentConfig['debug_mode'] = config.get('Main', 'debug_mode').lower() in ("yes", "true")

        if config.has_option('Main', 'use_ec2_instance_id'):
            use_ec2_instance_id = config.get('Main', 'use_ec2_instance_id')
            # translate yes into True, the rest into False
            agentConfig['use_ec2_instance_id'] = (use_ec2_instance_id.lower() == 'yes')
        else:
            agentConfig['use_ec2_instance_id'] = False

        if config.has_option('Main', 'check_freq'):
            try:
                agentConfig['check_freq'] = int(config.get('Main', 'check_freq'))
            except:
                agentConfig['check_freq'] = DEFAULT_CHECK_FREQUENCY

        if config.has_option('Main','hostname'):
            agentConfig['hostname'] = config.get('Main','hostname')
        else:
            agentConfig['hostname'] = None

        if config.has_option('Main','tags'):
            agentConfig['tags'] = config.get('Main','tags')
        else:
            agentConfig['tags'] = None

        # Disable Watchdog (optionally)
        agentConfig['watchdog'] = True
        if config.has_option('Main', 'watchdog'):
            if config.get('Main', 'watchdog').lower() in ('no', 'false'):
                agentConfig['watchdog'] = False

        # port we listen on (overriden via command line)
        if config.has_option('Main','port'):
            agentConfig['listen_port'] = int(config.get('Main','port'))
        else:
            agentConfig['listen_port'] = None

        # Optional graphite listener
        if config.has_option('Main','graphite_listen_port'):
            agentConfig['graphite_listen_port'] = int(config.get('Main','graphite_listen_port'))
        else:
            agentConfig['graphite_listen_port'] = None

        # Dogstatsd config
        dogstatsd_defaults = {
            'dogstatsd_port' : 8125,
            'dogstatsd_target' : 'http://localhost:17123',
            'dogstatsd_interval' : 10
        }
        for key, value in dogstatsd_defaults.iteritems():
            if config.has_option('Main', key):
                agentConfig[key] = config.get('Main', key)
            else:
                agentConfig[key] = value

        # Optional config
        # FIXME not the prettiest code ever...
        if config.has_option('Main', 'use_mount'):
            agentConfig['use_mount'] = config.get('Main', 'use_mount').lower() in ("yes", "true", "1")

        if config.has_option('Main', 'apache_status_url'):
            agentConfig['apache_status_url'] = config.get('Main', 'apache_status_url')

        if config.has_option('Main', 'mysql_server'):
            agentConfig['mysql_server'] = config.get('Main', 'mysql_server')

        if config.has_option('Main', 'mysql_user'):
            agentConfig['mysql_user'] = config.get('Main', 'mysql_user')

        if config.has_option('Main', 'mysql_pass'):
            agentConfig['mysql_pass'] = config.get('Main', 'mysql_pass')

        if config.has_option('Main', 'postgresql_server'):
            agentConfig['postgresql_server'] = config.get('Main','postgresql_server')

        if config.has_option('Main', 'postgresql_port'):
            agentConfig['postgresql_port'] = config.get('Main','postgresql_port')

        if config.has_option('Main', 'postgresql_user'):
            agentConfig['postgresql_user'] = config.get('Main','postgresql_user')

        if config.has_option('Main', 'postgresql_pass'):
            agentConfig['postgresql_pass'] = config.get('Main','postgresql_pass')

        if config.has_option('Main', 'nginx_status_url'):
            agentConfig['nginx_status_url'] = config.get('Main', 'nginx_status_url')

        if config.has_option('Main', 'plugin_directory'):
            agentConfig['plugin_directory'] = config.get('Main', 'plugin_directory')

        if config.has_option('Main', 'rabbitmq_status_url'):
            agentConfig['rabbitmq_status_url'] = config.get('Main', 'rabbitmq_status_url')

        if config.has_option('Main', 'rabbitmq_user'):
            agentConfig['rabbitmq_user'] = config.get('Main', 'rabbitmq_user')

        if config.has_option('Main', 'rabbitmq_pass'):
            agentConfig['rabbitmq_pass'] = config.get('Main', 'rabbitmq_pass')

        if config.has_option('Main', 'mongodb_server'):
            agentConfig['mongodb_server'] = config.get('Main', 'mongodb_server')

        if config.has_option('Main', 'couchdb_server'):
            agentConfig['couchdb_server'] = config.get('Main', 'couchdb_server')

        if config.has_option('Main', 'hudson_home'):
            agentConfig['hudson_home'] = config.get('Main', 'hudson_home')

        if config.has_option('Main', 'nagios_log'):
            agentConfig['nagios_log'] = config.get('Main', 'nagios_log')

        if config.has_option('Main', 'ganglia_host'):
            agentConfig['ganglia_host'] = config.get('Main', 'ganglia_host')

        if config.has_option('Main', 'ganglia_port'):
            agentConfig['ganglia_port'] = config.get('Main', 'ganglia_port')

        if config.has_option('datadog', 'ddforwarder_log'):
            agentConfig['has_datadog'] = True
            agentConfig['ddforwarder_log'] = config.get('datadog', 'ddforwarder_log')

        # Cassandra config
        if config.has_option('Main', 'cassandra_nodetool'):
            agentConfig['cassandra_nodetool'] = config.get('Main', 'cassandra_nodetool')
        if config.has_option('Main', 'cassandra_host'):
            agentConfig['cassandra_host'] = config.get('Main', 'cassandra_host')
        if config.has_option('Main', 'cassandra_nodetool'):
            agentConfig['cassandra_port'] = config.get('Main', 'cassandra_port')

        # Java config
        if config.has_option('Main', 'jvm_jmx_server'):
            agentConfig['jvm_jmx_server'] = config.get('Main', 'jvm_jmx_server')
        if config.has_option('Main', 'jvm_jmx_user'):
            agentConfig['jvm_jmx_user'] = config.get('Main', 'jvm_jmx_user')
        if config.has_option('Main', 'jvm_jmx_pass'):
            agentConfig['jvm_jmx_pass'] = config.get('Main', 'jvm_jmx_pass')
        if config.has_option('Main', 'jvm_jmx_name'):
            agentConfig['jvm_jmx_name'] = config.get('Main', 'jvm_jmx_name')

        # Tomcat config
        if config.has_option('Main', 'tomcat_jmx_server'):
            agentConfig['tomcat_jmx_server'] = config.get('Main', 'tomcat_jmx_server')
        if config.has_option('Main', 'tomcat_jmx_user'):
            agentConfig['tomcat_jmx_user'] = config.get('Main', 'tomcat_jmx_user')
        if config.has_option('Main', 'tomcat_jmx_pass'):
            agentConfig['tomcat_jmx_pass'] = config.get('Main', 'tomcat_jmx_pass')

        # ActiveMQ config
        if config.has_option('Main', 'activemq_jmx_server'):
            agentConfig['activemq_jmx_server'] = config.get('Main', 'activemq_jmx_server')
        if config.has_option('Main', 'activemq_jmx_user'):
            agentConfig['activemq_jmx_user'] = config.get('Main', 'activemq_jmx_user')
        if config.has_option('Main', 'activemq_jmx_pass'):
            agentConfig['activemq_jmx_pass'] = config.get('Main', 'activemq_jmx_pass')

        # Solr config
        if config.has_option('Main', 'solr_jmx_server'):
            agentConfig['solr_jmx_server'] = config.get('Main', 'solr_jmx_server')
        if config.has_option('Main', 'solr_jmx_user'):
            agentConfig['solr_jmx_user'] = config.get('Main', 'solr_jmx_user')
        if config.has_option('Main', 'solr_jmx_pass'):
            agentConfig['solr_jmx_pass'] = config.get('Main', 'solr_jmx_pass')

        # Memcache config
        if config.has_option("Main", "memcache_server"):
            agentConfig["memcache_server"] = config.get("Main", "memcache_server")
        if config.has_option("Main", "memcache_port"):
            agentConfig["memcache_port"] = config.get("Main", "memcache_port")

        # Dogstream config
        if config.has_option("Main", "dogstream_log"):
            # Older version, single log support
            log_path = config.get("Main", "dogstream_log")
            if config.has_option("Main", "dogstream_line_parser"):
                agentConfig["dogstreams"] = ':'.join([log_path, config.get("Main", "dogstream_line_parser")])
            else:
                agentConfig["dogstreams"] = log_path

        elif config.has_option("Main", "dogstreams"):
            agentConfig["dogstreams"] = config.get("Main", "dogstreams")

        if config.has_option("Main", "nagios_perf_cfg"):
            agentConfig["nagios_perf_cfg"] = config.get("Main", "nagios_perf_cfg")

        if config.has_option('Main', 'cacti_mysql_server'):
            agentConfig['cacti_mysql_server'] = config.get('Main', 'cacti_mysql_server')
        if config.has_option('Main', 'cacti_mysql_user'):
            agentConfig['cacti_mysql_user'] = config.get('Main', 'cacti_mysql_user')
        if config.has_option('Main', 'cacti_mysql_pass'):
            agentConfig['cacti_mysql_pass'] = config.get('Main', 'cacti_mysql_pass')
        if config.has_option('Main', 'cacti_rrd_path'):
            agentConfig['cacti_rrd_path'] = config.get('Main', 'cacti_rrd_path')
        if config.has_option('Main', 'cacti_rrd_whitelist'):
            agentConfig['cacti_rrd_whitelist'] = config.get('Main', 'cacti_rrd_whitelist')

        # Varnish
        if config.has_option('Main', 'varnishstat'):
            agentConfig['varnishstat'] = config.get('Main', 'varnishstat')

        # Redis
        if config.has_option('Main', 'redis_urls'):
            agentConfig['redis_urls'] = config.get('Main', 'redis_urls')

        # Elasticsearch
        if config.has_option('Main','elasticsearch'):
            agentConfig['elasticsearch'] = config.get('Main','elasticsearch')


    except ConfigParser.NoSectionError, e:
        sys.stderr.write('Config file not found or incorrectly formatted.\n')
        sys.exit(2)

    except ConfigParser.ParsingError, e:
        sys.stderr.write('Config file not found or incorrectly formatted.\n')
        sys.exit(2)

    except ConfigParser.NoOptionError, e:
        sys.stderr.write('There are some items missing from your config file, but nothing fatal [%s]' % e)

    if 'apache_status_url' in agentConfig and agentConfig['apache_status_url'] == None:
        sys.stderr.write('You must provide a config value for apache_status_url. If you do not wish to use Apache monitoring, leave it as its default value - http://www.example.com/server-status/?auto.\n')
        sys.exit(2)

    if 'nginx_status_url' in agentConfig and agentConfig['nginx_status_url'] == None:
        sys.stderr.write('You must provide a config value for nginx_status_url. If you do not wish to use Nginx monitoring, leave it as its default value - http://www.example.com/nginx_status.\n')
        sys.exit(2)

    if 'mysql_server' in agentConfig and agentConfig['mysql_server'] != '' and 'mysql_user' in agentConfig and agentConfig['mysql_user'] != '' and 'mysql_pass' in agentConfig:
        try:
            import MySQLdb
        except ImportError:
            sys.stderr.write('You have configured MySQL for monitoring, but the MySQLdb module is not installed. For more info, see: http://help.datadoghq.com.\n')
            sys.exit(2)

    if 'mongodb_server' in agentConfig and agentConfig['mongodb_server'] != '':
        try:
            import pymongo
        except ImportError:
            sys.stderr.write('You have configured MongoDB for monitoring, but the pymongo module is not installed.\n')
            sys.exit(2)

    return agentConfig

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
