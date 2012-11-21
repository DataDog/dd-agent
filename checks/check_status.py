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


class AgentStatus(object):
    """ 
    A small class used to load and save status messages to the filesystem.
    """

    def __init__(self):
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
            log.exception("Error persisting status")

    def created_seconds_ago(self):
        td = datetime.datetime.now() - self.created_at
        return td.seconds

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
        return os.path.join(tempfile.gettempdir(), cls._get_filename())

    @classmethod
    def _get_filename(cls):
        raise NotImplementedError


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

class EmitterStatus(object):

    def __init__(self, name, error=None):
        self.name = name
        self.error = None
        if error:
            self.error = repr(error)

    @property
    def status(self):
        if self.error:
            return STATUS_ERROR
        else:
            return STATUS_OK


class CollectorStatus(AgentStatus):

    def __init__(self, check_statuses=None, emitter_statuses=None):
        AgentStatus.__init__(self)
        self.check_statuses = check_statuses or []
        self.emitter_statuses = emitter_statuses or []

    @classmethod
    def _get_filename(cls):
        return 'collector_status.pickle'

    def print_status(self):
        lines = [
            "",
            "Collector",
            "=========",
            "Status date: %s (%ss ago)" % (self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                                            self.created_seconds_ago()),
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

        lines.append("")
        lines.append("Emitters")
        lines.append("------")
        if not self.emitter_statuses:
            lines.append("No emitters have run yet.")
        else:
            for es in self.emitter_statuses:
                line = "  - %s [%s]" % (es.name, es.status)
                if es.status != STATUS_OK:
                    line += ": %s" % es.error
                lines.append(line)

        print "\n".join(lines)

    @classmethod
    def print_latest_status(cls):
        collector_status = cls.load_latest_status()
        if not collector_status:
            print "The agent is not running."
        else:
            collector_status.print_status()


