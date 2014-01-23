import os
import platform
import signal
import socket
import subprocess
import sys
import math
import time
import types
import urllib2
import uuid
import tempfile

# Tornado
try:
    from tornado import ioloop, version_info as tornado_version
except ImportError:
    pass # We are likely running the agent without the forwarder and tornado is not installed
try:
    from hashlib import md5
except ImportError:
    from md5 import md5


# Import json for the agent. Try simplejson first, then the stdlib version and
# if all else fails, use minjson which we bundle with the agent.
def generate_minjson_adapter():
    import minjson
    class json(object):
        @staticmethod
        def dumps(data):
            return minjson.write(data)

        @staticmethod
        def loads(data):
            return minjson.safeRead(data)
    return json

try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = generate_minjson_adapter()



import yaml
try:
    from yaml import CLoader as yLoader
except ImportError:
    from yaml import Loader as yLoader

try:
    from collections import namedtuple
except ImportError:
    from compat.namedtuple import namedtuple

import logging
log = logging.getLogger(__name__)

NumericTypes = (float, int, long)

def plural(count):
    if count > 1:
        return "s"
    return ""

def get_tornado_ioloop():
    if tornado_version[0] == 3:
        return ioloop.IOLoop.current()
    else:
        return ioloop.IOLoop.instance()

def get_uuid():
    # Generate a unique name that will stay constant between
    # invocations, such as platform.node() + uuid.getnode()
    # Use uuid5, which does not depend on the clock and is
    # recommended over uuid3.
    # This is important to be able to identify a server even if
    # its drives have been wiped clean.
    # Note that this is not foolproof but we can reconcile servers
    # on the back-end if need be, based on mac addresses.
    return uuid.uuid5(uuid.NAMESPACE_DNS, platform.node() + str(uuid.getnode())).hex


def get_os():
    "Human-friendly OS name"
    if sys.platform == 'darwin':
        return 'mac'
    elif sys.platform.find('freebsd') != -1:
        return 'freebsd'
    elif sys.platform.find('linux') != -1:
        return 'linux'
    elif sys.platform.find('win32') != -1:
        return 'windows'
    elif sys.platform.find('sunos') != -1:
        return 'solaris'
    else:
        return sys.platform


