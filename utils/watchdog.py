import logging
import os
import resource
import signal
import threading
import time
import traceback

try:
    import psutil
except ImportError:
    psutil = None

from utils.platform import Platform

log = logging.getLogger(__name__)


class Watchdog(object):
    def destruct(self):
        raise NotImplementedError('Subclasses must override')

    def reset(self):
        raise NotImplementedError('Subclasses must override')

    def watch(self):
        raise NotImplementedError('Subclasses must override')


class WatchdogWindows(Watchdog, threading.Thread):
    """ Simple watchdog for Windows (relies on psutil) """
    def __init__(self, duration):
        self._duration = int(duration)

        threading.Thread.__init__(self)
        self.tlock = threading.RLock()
        self.reset()
        self.start()

    def destruct(self):
        try:
            log.error("Self-destructing...")
            log.error(traceback.format_exc())
        finally:
            # This will kill the current process including the Watchdog's thread
            psutil.Process().kill()

    def reset(self):
        log.debug("Resetting watchdog for %d" % self._duration)
        with self.tlock:
            self.expire_at = time.time() + self._duration

    def watch(self):
        while True:
            if time.time() > self.expire_at:
                self.destruct()
            time.sleep(self._duration/20)


class WatchdogPosix(Watchdog):
    """Simple signal-based watchdog that will scuttle the current process
    if it has not been reset every N seconds, or if the processes exceeds
    a specified memory threshold.
    Can only be invoked once per process, so don't use with multiple threads.
    If you instantiate more than one, you're also asking for trouble.
    """
    def __init__(self, duration, max_mem_mb=None):
        # Set the duration
        self._duration = int(duration)
        signal.signal(signal.SIGALRM, WatchdogPosix.self_destruct)

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
            log.error("Self-destructing...")
            log.error(traceback.format_exc())
        finally:
            os.kill(os.getpid(), signal.SIGKILL)

    def destruct(self):
        WatchdogPosix.self_destruct(None, None)

    def reset(self):
        # self destruct if using too much memory, as tornado will swallow MemoryErrors
        if self.memory_limit_enabled:
            mem_usage_kb = int(os.popen('ps -p %d -o %s | tail -1' % (os.getpid(), 'rss')).read())
            if mem_usage_kb > (0.95 * self._max_mem_kb):
                self.destruct()

        log.debug("Resetting watchdog for %d" % self._duration)
        signal.alarm(self._duration)


def new_watchdog(duration, max_mem_mb=None):
    if Platform.is_windows():
        return WatchdogWindows(duration)
    else:
        return WatchdogPosix(duration, max_mem_mb=max_mem_mb)
