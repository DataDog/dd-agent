import ConfigParser
import os
import logging
import logging.config
import platform
import string
import subprocess
import sys
import glob
import inspect
from optparse import OptionParser, Values
from cStringIO import StringIO
from util import getOS

# CONSTANTS
DATADOG_CONF = "datadog.conf"
DEFAULT_CHECK_FREQUENCY = 15 # seconds
DEFAULT_STATSD_FREQUENCY = 10 # seconds
PUP_STATSD_FREQUENCY = 2 # seconds

class PathNotFound(Exception): pass

def get_parsed_args():
    parser = OptionParser()
    parser.add_option('-d', '--dd_url', action='store', default=None,
                        dest='dd_url')
    parser.add_option('-c', '--clean', action='store_true', default=False,
                        dest='clean')
    parser.add_option('-u', '--use-local-forwarder', action='store_true',
                        default=False,dest='use_forwarder')
    parser.add_option('-n', '--disable-dd', action='store_true', default=False,
                        dest="disable_dd")
    try:
        options, args = parser.parse_args()
    except SystemExit:
        options, args = Values({'dd_url': None,
                                'clean': False,
                                'use_forwarder':False,
                                'disable_dd':False}), [] # Ignore parse errors
    return options, args

def get_version():
    return "3.3.0"

def skip_leading_wsp(f):
    "Works on a file, returns a file-like object"
    return StringIO("\n".join(map(string.strip, f.readlines())))

def initialize_logging(config_path, os_name=None):
    try:
        logging.config.fileConfig(config_path)
    except Exception, e:
        sys.stderr.write("Couldn't initialize logging: %s" % str(e))

def _windows_commondata_path():
    ''' Return the common appdata path, using ctypes 
    From: http://stackoverflow.com/questions/626796/how-do-i-find-the-windows-common-application-data-folder-using-python
    '''
    import ctypes
    from ctypes import wintypes, windll

    CSIDL_COMMON_APPDATA = 35

    _SHGetFolderPath = windll.shell32.SHGetFolderPathW
    _SHGetFolderPath.argtypes = [wintypes.HWND,
                                ctypes.c_int,
                                wintypes.HANDLE,
                                wintypes.DWORD, wintypes.LPCWSTR]

    path_buf = wintypes.create_unicode_buffer(wintypes.MAX_PATH)
    result = _SHGetFolderPath(0, CSIDL_COMMON_APPDATA, 0, 0, path_buf)
    return path_buf.value


def _windows_config_path():
    common_data = _windows_commondata_path()
    path = os.path.join(common_data, 'Datadog', DATADOG_CONF)
    if os.path.exists(path):
        return path
    raise PathNotFound(path)

def _windows_confd_path():
    common_data = _windows_commondata_path()
    path = os.path.join(common_data, 'Datadog', 'conf.d')
    if os.path.exists(path):
        return path
    raise PathNotFound(path)

def _windows_checksd_path():
    path = os.path.join(os.environ['PROGRAMFILES'], 'Datadog', 'Datadog Agent',
        'checks.d')
    if os.path.exists(path):
        return path
    raise PathNotFound(path)

def _unix_config_path():
    path = os.path.join('/etc/dd-agent', DATADOG_CONF)
    if os.path.exists(path):
        return path
    raise PathNotFound(path)

def _unix_confd_path():
    path = os.path.join('/etc/dd-agent', 'conf.d')
    if os.path.exists(path):
        return path
    raise PathNotFound(path)

def _is_affirmative(s):
    return s.lower() in ('yes', 'true')

def get_config_path(cfg_path=None, os_name=None):
    # Check if there's an override and if it exists
    if cfg_path is not None and os.path.exists(cfg_path):
        return cfg_path

    # Check for an OS-specific path, continue on not-found exceptions
    exc = None
    if os_name == 'windows':
        try:
            return _windows_config_path()
        except PathNotFound, e:
            exc = e
    else:
        try:
            return _unix_config_path()
        except PathNotFound, e:
            exc = e

    # Check if there's a config stored in the current agent directory
    path = os.path.realpath(__file__)
    path = os.path.dirname(path)
    if os.path.exists(os.path.join(path, DATADOG_CONF)):
        return os.path.join(path, DATADOG_CONF)
    
    # If all searches fail, exit the agent with an error
    sys.stderr.write("Please supply a configuration file at %s or in the directory where the agent is currently deployed.\n" % exc.message)
    sys.exit(3)

def get_config(parse_args = True, cfg_path=None, init_logging=False, options=None):
    if parse_args:
        options, args = get_parsed_args()
    elif not options:
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
        'use_ec2_instance_id': False,  # DEPRECATED
        'version': get_version(),
        'watchdog': True,
    }

    dogstatsd_interval = DEFAULT_STATSD_FREQUENCY

    # Config handling
    try:
        # Find the right config file
        path = os.path.realpath(__file__)
        path = os.path.dirname(path)

        config_path = get_config_path(cfg_path, os_name=getOS())
        config = ConfigParser.ConfigParser()
        config.readfp(skip_leading_wsp(open(config_path)))

        if init_logging:
            initialize_logging(config_path, os_name=getOS())


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
            agentConfig['use_pup'] = True

        if agentConfig['use_pup']:
            if config.has_option('Main', 'pup_url'):
                agentConfig['pup_url'] = config.get('Main', 'pup_url')
            else:
                agentConfig['pup_url'] = 'http://localhost:17125'

            pup_port = 17125
            if config.has_option('Main', 'pup_port'):
                agentConfig['pup_port'] = int(config.get('Main', 'pup_port'))

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

        # DEPRECATED
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
            'dogstatsd_interval' : dogstatsd_interval,
        }
        for key, value in dogstatsd_defaults.iteritems():
            if config.has_option('Main', key):
                agentConfig[key] = config.get('Main', key)
            else:
                agentConfig[key] = value

        # optionally send dogstatsd data directly to the agent.
        if config.has_option('Main', 'dogstatsd_use_ddurl'):
            use_ddurl = _is_affirmative(config.get('Main', 'dogstatsd_use_ddurl'))
            if use_ddurl:
                agentConfig['dogstatsd_target'] = agentConfig['dd_url']

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

        if config.has_section('WMI'):
            agentConfig['WMI'] = {}
            for key, value in config.items('WMI'):
                agentConfig['WMI'][key] = value    

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

