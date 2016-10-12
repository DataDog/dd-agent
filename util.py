# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import deque
import logging
import os
import platform
import re
import signal
import sys
import time
import uuid

# 3p
import yaml  # noqa, let's guess, probably imported somewhere
try:
    from yaml import CLoader as yLoader
    from yaml import CDumper as yDumper
except ImportError:
    # On source install C Extensions might have not been built
    from yaml import Loader as yLoader  # noqa, imported from here elsewhere
    from yaml import Dumper as yDumper  # noqa, imported from here elsewhere

# These classes are now in utils/, they are just here for compatibility reasons,
# if a user actually uses them in a custom check
# If you're this user, please use utils/* instead
# FIXME: remove them at a point (6.x)
from utils.pidfile import PidFile  # noqa, see ^^^
from utils.platform import Platform, get_os # noqa, see ^^^
from utils.proxy import get_proxy # noqa, see ^^^

COLON_NON_WIN_PATH = re.compile(':(?!\\\\)')

log = logging.getLogger(__name__)

NumericTypes = (float, int, long)


def plural(count):
    if count == 1:
        return ""
    return "s"

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


def headers(agentConfig, **kwargs):
    # Build the request headers
    res = {
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html, */*',
    }
    if 'http_host' in kwargs:
        res['Host'] = kwargs['http_host']
    return res


def windows_friendly_colon_split(config_string):
    '''
    Perform a split by ':' on the config_string
    without splitting on the start of windows path
    '''
    if Platform.is_win32():
        # will split on path/to/module.py:blabla but not on C:\\path
        return COLON_NON_WIN_PATH.split(config_string)
    else:
        return config_string.split(':')


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

_IDS = {}


def get_next_id(name):
    global _IDS
    current_id = _IDS.get(name, 0)
    current_id += 1
    _IDS[name] = current_id
    return current_id


def check_yaml(conf_path):
    with open(conf_path) as f:
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

def config_to_yaml(config):
    '''
    Convert a config dict to YAML
    '''
    assert 'init_config' in config, "No 'init_config' section found"
    assert 'instances' in config, "No 'instances' section found"

    valid_instances = True
    if config['instances'] is None or not isinstance(config['instances'], list):
        valid_instances = False
    else:
        yaml_output = yaml.safe_dump(config, default_flow_style=False)

    if not valid_instances:
        raise Exception('You need to have at least one instance defined in your config.')

    return yaml_output

def dump_yaml(path, config):
    '''
    Dump config dict to YAML file in path
    '''
    try:
        yaml = config_to_yaml(config)
    except Exception as e:
        log.exception("Unable to convert config to YAML: %s", e)
    else:
        with open(path, 'w+') as f:
            f.write(yaml)


class Watchdog(object):
    """
    Simple signal-based watchdog. Restarts the process when:
    * no reset was made for more than a specified duration
    * (optional) a specified memory threshold is exceeded
    * (optional) a suspicious high activity is detected, i.e. too many resets for a given timeframe.

    **Warning**: Not thread-safe.
    Can only be invoked once per process, so don't use with multiple threads.
    If you instantiate more than one, you're also asking for trouble.
    """
    # Activity history timeframe
    _RESTART_TIMEFRAME = 60

    def __init__(self, duration, max_mem_mb=None, max_resets=None):
        import resource

        # Set the duration
        self._duration = int(duration)
        signal.signal(signal.SIGALRM, Watchdog.self_destruct)

        # Set memory usage threshold
        if max_mem_mb is not None:
            self._max_mem_kb = 1024 * max_mem_mb
            max_mem_bytes = 1024 * self._max_mem_kb
            resource.setrlimit(resource.RLIMIT_AS, (max_mem_bytes, max_mem_bytes))
            self.memory_limit_enabled = True
        else:
            self.memory_limit_enabled = False

        # Set high activity monitoring
        self._restarts = deque([])
        self._max_resets = max_resets

    @staticmethod
    def self_destruct(signum, frame):
        """
        Kill the process. It will be eventually restarted.
        """
        try:
            import traceback
            log.error("Self-destructing...")
            log.error(traceback.format_exc())
        finally:
            os.kill(os.getpid(), signal.SIGKILL)

    def _is_frenetic(self):
        """
        Detect suspicious high activity, i.e. the number of resets exceeds the maximum limit set
        on the watchdog timeframe.
        Flush old activity history
        """
        now = time.time()
        while(self._restarts and self._restarts[0] < now - self._RESTART_TIMEFRAME):
            self._restarts.popleft()

        return len(self._restarts) > self._max_resets

    def reset(self):
        """
        Reset the watchdog state, i.e.
        * re-arm alarm signal
        * (optional) check memory consumption
        * (optional) save reset history, flush old entries and check frequency
        """
        # Check memory consumption: restart if too high as tornado will swallow MemoryErrors
        if self.memory_limit_enabled:
            mem_usage_kb = int(os.popen('ps -p %d -o %s | tail -1' % (os.getpid(), 'rss')).read())
            if mem_usage_kb > (0.95 * self._max_mem_kb):
                Watchdog.self_destruct(signal.SIGKILL, sys._getframe(0))

        # Check activity
        if self._max_resets:
            self._restarts.append(time.time())
            if self._is_frenetic():
                Watchdog.self_destruct(signal.SIGKILL, sys._getframe(0))

        # Re arm alarm signal
        log.debug("Resetting watchdog for %d" % self._duration)
        signal.alarm(self._duration)


class Timer(object):
    """ Helper class """

    def __init__(self):
        self.start()

    def _now(self):
        return time.time()

    def start(self):
        self.started = self._now()
        self.last = self.started
        return self

    def step(self):
        now = self._now()
        step = now - self.last
        self.last = now
        return step

    def total(self, as_sec=True):
        return self._now() - self.started

"""
Iterable Recipes
"""

def chunks(iterable, chunk_size):
    """Generate sequences of `chunk_size` elements from `iterable`."""
    iterable = iter(iterable)
    while True:
        chunk = [None] * chunk_size
        count = 0
        try:
            for _ in range(chunk_size):
                chunk[count] = iterable.next()
                count += 1
            yield chunk[:count]
        except StopIteration:
            if count:
                yield chunk[:count]
            break
