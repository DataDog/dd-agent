# std
import logging
import os
import tempfile
import time

# 3rd party
import yaml

# datadog
from config import _windows_commondata_path
from util import yDumper
from utils.pidfile import PidFile
from utils.platform import Platform


log = logging.getLogger(__name__)


class JMXFiles(object):
    """
    A small helper class for JMXFetch status & exit files.
    """
    _STATUS_FILE = 'jmx_status.yaml'
    _PYTHON_STATUS_FILE = 'jmx_status_python.yaml'
    _JMX_EXIT_FILE = 'jmxfetch_exit'

    @classmethod
    def _get_dir(cls):
        if Platform.is_win32():
            path = os.path.join(_windows_commondata_path(), 'Datadog')
        elif os.path.isdir(PidFile.get_dir()):
            path = PidFile.get_dir()
        else:
            path = tempfile.gettempdir()
        return path

    @classmethod
    def _get_file_path(cls, file):
        return os.path.join(cls._get_dir(), file)

    @classmethod
    def get_status_file_path(cls):
        return cls._get_file_path(cls._STATUS_FILE)

    @classmethod
    def get_python_status_file_path(cls):
        return cls._get_file_path(cls._PYTHON_STATUS_FILE)

    @classmethod
    def get_python_exit_file_path(cls):
        return cls._get_file_path(cls._JMX_EXIT_FILE)

    @classmethod
    def write_status_file(cls, invalid_checks):
        data = {
            'timestamp': time.time(),
            'invalid_checks': invalid_checks
        }
        stream = file(os.path.join(cls._get_dir(), cls._PYTHON_STATUS_FILE), 'w')
        yaml.dump(data, stream, Dumper=yDumper)
        stream.close()

    @classmethod
    def write_exit_file(cls):
        """
        Create a 'special' file, which acts as a trigger to exit JMXFetch.
        Note: Windows only
        """
        open(os.path.join(cls._get_dir(), cls._JMX_EXIT_FILE), 'a').close()

    @classmethod
    def clean_status_file(cls):
        """
        Removes JMX status files
        """
        try:
            os.remove(os.path.join(cls._get_dir(), cls._STATUS_FILE))
        except OSError:
            pass
        try:
            os.remove(os.path.join(cls._get_dir(), cls._PYTHON_STATUS_FILE))
        except OSError:
            pass

    @classmethod
    def clean_exit_file(cls):
        """
        Remove exit file trigger -may not exist-.
        Note: Windows only
        """
        try:
            os.remove(os.path.join(cls._get_dir(), cls._JMX_EXIT_FILE))
        except OSError:
            pass

    @classmethod
    def get_jmx_appnames(cls):
        """
        Retrieves the running JMX checks based on the {tmp}/jmx_status.yaml file
        updated by JMXFetch (and the only communication channel between JMXFetch
        and the collector since JMXFetch).
        """
        check_names = []
        jmx_status_path = os.path.join(cls._get_dir(), cls._STATUS_FILE)
        if os.path.exists(jmx_status_path):
            jmx_checks = yaml.load(file(jmx_status_path)).get('checks', {})
            check_names = [name for name in jmx_checks.get('initialized_checks', {}).iterkeys()]
        return check_names