def set_win32_cert_path():
    ''' In order to use tornado.httpclient with the packaged .exe on Windows we
    need to override the default ceritifcate location which is based on the path
    to tornado and will give something like "C:\path\to\program.exe\tornado/cert-file".

    If pull request #379 is accepted (https://github.com/facebook/tornado/pull/379) we
    will be able to override this in a clean way. For now, we have to monkey patch
    tornado.httpclient._DEFAULT_CA_CERTS
    '''
    crt_path = os.path.join(os.environ['PROGRAMFILES'], 'Datadog', 'Datadog Agent',
        'ca-certificates.crt')
    import tornado.simple_httpclient
    tornado.simple_httpclient._DEFAULT_CA_CERTS = crt_path

def get_confd_path(osname):
    log = logging.getLogger('config')

    if osname == 'windows':
        try:
            return _windows_confd_path()
        except PathNotFound, e:
            exc = e
    else:
        try:
            return _unix_confd_path()
        except PathNotFound, e:
            exc = e

    cur_path = os.path.dirname(os.path.realpath(__file__))
    cur_path = os.path.join(cur_path, 'conf.d')

    if os.path.exists(cur_path):
        return cur_path

    log.error("No conf.d folder found at '%s' or in the directory where the agent is currently deployed.\n" % exc.message)
    sys.exit(3)

def get_checksd_path(osname):
    log = logging.getLogger('config')

    # Unix only will look up based on the current directory
    # because checks.d will hang with the other python modules
    cur_path = os.path.dirname(os.path.realpath(__file__))
    checksd_path = os.path.join(cur_path, 'checks.d')
    if os.path.exists(checksd_path):
        return checksd_path

    if osname == 'windows':
        try:
            return _windows_checksd_path()
        except PathNotFound, e:
            sys.stderr.write("No checks.d folder found in '%s'.\n" % e.message)

    log.error("No checks.d folder at '%s'.\n" % checksd_path)
    sys.exit(3)

def load_check_directory(agentConfig):
    ''' Return the checks from checks.d. Only checks that have a configuration
    file in conf.d will be returned. '''
    from util import yaml, yLoader
    from checks import AgentCheck

    checks = []

    log = logging.getLogger('checks')
    osname = getOS()
    checks_path = get_checksd_path(osname)
    confd_path = get_confd_path(osname)
    check_glob = os.path.join(checks_path, '*.py')

    # Update the python path before the import
    sys.path.append(checks_path)

    # For backwards-compatability with old style checks, we have to load every
    # checks.d module and check for a corresponding config OR check if the old
    # config will "activate" the check.
    #
    # Once old-style checks aren't supported, we'll just read the configs and
    # import the corresponding check module
    for check in glob.glob(check_glob):
        check_name = os.path.basename(check).split('.')[0]
        try:
            check_module = __import__(check_name)
        except:
            log.exception('Unable to import check module %s.py from checks.d' % check_name)
            continue

        check_class = None
        classes = inspect.getmembers(check_module, inspect.isclass)
        for name, clsmember in classes:
            if clsmember == AgentCheck:
                continue
            if issubclass(clsmember, AgentCheck):
                check_class = clsmember
                if AgentCheck in clsmember.__bases__:
                    continue
                else:
                    break

        if not check_class:
            log.error('No check class (inheriting from AgentCheck) foound in %s.py' % check_name)
            continue

        # Check if the config exists OR we match the old-style config
        conf_path = os.path.join(confd_path, '%s.yaml' % check_name)
        if os.path.exists(conf_path):
            f = open(conf_path)
            try:
                check_config = yaml.load(f.read(), Loader=yLoader)
                assert check_config is not None
                f.close()
            except:
                f.close()
                log.warn("Unable to parse yaml config in %s" % conf_path)
                continue
        elif hasattr(check_class, 'parse_agent_config'):
            # FIXME: Remove this check once all old-style checks are gone
            check_config = check_class.parse_agent_config(agentConfig)
            if not check_config:
                continue
        else:
            log.debug('No conf.d/%s.yaml found for checks.d/%s.py' % (check_name, check_name))
            continue

        # Look for the per-check config, which *must* exist
        if not check_config.get('instances'):
            log.error("Config %s is missing 'instances'" % conf_path)
            continue

        # Accept instances as a list, as a single dict, or as non-existant
        instances = check_config.get('instances', {})
        if type(instances) != type([]):
            instances = [instances]

        # Init all of the check's classes with
        init_config = check_config.get('init_config', {})
        init_config['instances_number'] = len(instances)
        check_class = check_class(check_name, init_config=init_config,
            agentConfig=agentConfig)

        # Add custom pythonpath(s) if available
        if 'pythonpath' in check_config:
            pythonpath = check_config['pythonpath']
            if not isinstance(pythonpath, list):
                pythonpath = [pythonpath]
            sys.path.extend(pythonpath)

        log.debug('Loaded check.d/%s.py' % check_name)
        checks.append({
            'name': check_name,
            'instances': check_config['instances'],
            'class': check_class
        })

    return checks
