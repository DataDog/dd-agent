import logging
import os
import platform
import signal
import sys

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
