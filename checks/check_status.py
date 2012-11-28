"""
This module contains classes which are used to occasionally persist the status
of checks.
"""

# stdlib
import datetime
import logging
import os
import pickle
import platform
import sys
import tempfile

# project
import config


STATUS_OK = 'OK'
STATUS_ERROR = 'ERROR'


log = logging.getLogger(__name__)


class Stylizer(object):

    STYLES = {
        'bold'    : 1,
        'grey'    : 30, 
        'red'     : 31,
        'green'   : 32,
        'yellow'  : 33,
        'blue'    : 34,
        'magenta' : 35,
        'cyan'    : 36,
        'white'   : 37,
    }

    HEADER = '\033[1m'
    UNDERLINE = '\033[2m'

    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    RESET = '\033[0m'


    def __init__(self):
        self.enabled = True

    def stylize(self, text, *styles):
        """ stylize the text. """
        if not self.enabled:
            return text
        # don't bother about escaping, not that complicated.
        fmt = '\033[%dm%s'

        for style in styles or []:
            text = fmt % (self.STYLES[style], text)

        return text + fmt % (0, '') # reset

    def disabled(self):
        self.enabled = False

    def bold(self, text):
        return self.s(text, 'bold')


class AgentStatus(object):
    """ 
    A small class used to load and save status messages to the filesystem.
    """

    NAME = None
    STYLIZER = Stylizer()
    
    def __init__(self):
        self.created_at = datetime.datetime.now()
        self.created_by_pid = os.getpid()

    def style(self, text, *args):
        return self.STYLIZER.stylize(text, *args)

    def persist(self):
        try:
            path = self._get_pickle_path()
            log.debug("Persisting status to %s" % path)
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

    def _header_lines(self):
        name_line = "%s (v %s)" % (self.NAME, config.get_version())
        lines = [
            "",
            "=" * len(name_line),
            "%s" % name_line,
            "=" * len(name_line),
        ]

        fields = [
            ("Status date", "%s (%ss ago)" % (self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                                            self.created_seconds_ago())),
            ("Pid", self.created_by_pid),
            ("Platform", sys.platform),
            ("Python Version", platform.python_version()),
        ]

        for key, value in fields:
            l = "%s: %s" % (key, value)
            lines.append(l)
        return lines + ["\n"]


    @classmethod
    def remove_latest_status(cls):
        log.debug("Removing latest status")
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
    def print_latest_status(cls):
        collector_status = cls.load_latest_status()
        if not collector_status:
            print "%s is not running." % cls.NAME
        else:
            collector_status.print_status() 
            print "\n"


    @classmethod
    def _get_pickle_path(cls):
        return os.path.join(tempfile.gettempdir(), cls.__name__ + '.pickle')


class InstanceStatus(object):

    def __init__(self, instance_id, status, error=None):
        self.instance_id = instance_id
        self.status = status
        self.error = repr(error)

    def has_error(self):
        return self.status != STATUS_OK


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

    def has_error(self):
        return self.status != STATUS_OK


class CollectorStatus(AgentStatus):

    NAME = 'Collector'

    def __init__(self, check_statuses=None, emitter_statuses=None):
        AgentStatus.__init__(self)
        self.check_statuses = check_statuses or []
        self.emitter_statuses = emitter_statuses or []

    def print_status(self):
        lines = self._header_lines()

        lines.append("Checks")
        lines.append("------")
        if not self.check_statuses:
            lines.append("No checks have run yet.")
        else:
            for cs in self.check_statuses:
                check_lines = [
                    cs.name
                ]
                for s in cs.instance_statuses:
                    c = 'green'
                    if s.has_error():
                        c = 'red'
                    line =  "  - instance #%s [%s]" % (
                             s.instance_id, self.style(s.status, c))
                    if s.has_error():
                        line += u": %s" % s.error
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
                c = 'green'
                if es.has_error():
                    c = 'red'
                line = "  - %s [%s]" % (es.name, self.style(es.status,c))
                if es.status != STATUS_OK:
                    line += ": %s" % es.error
                lines.append(line)

        print "\n".join(lines)


class DogstatsdStatus(AgentStatus):

    NAME = 'Dogstatsd'
    
    def __init__(self, flush_count=0, packet_count=0, packets_per_second=0, metric_count=0):
        AgentStatus.__init__(self)
        self.flush_count = flush_count
        self.packet_count = packet_count
        self.packets_per_second = packets_per_second
        self.metric_count = metric_count


    def print_status(self):
        lines = self._header_lines() + [
            "Flush count: %s" % self.flush_count,
            "Packet Count: %s" % self.packet_count,
            "Packets per second: %s" % self.packets_per_second,
            "Metric count: %s" % self.metric_count,
        ]
        print "\n".join(lines)


class ForwarderStatus(AgentStatus):

    NAME = 'Forwarder'

    def __init__(self, queue_length=0, queue_size=0, flush_count=0):
        AgentStatus.__init__(self)
        self.queue_length = queue_length
        self.queue_size = queue_size
        self.flush_count = flush_count

    def print_status(self):
        lines = self._header_lines() + [
            "Queue Size: %s" % self.queue_size,
            "Queue Length: %s" % self.queue_length,
            "Flush Count: %s" % self.flush_count,
        ]
        print "\n".join(lines)
        


