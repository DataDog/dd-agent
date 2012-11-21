"""
This module contains classes which are used to occasionally persist the status
of checks.
"""

import datetime
import logging
import os
import pickle
import platform
import sys
import tempfile

import config


STATUS_OK = 'OK'
STATUS_ERROR = 'ERROR'
STATUS_NO_DATA = 'NO DATA'


log = logging.getLogger(__name__)


class InstanceStatus(object):

    def __init__(self, instance_id, status, error=None):
        self.instance_id = instance_id
        self.status = status
        self.error = error


class CheckStatus(object):
    
    def __init__(self, check_name, instance_statuses, has_data=False):
        self.name = check_name
        self.instance_statuses = instance_statuses
        self.has_data = has_data

    @property
    def status(self):
        if not self.has_data:
            return STATUS_NO_DATA
        for instance_status in self.instance_statuses:
            if instance_status.status == STATUS_ERROR:
                return STATUS_ERROR
        return STATUS_OK


class CollectorStatus(object):

    def __init__(self, check_statuses=None, start_up=False):
        self.check_statuses = check_statuses or []
        self.start_up = start_up
        self.created_at = datetime.datetime.now()
        self.created_by_pid = os.getpid()

    def persist(self):
        path = self._get_pickle_path()
        log.debug("Persisting status to %s" % path)
        try:
            f = open(path, 'w')
            try:
                pickle.dump(self, f)
            finally:
                f.close()
        except Exception:
            log.exception("Error persisting collector status")

    def print_status(self):
        lines = [
            "",
            "Collector",
            "=========",
            "Status date: %s" % self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "Version: %s" % config.get_version(),
            "Pid: %s" % self.created_by_pid,
            "Platform: %s" % sys.platform,
            "Python Version: %s" % platform.python_version(),
            ""
        ]

        if self.start_up and not self.check_statuses:
            lines.append("No checks have run yet.")
        else:
            lines.append("Checks")
            lines.append("------")
            for check_status in self.check_statuses:
                check_lines = [
                    check_status.name
                ]
                for instance_status in check_status.instance_statuses:
                    check_lines.append("  instance #%s [%s]" %
                    (instance_status.instance_id, instance_status.status))
                lines += check_lines
        print "\n".join(lines)

    @classmethod
    def print_latest_status(cls):
        collector_status = cls.load_latest_status()
        if not collector_status:
            print "The agent is not running."
        else:
            collector_status.print_status()

    @classmethod
    def remove_latest_status(cls):
        log.debug("Removing latest collector status")
        try:
            os.remove(cls._get_pickle_path())
        except OSError:
            pass

    @classmethod
    def load_latest_status(cls):
        try:
            f = open(cls._get_pickle_path())
            try:
                return pickle.load(f)
            finally:
                f.close()
        except IOError:
            log.info("Couldn't load latest status")
            return None

    @classmethod
    def _get_pickle_path(cls):
        return os.path.join(tempfile.gettempdir(), 'collector_status.pickle')