def headers(agentConfig):
    # Build the request headers
    return {
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html, */*',
    }


def getTopIndex():
    macV = None
    if sys.platform == 'darwin':
        macV = platform.mac_ver()
        
    # Output from top is slightly modified on OS X 10.6 (case #28239)
    if macV and macV[0].startswith('10.6.'):
        return 6
    else:
        return 5


def isnan(val):
    if hasattr(math, 'isnan'):
        return math.isnan(val)

    # for py < 2.6, use a different check
    # http://stackoverflow.com/questions/944700/how-to-check-for-nan-in-python
    return str(val) == str(1e400*0)


def cast_metric_val(val):
    # ensure that the metric value is a numeric type
    if not isinstance(val, NumericTypes):
        # Try the int conversion first because want to preserve
        # whether the value is an int or a float. If neither work,
        # raise a ValueError to be handled elsewhere
        for cast in [int, float]:
            try:
                val = cast(val)
                return val
            except ValueError:
                continue
        raise ValueError
    return val

def is_valid_hostname(hostname):
    return hostname.lower() not in set([
        'localhost',
        'localhost.localdomain',
        'localhost6.localdomain6',
        'ip6-localhost',
    ])

def get_hostname(config=None):
    """
    Get the canonical host name this agent should identify as. This is
    the authoritative source of the host name for the agent.

    Tries, in order:

      * agent config (datadog.conf, "hostname:")
      * 'hostname -f' (on unix)
      * socket.gethostname()
    """
    hostname = None

    # first, try the config
    if config is None:
        from config import get_config
        config = get_config(parse_args=True)
    config_hostname = config.get('hostname')
    if config_hostname and is_valid_hostname(config_hostname):
        hostname = config_hostname

    # then move on to os-specific detection
    if hostname is None:
        def _get_hostname_unix():
            try:
                # try fqdn
                p = subprocess.Popen(['/bin/hostname', '-f'], stdout=subprocess.PIPE)
                out, err = p.communicate()
                if p.returncode == 0:
                    return out.strip()
            except Exception:
                return None

        os_name = get_os()
        if os_name in ['mac', 'freebsd', 'linux', 'solaris']:
            unix_hostname = _get_hostname_unix()
            if unix_hostname and is_valid_hostname(unix_hostname):
                hostname = unix_hostname

    # if we have an ec2 default hostname, see if there's an instance-id available
    if hostname is not None and True in [hostname.lower().startswith(p) for p in [u'ip-', u'domu']]:
        instanceid = EC2.get_instance_id()
        if instanceid:
            hostname = instanceid

    # fall back on socket.gethostname(), socket.getfqdn() is too unreliable
    if hostname is None:
        try:
            socket_hostname = socket.gethostname()
        except socket.error, e:
            socket_hostname = None
        if socket_hostname and is_valid_hostname(socket_hostname):
            hostname = socket_hostname

    if hostname is None:
        log.critical('Unable to reliably determine host name. You can define one in datadog.conf or in your hosts file')
        raise Exception('Unable to reliably determine host name. You can define one in datadog.conf or in your hosts file')
    else:
        return hostname

class EC2(object):
    """Retrieve EC2 metadata
    """
    URL = "http://169.254.169.254/latest/meta-data"
    TIMEOUT = 0.1 # second
    metadata = {}

    @staticmethod
    def get_tags():
        socket_to = None
        try:
            socket_to = socket.getdefaulttimeout()
            socket.setdefaulttimeout(EC2.TIMEOUT)
        except Exception:
            pass

        try:
            iam_role = urllib2.urlopen(EC2.URL + "/iam/security-credentials").read().strip()
            iam_params = json.loads(urllib2.urlopen(EC2.URL + "/iam/security-credentials" + "/" + unicode(iam_role)).read().strip())
            from checks.libs.boto.ec2.connection import EC2Connection
            connection = EC2Connection(aws_access_key_id=iam_params['AccessKeyId'], aws_secret_access_key=iam_params['SecretAccessKey'], security_token=iam_params['Token'])
            instance_object = connection.get_only_instances([EC2.metadata['instance-id']])[0]

            EC2_tags = [u"%s:%s" % (tag_key, tag_value) for tag_key, tag_value in instance_object.tags.iteritems()]

        except Exception:
            log.exception("Problem retrieving custom EC2 tags")
            EC2_tags = []

        try:
            if socket_to is None:
                socket_to = 3
            socket.setdefaulttimeout(socket_to)
        except Exception:
            pass

        return EC2_tags


    @staticmethod
    def get_metadata():
        """Use the ec2 http service to introspect the instance. This adds latency if not running on EC2
        """
        # >>> import urllib2
        # >>> urllib2.urlopen('http://169.254.169.254/latest/', timeout=1).read()
        # 'meta-data\nuser-data'
        # >>> urllib2.urlopen('http://169.254.169.254/latest/meta-data', timeout=1).read()
        # 'ami-id\nami-launch-index\nami-manifest-path\nhostname\ninstance-id\nlocal-ipv4\npublic-keys/\nreservation-id\nsecurity-groups'
        # >>> urllib2.urlopen('http://169.254.169.254/latest/meta-data/instance-id', timeout=1).read()
        # 'i-deadbeef'

        # Every call may add TIMEOUT seconds in latency so don't abuse this call
        # python 2.4 does not support an explicit timeout argument so force it here
        # Rather than monkey-patching urllib2, just lower the timeout globally for these calls
        socket_to = None
        try:
            socket_to = socket.getdefaulttimeout()
            socket.setdefaulttimeout(EC2.TIMEOUT)
        except Exception:
            pass

        for k in ('instance-id', 'hostname', 'local-hostname', 'public-hostname', 'ami-id', 'local-ipv4', 'public-keys', 'public-ipv4', 'reservation-id', 'security-groups'):
            try:
                v = urllib2.urlopen(EC2.URL + "/" + unicode(k)).read().strip()
                assert type(v) in (types.StringType, types.UnicodeType) and len(v) > 0, "%s is not a string" % v
                EC2.metadata[k] = v
            except Exception:
                pass

        try:
            if socket_to is None:
                socket_to = 3
            socket.setdefaulttimeout(socket_to)
        except Exception:
            pass

        return EC2.metadata

    @staticmethod
    def get_instance_id():
        try:
            return EC2.get_metadata().get("instance-id", None)
        except Exception:
            return None


class Watchdog(object):
    """Simple signal-based watchdog that will scuttle the current process
    if it has not been reset every N seconds, or if the processes exceeds
    a specified memory threshold.
    Can only be invoked once per process, so don't use with multiple threads.
    If you instantiate more than one, you're also asking for trouble.
    """
    def __init__(self, duration, max_mem_mb = None):
        import resource

        #Set the duration
        self._duration = int(duration)
        signal.signal(signal.SIGALRM, Watchdog.self_destruct)

        # cap memory usage
        if max_mem_mb is not None:
            self._max_mem_kb = 1024 * max_mem_mb
            max_mem_bytes = 1024 * self._max_mem_kb
            resource.setrlimit(resource.RLIMIT_AS, (max_mem_bytes, max_mem_bytes))
            self.memory_limit_enabled = True
        else:
            self.memory_limit_enabled = False

    @staticmethod
    def self_destruct(signum, frame):
        try:
            import traceback
            log.error("Self-destructing...")
            log.error(traceback.format_exc())
        finally:
            os.kill(os.getpid(), signal.SIGKILL)


    def reset(self):
        # self destruct if using too much memory, as tornado will swallow MemoryErrors
        mem_usage_kb = int(os.popen('ps -p %d -o %s | tail -1' % (os.getpid(), 'rss')).read())
        if self.memory_limit_enabled and mem_usage_kb > (0.95 * self._max_mem_kb):
            Watchdog.self_destruct(signal.SIGKILL, sys._getframe(0))

        log.debug("Resetting watchdog for %d" % self._duration)
        signal.alarm(self._duration)


class PidFile(object):
    """ A small helper class for pidfiles. """

    PID_DIR = '/var/run/dd-agent'


    def __init__(self, program, pid_dir=None):
        self.pid_file = "%s.pid" % program
        self.pid_dir = pid_dir or self.get_default_pid_dir()
        self.pid_path = os.path.join(self.pid_dir, self.pid_file)

    def get_default_pid_dir(self):
        if get_os() != 'windows':
            return PidFile.PID_DIR

        return tempfile.gettempdir()

    def get_path(self):
        # Can we write to the directory
        try:
            if os.access(self.pid_dir, os.W_OK):
                log.info("Pid file is: %s" % self.pid_path)
                return self.pid_path
        except Exception:
            log.warn("Cannot locate pid file, trying to use: %s" % tempfile.gettempdir())

        # if all else fails
        if os.access(tempfile.gettempdir(), os.W_OK):
            tmp_path = os.path.join(tempfile.gettempdir(), self.pid_file)
            log.debug("Using temporary pid file: %s" % tmp_path)
            return tmp_path
        else:
            # Can't save pid file, bail out
            log.error("Cannot save pid file anywhere")
            raise Exception("Cannot save pid file anywhere")


    def clean(self):
        try:
            path = self.get_path()
            log.debug("Cleaning up pid file %s" % path)
            os.remove(path)
            return True
        except Exception:
            log.warn("Could not clean up pid file")
            return False


    def get_pid(self):
        "Retrieve the actual pid"
        try:
            pf = open(self.get_path())
            pid_s = pf.read()
            pf.close()

            return int(pid_s.strip())
        except Exception:
            return None


class LaconicFilter(logging.Filter):
    """
    Filters messages, only print them once while keeping memory under control
    """
    LACONIC_MEM_LIMIT = 1024

    def __init__(self, name=""):
        logging.Filter.__init__(self, name)
        self.hashed_messages = {}

    def hash(self, msg):
        return md5(msg).hexdigest()

    def filter(self, record):
        try:
            h = self.hash(record.getMessage())
            if h in self.hashed_messages:
                return 0
            else:
                # Don't blow up our memory
                if len(self.hashed_messages) >= LaconicFilter.LACONIC_MEM_LIMIT:
                    self.hashed_messages.clear()
                self.hashed_messages[h] = True
                return 1
        except Exception:
            return 1

class Timer(object):
    """ Helper class """

    def __init__(self):
        self.start()

    def _now(self):
        return time.time()

    def start(self):
        self.start = self._now()
        self.last = self.start
        return self

    def step(self):
        now = self._now()
        step =  now - self.last
        self.last = now
        return step

    def total(self, as_sec=True):
        return self._now() - self.start
