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
            except:
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
        raise Exception('Unable to reliably determine host name')
    else:
        return hostname

class EC2(object):
    """Retrieve EC2 metadata
    """
    URL = "http://169.254.169.254/latest/meta-data"
    TIMEOUT = 0.1 # second

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
        metadata = {}

        # Every call may add TIMEOUT seconds in latency so don't abuse this call
        # python 2.4 does not support an explicit timeout argument so force it here
        # Rather than monkey-patching urllib2, just lower the timeout globally for these calls
        socket_to = None
        try:
            socket_to = socket.getdefaulttimeout()
            socket.setdefaulttimeout(EC2.TIMEOUT)
        except:
            pass

        for k in ('instance-id', 'hostname', 'local-hostname', 'public-hostname', 'ami-id', 'local-ipv4', 'public-keys', 'public-ipv4', 'reservation-id', 'security-groups'):
            try:
                v = urllib2.urlopen(EC2.URL + "/" + unicode(k)).read().strip()
                assert type(v) in (types.StringType, types.UnicodeType) and len(v) > 0, "%s is not a string" % v
                metadata[k] = v
            except:
                pass

        try:
            if socket_to is None:
                socket_to = 3
            socket.setdefaulttimeout(socket_to)
        except:
            pass

        return metadata

    @staticmethod
    def get_instance_id():
        try:
            return EC2.get_metadata().get("instance-id", None)
        except:
            return None

class Watchdog(object):
    """Simple signal-based watchdog that will scuttle the current process
    if it has not been reset every N seconds.
    Can only be invoked once per process, so don't use with multiple threads.
    If you instantiate more than one, you're also asking for trouble.
    """
    def __init__(self, duration):
        """Set the duration
        """
        self._duration = int(duration)
        signal.signal(signal.SIGALRM, Watchdog.self_destruct)


    @staticmethod
    def self_destruct(signum, frame):
        try:
            import traceback
            log.error("Self-destructing...")
            log.error(traceback.format_exc())
        finally:
            os.kill(os.getpid(), signal.SIGKILL)


    def reset(self):
        log.debug("Resetting watchdog for %d" % self._duration)
        signal.alarm(self._duration)


class PidFile(object):
    """ A small helper class for pidfiles. """

    PID_DIR = '/var/run/dd-agent'


    def __init__(self, program, pid_dir=PID_DIR):
        self.pid_file = "%s.pid" % program
        self.pid_dir = pid_dir
        self.pid_path = os.path.join(self.pid_dir, self.pid_file)


    def get_path(self):
        # Can we write to the directory
        try:
            if os.access(self.pid_dir, os.W_OK):
                log.info("Pid file is: %s" % self.pid_path)
                return self.pid_path
        except:
            log.warn("Cannot locate pid file, defaulting to /tmp/%s" % PID_FILE)

        # if all else fails
        if os.access("/tmp", os.W_OK):
            tmp_path = os.path.join('/tmp', self.pid_file)
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
        except:
            log.warn("Could not clean up pid file")
            return False


    def get_pid(self):
        "Retrieve the actual pid"
        try:
            pf = open(self.get_path())
            pid_s = pf.read()
            pf.close()

            return int(pid_s.strip())
        except:
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
        except:
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


class AgentSupervisor(object):
    ''' A simple supervisor to keep a restart a child on expected auto-restarts
    '''
    RESTART_EXIT_STATUS = 5

    @classmethod
    def start(cls, parent_func, child_func=None):
        ''' `parent_func` is a function that's called every time the child
            process dies.
            `child_func` is a function that should be run by the forked child
            that will auto-restart with the RESTART_EXIT_STATUS.
        '''
        cls.running = True
        exit_code = cls.RESTART_EXIT_STATUS

        # Allow the child process to die on SIGTERM
        signal.signal(signal.SIGTERM, cls._handle_sigterm)

        while cls.running and exit_code == cls.RESTART_EXIT_STATUS:
            try:
                pid = os.fork()
                if pid > 0:
                    # The parent waits on the child.
                    cls.child_pid = pid
                    wait_pid, status = os.waitpid(pid, 0)
                    exit_code = status >> 8
                    parent_func()
                else:
                    # The child will call our given function
                    if child_func:
                        child_func()
                    else:
                        break
            except OSError, e:
                msg = "Agent fork failed: %d (%s)" % (e.errno, e.strerror)
                logging.error(msg)
                sys.stderr.write(msg + "\n")
                sys.exit(1)

        # Exit from the parent cleanly
        if pid > 0:
            sys.exit(0)

    @classmethod
    def _handle_sigterm(cls, signum, frame):
        os.kill(cls.child_pid, signal.SIGTERM)
