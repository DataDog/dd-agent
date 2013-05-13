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
import traceback

# project
import config

STATUS_OK = 'OK'
STATUS_ERROR = 'ERROR'
STATUS_WARNING = 'WARNING'


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


    ENABLED = False

    @classmethod
    def stylize(cls, text, *styles):
        """ stylize the text. """
        if not cls.ENABLED:
            return text
        # don't bother about escaping, not that complicated.
        fmt = '\033[%dm%s'

        for style in styles or []:
            text = fmt % (cls.STYLES[style], text)

        return text + fmt % (0, '') # reset


# a small convienence method
def style(*args):
    return Stylizer.stylize(*args)

def logger_info():
    loggers = []
    root_logger = logging.getLogger()
    if len(root_logger.handlers) > 0:
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                loggers.append(handler.stream.name)
            if isinstance(handler, logging.handlers.SysLogHandler):
                if isinstance(handler.address, basestring):
                    loggers.append('syslog:%s' % handler.address)
                else:
                    loggers.append('syslog:(%s, %s)' % handler.address)
    else:
        loggers.append("No loggers configured")
    return ', '.join(loggers)

class AgentStatus(object):
    """ 
    A small class used to load and save status messages to the filesystem.
    """

    NAME = None
    
    def __init__(self):
        self.created_at = datetime.datetime.now()
        self.created_by_pid = os.getpid()

    def has_error(self):
        raise NotImplementedError

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

    def render(self):
        indent = "  "
        lines = self._header_lines(indent) + [
            indent + l for l in self.body_lines()
        ] + ["", ""]
        return "\n".join(lines)

    @classmethod
    def _title_lines(self):
        name_line = "%s (v %s)" % (self.NAME, config.get_version())
        lines = [
            "=" * len(name_line),
            "%s" % name_line,
            "=" * len(name_line),
            "",
        ]
        return lines
        
    def _header_lines(self, indent):
        # Don't indent the header
        lines = self._title_lines()
        if self.created_seconds_ago() > 120:
            styles = ['red','bold']
        else:
            styles = []
        # We color it in red if the status is too old
        fields = [
            (
                style("Status date", *styles),
                style("%s (%ss ago)" %
                    (self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                                        self.created_seconds_ago()), *styles)
            )
        ]

        fields += [
            ("Pid", self.created_by_pid),
            ("Platform", platform.platform()),
            ("Python Version", platform.python_version()),
            ("Logs", logger_info()),
        ]

        for key, value in fields:
            l = indent + "%s: %s" % (key, value)
            lines.append(l)
        return lines + [""]

    def to_dict(self):
        return {
            'pid': self.created_by_pid,
            'status_date': "%s (%ss ago)" % (self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                                        self.created_seconds_ago()),
            }

    @classmethod
    def _not_running_message(cls):
        lines = cls._title_lines() + [
            style("  %s is not running." % cls.NAME, 'red'),
            style("""  You can get more informations in the logs: 
    %s""" % logger_info(), 'red'),
            "",
            ""
        ]
        return "\n".join(lines)


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
    def print_latest_status(cls, verbose=False):
        cls.verbose = verbose
        Stylizer.ENABLED = False
        try:
            if sys.stdout.isatty():
                Stylizer.ENABLED = True
        except Exception:
            # Don't worry if we can't enable the
            # stylizer.
            pass

        message = cls._not_running_message()
        exit_code = -1

        module_status = cls.load_latest_status()
        if module_status:
            message = module_status.render()
            exit_code = 0
            if module_status.has_error():
                exit_code = 1

        sys.stdout.write(message)
        return exit_code

    @classmethod
    def _get_pickle_path(cls):
        return os.path.join(tempfile.gettempdir(), cls.__name__ + '.pickle')


class InstanceStatus(object):

    def __init__(self, instance_id, status, error=None, tb=None, warnings=None):
        self.instance_id = instance_id
        self.status = status
        self.error = repr(error)
        self.traceback = tb
        self.warnings = warnings

    def has_error(self):
        return self.status == STATUS_ERROR

    def has_warnings(self):
        return self.status == STATUS_WARNING

