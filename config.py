import ConfigParser
import os
import itertools
import logging
import logging.config
import logging.handlers
import platform
import string
import subprocess
import sys
import glob
import inspect
import tempfile
import traceback
import re
import imp
import socket
from socket import gaierror
from optparse import OptionParser, Values
from cStringIO import StringIO
from urlparse import urlparse

# project
from util import get_os, Platform, yLoader

# 3rd party
import yaml

# CONSTANTS
AGENT_VERSION = "5.4.0"
DATADOG_CONF = "datadog.conf"
DEFAULT_CHECK_FREQUENCY = 15   # seconds
LOGGING_MAX_BYTES = 5 * 1024 * 1024

log = logging.getLogger(__name__)

OLD_STYLE_PARAMETERS = [
    ('apache_status_url', "apache"),
    ('cacti_mysql_server' , "cacti"),
    ('couchdb_server', "couchdb"),
    ('elasticsearch', "elasticsearch"),
    ('haproxy_url', "haproxy"),
    ('hudson_home', "Jenkins"),
    ('memcache_', "memcached"),
    ('mongodb_server', "mongodb"),
    ('mysql_server', "mysql"),
    ('nginx_status_url', "nginx"),
    ('postgresql_server', "postgres"),
    ('redis_urls', "redis"),
    ('varnishstat', "varnish"),
    ('WMI', "WMI"),
]

NAGIOS_OLD_CONF_KEYS = [
    'nagios_log',
    'nagios_perf_cfg'
    ]

DEFAULT_CHECKS = ("network", "ntp")
LEGACY_DATADOG_URLS = [
    "app.datadoghq.com",
    "app.datad0g.com",
]

class PathNotFound(Exception):
    pass


def get_parsed_args():
    parser = OptionParser()
    parser.add_option('-A', '--autorestart', action='store_true', default=False,
                        dest='autorestart')
    parser.add_option('-d', '--dd_url', action='store', default=None,
                        dest='dd_url')
    parser.add_option('-c', '--clean', action='store_true', default=False,
                        dest='clean')
    parser.add_option('-u', '--use-local-forwarder', action='store_true',
                        default=False, dest='use_forwarder')
    parser.add_option('-n', '--disable-dd', action='store_true', default=False,
                        dest="disable_dd")
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                        dest='verbose',
                      help='Print out stacktraces for errors in checks')

    try:
        options, args = parser.parse_args()
    except SystemExit:
        # Ignore parse errors
        options, args = Values({'autorestart': False,
                                'dd_url': None,
                                'clean': False,
                                'disable_dd':False,
                                'use_forwarder': False}), []
    return options, args


def get_version():
    return AGENT_VERSION


# Return url endpoint, here because needs access to version number
def get_url_endpoint(default_url, endpoint_type='app'):
    parsed_url = urlparse(default_url)
    if parsed_url.netloc not in LEGACY_DATADOG_URLS:
        return default_url

    subdomain = parsed_url.netloc.split(".")[0]

    # Replace https://app.datadoghq.com in https://5-2-0-app.agent.datadoghq.com
    return default_url.replace(subdomain,
        "{0}-{1}.agent".format(
            get_version().replace(".", "-"),
            endpoint_type))

def skip_leading_wsp(f):
    "Works on a file, returns a file-like object"
    return StringIO("\n".join(map(string.strip, f.readlines())))



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
    if hasattr(sys, 'frozen'):
        # we're frozen - from py2exe
        prog_path = os.path.dirname(sys.executable)
        checksd_path = os.path.join(prog_path, '..', 'checks.d')
    else:

        cur_path = os.path.dirname(__file__)
        checksd_path = os.path.join(cur_path, 'checks.d')

    if os.path.exists(checksd_path):
        return checksd_path
    raise PathNotFound(checksd_path)


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


