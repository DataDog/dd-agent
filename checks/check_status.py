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


log = logging.getLogger(__name__)


class InstanceStatus(object):

    def __init__(self, instance_id, status, error=None):
        self.instance_id = instance_id
        self.status = status
        self.error = repr(error)


class CheckStatus(object):
    
    def __init__(self, check_name, instance_statuses, metric_count, event_count):
        self.name = check_name
        self.instance_statuses = instance_statuses
        self.metric_count = metric_count
        self.event_count = event_count

    @property
    def status(self):
        for instance_status in self.instance_statuses:
            if instance_status.status == STATUS_ERROR:
                return STATUS_ERROR
        return STATUS_OK


class CollectorStatus(object):

    def __init__(self, check_statuses=None):
        self.check_statuses = check_statuses or []
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
        td = datetime.datetime.now() - self.created_at
        lines = [
            "",
            "Collector",
            "=========",
            "Status date: %s (%ss ago)" % (self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                                            td.seconds),
            "Version: %s" % config.get_version(),
            "Pid: %s" % self.created_by_pid,
            "Platform: %s" % sys.platform,
            "Python Version: %s" % platform.python_version(),
            ""
        ]

        lines.append("Checks")
        lines.append("------")
        if not self.check_statuses:
            lines.append("No checks have run yet.")
        else:
            for cs in self.check_statuses:
                check_lines = [
                    cs.name
                ]
                for instance_status in cs.instance_statuses:
                    line =  "  - instance #%s [%s]" % (
                             instance_status.instance_id, instance_status.status)
                    if instance_status.status != STATUS_OK:
                        line += u": %s" % instance_status.error
                    check_lines.append(line)
                check_lines += [
                    "  - Collected %s metrics & %s events" % (cs.metric_count, cs.event_count),
                ]
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