class CheckStatus(object):

    def __init__(self, check_name, instance_statuses, metric_count,
                 event_count, init_failed=False, init_failed_exception=None,
                 init_failed_traceback=None):
        self.name = check_name
        self.instance_statuses = instance_statuses
        self.metric_count = metric_count
        self.event_count = event_count
        self.init_failed = init_failed
        self.init_failed_exception = init_failed_exception
        self.init_failed_traceback = init_failed_traceback

    @property
    def status(self):
        if self.init_failed:
            return STATUS_ERROR
        for instance_status in self.instance_statuses:
            if instance_status.status == STATUS_ERROR:
                return STATUS_ERROR
        return STATUS_OK

    def has_error(self):
        return self.status == STATUS_ERROR


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

    def __init__(self, check_statuses=None, emitter_statuses=None, metadata=None):
        AgentStatus.__init__(self)
        self.check_statuses = check_statuses or []
        self.emitter_statuses = emitter_statuses or []
        self.metadata = metadata or []

    @property
    def status(self):
        for check_status in self.check_statuses:
            if check_status.status == STATUS_ERROR:
                return STATUS_ERROR
        return STATUS_OK

    def has_error(self):
        return self.status != STATUS_OK

    def body_lines(self):
        # Metadata whitelist
        metadata_whitelist = [
            'hostname',
            'fqdn',
            'ipv4',
            'instance-id'
        ]

        # Hostnames
        lines = [
            'Hostnames',
            '=========',
            ''
        ]
        if not self.metadata:
            lines.append("  No host information available yet.")
        else:
            for key, host in self.metadata.items():
                for whitelist_item in metadata_whitelist:
                    if whitelist_item in key:
                        lines.append("  " + key + ": " + host)
                        break

        lines.append('')

        # Checks.d Status
        lines += [
            'Checks',
            '======',
            ''
        ]
        if not self.check_statuses:
            lines.append("  No checks have run yet.")
        else:
            for cs in self.check_statuses:
                check_lines = [
                    '  ' + cs.name,
                    '  ' + '-' * len(cs.name)
                ]
                if cs.init_failed:
                    check_lines.append("    - initialize check class [%s]: %s" %
                                       (style(STATUS_ERROR, 'red'),
                                       repr(cs.init_failed_exception)))
                    if self.verbose and cs.init_failed_traceback:
                        check_lines.extend('      ' + line for line in
                                           cs.init_failed_traceback.split('\n'))
                else:
                    check_lines.append("    - initialize check class [%s]" %
                            style(STATUS_OK, 'green'))
                    for s in cs.instance_statuses:
                        c = 'green'
                        if s.has_warnings():
                            c = 'yellow'
                        if s.has_error():
                            c = 'red'
                        line =  "    - instance #%s [%s]" % (
                                 s.instance_id, style(s.status, c))
                        if s.has_error():
                            line += u": %s" % s.error

                        check_lines.append(line)

                        if s.has_warnings():
                            for warning in s.warnings:
                                check_lines.append(u"         %s: %s" % (style("Warning", 'yellow'), warning))

                        if self.verbose and s.traceback is not None:
                            check_lines.extend('      ' + line for line in
                                           s.traceback.split('\n'))

                    check_lines += [
                        "    - Collected %s metrics & %s events" % (cs.metric_count, cs.event_count),
                        ""
                    ]

                lines += check_lines

        # Emitter status
        lines += [
            "",
            "Emitters",
            "========",
            ""
        ]
        if not self.emitter_statuses:
            lines.append("  No emitters have run yet.")
        else:
            for es in self.emitter_statuses:
                c = 'green'
                if es.has_error():
                    c = 'red'
                line = "  - %s [%s]" % (es.name, style(es.status,c))
                if es.status != STATUS_OK:
                    line += ": %s" % es.error
                lines.append(line)

        return lines

    def to_dict(self):
        status_info = AgentStatus.to_dict(self)

        # Hostnames
        status_info['hostnames'] = {}
        metadata_whitelist = [
            'hostname',
            'fqdn',
            'ipv4',
            'instance-id'
        ]
        if self.metadata:
            for key, host in self.metadata.items():
                for whitelist_item in metadata_whitelist:
                    if whitelist_item in key:
                        status_info['hostnames'][key] = host
                        break

        # Checks.d Status
        status_info['checks'] = {}
        for cs in self.check_statuses:
            status_info['checks'][cs.name] = {'instances': {}}
            for s in cs.instance_statuses:
                status_info['checks'][cs.name]['instances'][s.instance_id] = {
                    'status': s.status,
                    'has_error': s.has_error(),
                    'has_warnings': s.has_warnings(),
                }
                if s.has_error():
                    status_info['checks'][cs.name]['instances'][s.instance_id]['error'] = s.error
                if s.has_warnings():
                    status_info['checks'][cs.name]['instances'][s.instance_id]['warnings'] = s.warnings
            status_info['checks'][cs.name]['metric_count'] = cs.metric_count
            status_info['checks'][cs.name]['event_count'] = cs.event_count

        # Emitter status
        status_info['emitter'] = []
        for es in self.emitter_statuses:
            check_status = {
                'name': es.name,
                'status': es.status,
                'has_error': es.has_error(),
                }
            if es.has_error():
                check_status['error'] = es.error
            status_info['emitter'].append(check_status)

        return status_info


class DogstatsdStatus(AgentStatus):

    NAME = 'Dogstatsd'

    def __init__(self, flush_count=0, packet_count=0, packets_per_second=0, 
        metric_count=0):
        AgentStatus.__init__(self)
        self.flush_count = flush_count
        self.packet_count = packet_count
        self.packets_per_second = packets_per_second
        self.metric_count = metric_count

    def has_error(self):
        return self.flush_count == 0 and self.packet_count == 0 and self.metric_count == 0

    def body_lines(self):
        lines = [
            "Flush count: %s" % self.flush_count,
            "Packet Count: %s" % self.packet_count,
            "Packets per second: %s" % self.packets_per_second,
            "Metric count: %s" % self.metric_count,
        ]
        return lines

    def to_dict(self):
        status_info = AgentStatus.to_dict(self)
        status_info.update({
            'flush_count': self.flush_count,
            'packet_count': self.packet_count,
            'packets_per_second': self.packets_per_second,
            'metric_count': self.metric_count,
        })
        return status_info


class ForwarderStatus(AgentStatus):

    NAME = 'Forwarder'

    def __init__(self, queue_length=0, queue_size=0, flush_count=0):
        AgentStatus.__init__(self)
        self.queue_length = queue_length
        self.queue_size = queue_size
        self.flush_count = flush_count

    def body_lines(self):
        lines = [
            "Queue Size: %s" % self.queue_size,
            "Queue Length: %s" % self.queue_length,
            "Flush Count: %s" % self.flush_count,
        ]
        return lines

    def has_error(self):
        return self.flush_count == 0

    def to_dict(self):
        status_info = AgentStatus.to_dict(self)
        status_info.update({
            'flush_count': self.flush_count,
            'queue_length': self.queue_length,
            'queue_size': self.queue_size,
        })
        return status_info