def _unix_checksd_path():
    # Unix only will look up based on the current directory
    # because checks.d will hang with the other python modules
    cur_path = os.path.dirname(os.path.realpath(__file__))
    checksd_path = os.path.join(cur_path, 'checks.d')

    if os.path.exists(checksd_path):
        return checksd_path
    raise PathNotFound(checksd_path)


def _is_affirmative(s):
    # int or real bool
    if isinstance(s, int):
        return bool(s)
    # try string cast
    return s.lower() in ('yes', 'true', '1')


def get_config_path(cfg_path=None, os_name=None):
    # Check if there's an override and if it exists
    if cfg_path is not None and os.path.exists(cfg_path):
        return cfg_path

    if os_name is None:
        os_name = get_os()

    # Check for an OS-specific path, continue on not-found exceptions
    bad_path = ''
    if os_name == 'windows':
        try:
            return _windows_config_path()
        except PathNotFound, e:
            if len(e.args) > 0:
                bad_path = e.args[0]
    else:
        try:
            return _unix_config_path()
        except PathNotFound, e:
            if len(e.args) > 0:
                bad_path = e.args[0]

    # Check if there's a config stored in the current agent directory
    path = os.path.realpath(__file__)
    path = os.path.dirname(path)
    if os.path.exists(os.path.join(path, DATADOG_CONF)):
        return os.path.join(path, DATADOG_CONF)

    # If all searches fail, exit the agent with an error
    sys.stderr.write("Please supply a configuration file at %s or in the directory where the Agent is currently deployed.\n" % bad_path)
    sys.exit(3)

def get_default_bind_host():
    try:
        socket.gethostbyname('localhost')
    except gaierror:
        log.warning("localhost seems undefined in your hosts file, using 127.0.0.1 instead")
        return '127.0.0.1'
    return 'localhost'

def get_config(parse_args=True, cfg_path=None, options=None):
    if parse_args:
        options, _ = get_parsed_args()

    # General config
    agentConfig = {
        'graphite_listen_port': None,
        'hostname': None,
        'listen_port': None,
        'tags': None,
        'use_ec2_instance_id': False,  # DEPRECATED
        'version': get_version(),
        'watchdog': True,
        'bind_host': get_default_bind_host(),
    }

    # Config handling
    try:
        # Find the right config file
        path = os.path.realpath(__file__)
        path = os.path.dirname(path)

        config_path = get_config_path(cfg_path, os_name=get_os())
        config = ConfigParser.ConfigParser()
        config.readfp(skip_leading_wsp(open(config_path)))

        # bulk import
        for option in config.options('Main'):
            agentConfig[option] = config.get('Main', option)

        #
        # Core config
        #

        # FIXME unnecessarily complex



        # Dogstatsd config
        dogstatsd_defaults = {
            'dogstatsd_port': 8125,
            'dogstatsd_target': 'http://' + agentConfig['bind_host'] + ':17123',
        }
        for key, value in dogstatsd_defaults.iteritems():
            if config.has_option('Main', key):
                agentConfig[key] = config.get('Main', key)
            else:
                agentConfig[key] = value



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

        if config.has_option("Main", "use_curl_http_client"):
            agentConfig["use_curl_http_client"] = _is_affirmative(config.get("Main", "use_curl_http_client"))
        else:
            # Default to False as there are some issues with the curl client and ELB
            agentConfig["use_curl_http_client"] = False

        if config.has_section('WMI'):
            agentConfig['WMI'] = {}
            for key, value in config.items('WMI'):
                agentConfig['WMI'][key] = value

        if config.has_option("Main", "limit_memory_consumption") and \
            config.get("Main", "limit_memory_consumption") is not None:
            agentConfig["limit_memory_consumption"] = int(config.get("Main", "limit_memory_consumption"))
        else:
            agentConfig["limit_memory_consumption"] = None

        if config.has_option("Main", "skip_ssl_validation"):
            agentConfig["skip_ssl_validation"] = _is_affirmative(config.get("Main", "skip_ssl_validation"))

        agentConfig["collect_instance_metadata"] = True
        if config.has_option("Main", "collect_instance_metadata"):
            agentConfig["collect_instance_metadata"] = _is_affirmative(config.get("Main", "collect_instance_metadata"))

        agentConfig["proxy_forbid_method_switch"] = False
        if config.has_option("Main", "proxy_forbid_method_switch"):
            agentConfig["proxy_forbid_method_switch"] = _is_affirmative(config.get("Main", "proxy_forbid_method_switch"))

    except ConfigParser.NoSectionError, e:
        sys.stderr.write('Config file not found or incorrectly formatted.\n')
        sys.exit(2)

    except ConfigParser.ParsingError, e:
        sys.stderr.write('Config file not found or incorrectly formatted.\n')
        sys.exit(2)

    except ConfigParser.NoOptionError, e:
        sys.stderr.write('There are some items missing from your config file, but nothing fatal [%s]' % e)

    # Storing proxy settings in the agentConfig
    agentConfig['proxy_settings'] = get_proxy(agentConfig)
    if agentConfig.get('ca_certs', None) is None:
        agentConfig['ssl_certificate'] = get_ssl_certificate(get_os(), 'datadog-cert.pem')
    else:
        agentConfig['ssl_certificate'] = agentConfig['ca_certs']

    return agentConfig


