"""
    ***
    Modified generic daemon class
    ***

    Author:     http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
                www.boxedice.com
                www.datadoghq.com

    License:    http://creativecommons.org/licenses/by-sa/3.0/
"""

# Core modules
import atexit
import logging
import os
import sys

# project
from utils.process import is_my_process

log = logging.getLogger(__name__)


class AgentProcess(object):
    """
    An agent process.

    Class doing some wrapping around the pidfile.
    """
    def __init__(self, pidfile, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def start(self):
        log.info("Starting")
        pid = self.pid()

        if pid:
            # Check if the pid in the pidfile corresponds to a running process
            # and if psutil is installed, check if it's a datadog-agent one
            if is_my_process(pid):
                log.error("Not starting, another instance is already running"
                          " (using pidfile {0})".format(self.pidfile))
                sys.exit(1)
            else:
                log.warn("pidfile doesn't contain the pid of an agent process."
                         ' Starting normally')

        self.write_pidfile()
        self.run()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        raise NotImplementedError

    @classmethod
    def info(cls):
        """
        You should override this method when you subclass Daemon. It will be
        called to provide information about the status of the process
        """
        raise NotImplementedError

    def pid(self):
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
            return pid
        except IOError:
            return None
        except ValueError:
            return None

    def write_pidfile(self):
        # Write pidfile
        atexit.register(self.delpid)  # Make sure pid file is removed if we quit
        pid = str(os.getpid())
        try:
            fp = open(self.pidfile, 'w+')
            fp.write(str(pid))
            fp.close()
            os.chmod(self.pidfile, 0644)
        except Exception:
            msg = "Unable to write pidfile: %s" % self.pidfile
            log.exception(msg)
            sys.stderr.write(msg + "\n")
            sys.exit(1)

    def delpid(self):
        try:
            os.remove(self.pidfile)
        except OSError:
            pass
