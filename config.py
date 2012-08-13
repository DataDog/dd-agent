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
DEFAULT_STATSD_FREQUENCY = 10 # seconds
PUP_STATSD_FREQUENCY = 2 # seconds

def get_parsed_args():
    parser = OptionParser()
    parser.add_option('-d', '--dd_url', action='store', default=None,
                        dest='dd_url')
    parser.add_option('-c', '--clean', action='store_true', default=False,
                        dest='clean')
    parser.add_option('-u', '--use-local-forwarder', action='store_true',
                        default=False,dest='use_forwarder')
    parser.add_option('-p', '--disable-pup', action='store_true', default=False,
                        dest="disable_pup")
    parser.add_option('-n', '--disable-dd', action='store_true', default=False,
                        dest="disable_dd")
    try:
        options, args = parser.parse_args()
    except SystemExit:
        options, args = Values({'dd_url': None, 
                                'clean': False, 
                                'use_forwarder':False,
                                'disable_pup':False,
                                'disable_dd':False}), [] # Ignore parse errors
    return options, args

def get_version():
    return "3.0.5"

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
    agentConfig = {
        'check_freq': DEFAULT_CHECK_FREQUENCY,
        'debug_mode': False,
        'dogstatsd_interval': DEFAULT_STATSD_FREQUENCY,
        'dogstatsd_port': 8125,
        'dogstatsd_target': 'http://localhost:17123',
        'graphite_listen_port': None,
        'hostname': None,
        'listen_port': None,
        'tags': None,
        'use_ec2_instance_id': False,
        'version': get_version(),
        'watchdog': True,
    }

    dogstatsd_interval = DEFAULT_STATSD_FREQUENCY

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


        # bulk import
        for option in config.options('Main'):
            agentConfig[option] = config.get('Main', option)

        #
        # Core config
        #

        if config.has_option('Main', 'use_dd'):
            agentConfig['use_dd'] = config.get('Main', 'use_dd').lower() in ("yes", "true")
        else:
            agentConfig['use_dd'] = True

        if options is not None and options.use_forwarder:
            listen_port = 17123
            if config.has_option('Main','listen_port'):
                listen_port = config.get('Main','listen_port')
            agentConfig['dd_url'] = "http://localhost:" + str(listen_port)
        elif options is not None and not options.disable_dd and options.dd_url:
            agentConfig['dd_url'] = options.dd_url
        else:
            agentConfig['dd_url'] = config.get('Main', 'dd_url')
        if agentConfig['dd_url'].endswith('/'):
            agentConfig['dd_url'] = agentConfig['dd_url'][:-1]
        
        # Whether also to send to Pup
        if config.has_option('Main', 'use_pup'):
            agentConfig['use_pup'] = config.get('Main', 'use_pup').lower() in ("yes", "true")
        else:
            agentConfig['use_pup'] = False

        if options is not None and options.disable_pup:
            agentConfig['use_pup'] = False
        elif agentConfig['use_pup']:
            if config.has_option('Main', 'pup_url'):
                agentConfig['pup_url'] = config.get('Main', 'pup_url')
            else:
                agentConfig['pup_url'] = 'http://localhost:17125'
   
        # Increases the frequency of statsd metrics when only sending to Pup
        if not agentConfig['use_dd'] and agentConfig['use_pup']:
            dogstatsd_interval = PUP_STATSD_FREQUENCY

        if not agentConfig['use_dd'] and not agentConfig['use_pup']:
            sys.stderr.write("Please specify at least one endpoint to send metrics to. This can be done in datadog.conf.")
            exit(2)

        # Which API key to use
        agentConfig['api_key'] = config.get('Main', 'api_key')

        # Debug mode
        agentConfig['debug_mode'] = config.get('Main', 'debug_mode').lower() in ("yes", "true")

        if config.has_option('Main', 'use_ec2_instance_id'):
            use_ec2_instance_id = config.get('Main', 'use_ec2_instance_id')
            # translate yes into True, the rest into False
            agentConfig['use_ec2_instance_id'] = (use_ec2_instance_id.lower() == 'yes')

        if config.has_option('Main', 'check_freq'):
            try:
                agentConfig['check_freq'] = int(config.get('Main', 'check_freq'))
            except:
                pass

        # Disable Watchdog (optionally)
        if config.has_option('Main', 'watchdog'):
            if config.get('Main', 'watchdog').lower() in ('no', 'false'):
                agentConfig['watchdog'] = False

        # Optional graphite listener
        if config.has_option('Main','graphite_listen_port'):
            agentConfig['graphite_listen_port'] = int(config.get('Main','graphite_listen_port'))
        else:
            agentConfig['graphite_listen_port'] = None

        # Dogstatsd config
        dogstatsd_defaults = {
            'dogstatsd_port' : 8125,
            'dogstatsd_target' : 'http://localhost:17123',
            'dogstatsd_interval' : dogstatsd_interval
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

        if config.has_option('datadog', 'ddforwarder_log'):
            agentConfig['has_datadog'] = True

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