def get_system_stats():
    systemStats = {
        'machine': platform.machine(),
        'platform': sys.platform,
        'processor': platform.processor(),
        'pythonV': platform.python_version(),
    }

    platf = sys.platform

    if  Platform.is_linux(platf):
        grep = subprocess.Popen(['grep', 'model name', '/proc/cpuinfo'], stdout=subprocess.PIPE, close_fds=True)
        wc = subprocess.Popen(['wc', '-l'], stdin=grep.stdout, stdout=subprocess.PIPE, close_fds=True)
        systemStats['cpuCores'] = int(wc.communicate()[0])

    if Platform.is_darwin(platf):
        systemStats['cpuCores'] = int(subprocess.Popen(['sysctl', 'hw.ncpu'], stdout=subprocess.PIPE, close_fds=True).communicate()[0].split(': ')[1])

    if Platform.is_freebsd(platf):
        systemStats['cpuCores'] = int(subprocess.Popen(['sysctl', 'hw.ncpu'], stdout=subprocess.PIPE, close_fds=True).communicate()[0].split(': ')[1])

    if Platform.is_linux(platf):
        systemStats['nixV'] = platform.dist()

    elif Platform.is_darwin(platf):
        systemStats['macV'] = platform.mac_ver()

    elif Platform.is_freebsd(platf):
        version = platform.uname()[2]
        systemStats['fbsdV'] = ('freebsd', version, '')  # no codename for FreeBSD

    elif Platform.is_win32(platf):
        systemStats['winV'] = platform.win32_ver()

    return systemStats


def set_win32_cert_path():
    """In order to use tornado.httpclient with the packaged .exe on Windows we
    need to override the default ceritifcate location which is based on the path
    to tornado and will give something like "C:\path\to\program.exe\tornado/cert-file".

    If pull request #379 is accepted (https://github.com/facebook/tornado/pull/379) we
    will be able to override this in a clean way. For now, we have to monkey patch
    tornado.httpclient._DEFAULT_CA_CERTS
    """
    if hasattr(sys, 'frozen'):
        # we're frozen - from py2exe
        prog_path = os.path.dirname(sys.executable)
        crt_path = os.path.join(prog_path, 'ca-certificates.crt')
    else:
        cur_path = os.path.dirname(__file__)
        crt_path = os.path.join(cur_path, 'packaging', 'datadog-agent', 'win32',
                'install_files', 'ca-certificates.crt')
    import tornado.simple_httpclient
    log.info("Windows certificate path: %s" % crt_path)
    tornado.simple_httpclient._DEFAULT_CA_CERTS = crt_path

