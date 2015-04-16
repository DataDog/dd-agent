import logging
import os.path
import tempfile

from utils.platform import Platform

log = logging.getLogger(__name__)


class PidFile(object):
    """ A small helper class for pidfiles. """

    PID_DIR = '/var/run/dd-agent'

    def __init__(self, program, pid_dir=None):
        self.pid_file = "%s.pid" % program
        self.pid_dir = pid_dir or self.get_default_pid_dir()
        self.pid_path = os.path.join(self.pid_dir, self.pid_file)

    def get_default_pid_dir(self):
        if not Platform.is_windows():
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
