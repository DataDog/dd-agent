import logging
import os
import platform
import signal
import sys
import math

NumericTypes = (float, int, long)

# We need to return the data using JSON. As of Python 2.6+, there is a core JSON
# module. We have a 2.4/2.5 compatible lib included with the agent but if we're
# on 2.6 or above, we should use the core module which will be faster
pythonVersion = platform.python_version_tuple()

if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
    import json
else:
    import minjson
    class json(object):
        @staticmethod
        def dumps(data):
            return minjson.write(data)

        @staticmethod
        def loads(data):
            return minjson.safeRead(data)

import yaml
try:
    from yaml import CLoader as yLoader
except ImportError:
    from yaml import Loader as yLoader


def headers(agentConfig):
    # Build the request headers
    return {
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html, */*',
    }

def getOS():
    if sys.platform == 'darwin':
        return 'mac'
    elif sys.platform.find('freebsd') != -1:
        return 'freebsd'
    elif sys.platform.find('linux') != -1:
        return 'linux'
    elif sys.platform.find('win32') != -1:
        return 'windows'
    else:
        return sys.platform

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
            logging.error("Self-destructing...")
            logging.error(traceback.format_exc())
        finally:
            os.kill(os.getpid(), signal.SIGKILL)

    def reset(self):
        logging.debug("Resetting watchdog for %d" % self._duration)
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
                logging.info("Pid file is: %s" % self.pid_path)
                return self.pid_path
        except:
            logging.exception("Cannot locate pid file, defaulting to /tmp/%s" % PID_FILE)

        # if all else fails
        if os.access("/tmp", os.W_OK):
            tmp_path = os.path.join('/tmp', self.pid_file)
            logging.warn("Using temporary pid file: %s" % tmp_path)
            return tmp_path
        else:
            # Can't save pid file, bail out
            logging.error("Cannot save pid file anywhere")
            raise Exception("Cannot save pid file anywhere")

    def clean(self):
        try:
            path = self.get_path()
            logging.debug("Cleaning up pid file %s" % path)
            os.remove(path)
            return True
        except:
            logging.exception("Could not clean up pid file")
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

    