def get_proxy(agentConfig, use_system_settings=False):
    proxy_settings = {}

    # First we read the proxy configuration from datadog.conf
    proxy_host = agentConfig.get('proxy_host', None)
    if proxy_host is not None and not use_system_settings:
        proxy_settings['host'] = proxy_host
        try:
            proxy_settings['port'] = int(agentConfig.get('proxy_port', 3128))
        except ValueError:
            log.error('Proxy port must be an Integer. Defaulting it to 3128')
            proxy_settings['port'] = 3128

        proxy_settings['user'] = agentConfig.get('proxy_user', None)
        proxy_settings['password'] = agentConfig.get('proxy_password', None)
        proxy_settings['system_settings'] = False
        log.debug("Proxy Settings: %s:%s@%s:%s" % (proxy_settings['user'], "*****", proxy_settings['host'], proxy_settings['port']))
        return proxy_settings

    # If no proxy configuration was specified in datadog.conf
    # We try to read it from the system settings
    try:
        import urllib
        proxies = urllib.getproxies()
        proxy = proxies.get('https', None)
        if proxy is not None:
            try:
                proxy = proxy.split('://')[1]
            except Exception:
                pass
            px = proxy.split(':')
            proxy_settings['host'] = px[0]
            proxy_settings['port'] = int(px[1])
            proxy_settings['user'] = None
            proxy_settings['password'] = None
            proxy_settings['system_settings'] = True
            if '@' in proxy_settings['host']:
                creds = proxy_settings['host'].split('@')[0].split(':')
                proxy_settings['user'] = creds[0]
                if len(creds) == 2:
                    proxy_settings['password'] = creds[1]

            log.debug("Proxy Settings: %s:%s@%s:%s" % (proxy_settings['user'], "*****", proxy_settings['host'], proxy_settings['port']))
            return proxy_settings

    except Exception, e:
        log.debug("Error while trying to fetch proxy settings using urllib %s. Proxy is probably not set" % str(e))

    log.debug("No proxy configured")

    return None


def get_confd_path(osname=None):
    if not osname:
        osname = get_os()
    bad_path = ''
    if osname == 'windows':
        try:
            return _windows_confd_path()
        except PathNotFound, e:
            if len(e.args) > 0:
                bad_path = e.args[0]
    else:
        try:
            return _unix_confd_path()
        except PathNotFound, e:
            if len(e.args) > 0:
                bad_path = e.args[0]

    cur_path = os.path.dirname(os.path.realpath(__file__))
    cur_path = os.path.join(cur_path, 'conf.d')

    if os.path.exists(cur_path):
        return cur_path

    raise PathNotFound(bad_path)


def get_checksd_path(osname=None):
    if not osname:
        osname = get_os()
    if osname == 'windows':
        return _windows_checksd_path()
    else:
        return _unix_checksd_path()


def get_win32service_file(osname, filename):
    # This file is needed to log in the event viewer for windows
    if osname == 'windows':
        if hasattr(sys, 'frozen'):
            # we're frozen - from py2exe
            prog_path = os.path.dirname(sys.executable)
            path = os.path.join(prog_path, filename)
        else:
            cur_path = os.path.dirname(__file__)
            path = os.path.join(cur_path, filename)
        if os.path.exists(path):
            log.debug("Certificate file found at %s" % str(path))
            return path

    else:
        cur_path = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(cur_path, filename)
        if os.path.exists(path):
            return path

    return None


def get_ssl_certificate(osname, filename):
    # The SSL certificate is needed by tornado in case of connection through a proxy
    if osname == 'windows':
        if hasattr(sys, 'frozen'):
            # we're frozen - from py2exe
            prog_path = os.path.dirname(sys.executable)
            path = os.path.join(prog_path, filename)
        else:
            cur_path = os.path.dirname(__file__)
            path = os.path.join(cur_path, filename)
        if os.path.exists(path):
            log.debug("Certificate file found at %s" % str(path))
            return path

    else:
        cur_path = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(cur_path, filename)
        if os.path.exists(path):
            return path


    log.info("Certificate file NOT found at %s" % str(path))
    return None

def check_yaml(conf_path):
    f = open(conf_path)
    check_name = os.path.basename(conf_path).split('.')[0]
    try:
        check_config = yaml.load(f.read(), Loader=yLoader)
        assert 'init_config' in check_config, "No 'init_config' section found"
        assert 'instances' in check_config, "No 'instances' section found"

        valid_instances = True
        if check_config['instances'] is None or not isinstance(check_config['instances'], list):
            valid_instances = False
        else:
            for i in check_config['instances']:
                if not isinstance(i, dict):
                    valid_instances = False
                    break
        if not valid_instances:
            raise Exception('You need to have at least one instance defined in the YAML file for this check')
        else:
            return check_config
    finally:
        f.close()

def load_check_directory(agentConfig, hostname):
    ''' Return the initialized checks from checks.d, and a mapping of checks that failed to
    initialize. Only checks that have a configuration
    file in conf.d will be returned. '''
    from checks import AgentCheck

    initialized_checks = {}
    init_failed_checks = {}
    deprecated_checks = {}
    agentConfig['checksd_hostname'] = hostname

    deprecated_configs_enabled = [v for k,v in OLD_STYLE_PARAMETERS if len([l for l in agentConfig if l.startswith(k)]) > 0]
    for deprecated_config in deprecated_configs_enabled:
        msg = "Configuring %s in datadog.conf is not supported anymore. Please use conf.d" % deprecated_config
        deprecated_checks[deprecated_config] = {'error': msg, 'traceback': None}
        log.error(msg)

    osname = get_os()
    checks_paths = [glob.glob(os.path.join(agentConfig['additional_checksd'], '*.py'))]

    try:
        checksd_path = get_checksd_path(osname)
        checks_paths.append(glob.glob(os.path.join(checksd_path, '*.py')))
    except PathNotFound, e:
        log.error(e.args[0])
        sys.exit(3)

    try:
        confd_path = get_confd_path(osname)
    except PathNotFound, e:
        log.error("No conf.d folder found at '%s' or in the directory where the Agent is currently deployed.\n" % e.args[0])
        sys.exit(3)

    # We don't support old style configs anymore
    # So we iterate over the files in the checks.d directory
    # If there is a matching configuration file in the conf.d directory
    # then we import the check
    for check in itertools.chain(*checks_paths):
        check_name = os.path.basename(check).split('.')[0]
        check_config = None
        if check_name in initialized_checks or check_name in init_failed_checks:
            log.debug('Skipping check %s because it has already been loaded from another location', check)
            continue

        # Let's see if there is a conf.d for this check
        conf_path = os.path.join(confd_path, '%s.yaml' % check_name)

        # Default checks are checks that are enabled by default
        # They read their config from the "[CHECKNAME].yaml.default" file
        if check_name in DEFAULT_CHECKS:
            default_conf_path = os.path.join(confd_path, '%s.yaml.default' % check_name)
        else:
            default_conf_path = None

        conf_exists = False

        if os.path.exists(conf_path):
            conf_exists = True

        elif not conf_exists and default_conf_path is not None:
            if not os.path.exists(default_conf_path):
                log.error("Default configuration file {0} is missing".format(default_conf_path))
                continue
            conf_path = default_conf_path
            conf_exists = True

        if conf_exists:
            f = open(conf_path)
            try:
                check_config = check_yaml(conf_path)
            except Exception, e:
                log.exception("Unable to parse yaml config in %s" % conf_path)
                traceback_message = traceback.format_exc()
                init_failed_checks[check_name] = {'error':str(e), 'traceback':traceback_message}
                continue
        else:
            # Compatibility code for the Nagios checks if it's still configured
            # in datadog.conf
            # fixme: Should be removed in ulterior major version
            if check_name == 'nagios':
                if any([nagios_key in agentConfig for nagios_key in NAGIOS_OLD_CONF_KEYS]):
                    log.warning("Configuring Nagios in datadog.conf is deprecated "
                                "and will be removed in a future version. "
                                "Please use conf.d")
                    check_config = {'instances':[dict((key, agentConfig[key]) for key in agentConfig if key in NAGIOS_OLD_CONF_KEYS)]}
                else:
                    continue
            else:
                log.debug("No configuration file for %s" % check_name)
                continue

        # If we are here, there is a valid matching configuration file.
        # Let's try to import the check
        try:
            check_module = imp.load_source('checksd_%s' % check_name, check)
        except Exception, e:
            traceback_message = traceback.format_exc()
            # There is a configuration file for that check but the module can't be imported
            init_failed_checks[check_name] = {'error':e, 'traceback':traceback_message}
            log.exception('Unable to import check module %s.py from checks.d' % check_name)
            continue

        # We make sure that there is an AgentCheck class defined
        check_class = None
        classes = inspect.getmembers(check_module, inspect.isclass)
        for _, clsmember in classes:
            if clsmember == AgentCheck:
                continue
            if issubclass(clsmember, AgentCheck):
                check_class = clsmember
                if AgentCheck in clsmember.__bases__:
                    continue
                else:
                    break

        if not check_class:
            log.error('No check class (inheriting from AgentCheck) found in %s.py' % check_name)
            continue

        # Look for the per-check config, which *must* exist
        if not check_config.get('instances'):
            log.error("Config %s is missing 'instances'" % conf_path)
            continue

        # Init all of the check's classes with
        init_config = check_config.get('init_config', {})
        # init_config: in the configuration triggers init_config to be defined
        # to None.
        if init_config is None:
            init_config = {}

        instances = check_config['instances']
        try:
            try:
                c = check_class(check_name, init_config=init_config,
                                agentConfig=agentConfig, instances=instances)
            except TypeError, e:
                # Backwards compatibility for checks which don't support the
                # instances argument in the constructor.
                c = check_class(check_name, init_config=init_config,
                                agentConfig=agentConfig)
                c.instances = instances
        except Exception, e:
            log.exception('Unable to initialize check %s' % check_name)
            traceback_message = traceback.format_exc()
            init_failed_checks[check_name] = {'error':e, 'traceback':traceback_message}
        else:
            initialized_checks[check_name] = c

        # Add custom pythonpath(s) if available
        if 'pythonpath' in check_config:
            pythonpath = check_config['pythonpath']
            if not isinstance(pythonpath, list):
                pythonpath = [pythonpath]
            sys.path.extend(pythonpath)

        log.debug('Loaded check.d/%s.py' % check_name)

    init_failed_checks.update(deprecated_checks)
    log.info('initialized checks.d checks: %s' % initialized_checks.keys())
    log.info('initialization failed checks.d checks: %s' % init_failed_checks.keys())
    return {'initialized_checks':initialized_checks.values(),
            'init_failed_checks':init_failed_checks,
            }


#
# logging

def get_log_date_format():
    return "%Y-%m-%d %H:%M:%S %Z"


def get_log_format(logger_name):
    if get_os() != 'windows':
        return '%%(asctime)s | %%(levelname)s | dd.%s | %%(name)s(%%(filename)s:%%(lineno)s) | %%(message)s' % logger_name
    return '%(asctime)s | %(levelname)s | %(name)s(%(filename)s:%(lineno)s) | %(message)s'


def get_syslog_format(logger_name):
    return 'dd.%s[%%(process)d]: %%(levelname)s (%%(filename)s:%%(lineno)s): %%(message)s' % logger_name


def get_jmx_status_path():
    if Platform.is_win32():
        path = os.path.join(_windows_commondata_path(), 'Datadog')
    else:
        path = tempfile.gettempdir()
    return path


