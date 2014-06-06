import time
import re
from util import namedtuple, get_hostname
from checks.utils import TailFile
from checks import AgentCheck

# Event types we know about but decide to ignore in the parser
IGNORE_EVENT_TYPES = []

# fields order for each event type, as named tuples
EVENT_FIELDS = {
    'CURRENT HOST STATE':       namedtuple('E_CurrentHostState', 'host, event_state, event_soft_hard, return_code, payload'),
    'CURRENT SERVICE STATE':    namedtuple('E_CurrentServiceState', 'host, check_name, event_state, event_soft_hard, return_code, payload'),
    'SERVICE ALERT':            namedtuple('E_ServiceAlert', 'host, check_name, event_state, event_soft_hard, return_code, payload'),
    'PASSIVE SERVICE CHECK':    namedtuple('E_PassiveServiceCheck', 'host, check_name, return_code, payload'),
    'HOST ALERT':               namedtuple('E_HostAlert', 'host, event_state, event_soft_hard, return_code, payload'),

    # [1305744274] SERVICE NOTIFICATION: ops;ip-10-114-237-165;Metric ETL;ACKNOWLEDGEMENT (CRITICAL);notify-service-by-email;HTTP CRITICAL: HTTP/1.1 503 Service Unavailable - 394 bytes in 0.010 second response time;datadog;alq
    'SERVICE NOTIFICATION':     namedtuple('E_ServiceNotification', 'contact, host, check_name, event_state, notification_type, payload'),

    # [1296509331] SERVICE FLAPPING ALERT: ip-10-114-97-27;cassandra JVM Heap;STARTED; Service appears to have started flapping (23.4% change >= 20.0% threshold)
    # [1296662511] SERVICE FLAPPING ALERT: ip-10-114-97-27;cassandra JVM Heap;STOPPED; Service appears to have stopped flapping (3.8% change < 5.0% threshold)
    'SERVICE FLAPPING ALERT':   namedtuple('E_FlappingAlert', 'host, check_name, flap_start_stop, payload'),

    # Reference for external commands: http://old.nagios.org/developerinfo/externalcommands/commandlist.php
    # Command Format:
    # ACKNOWLEDGE_SVC_PROBLEM;<host_name>;<service_description>;<sticky>;<notify>;<persistent>;<author>;<comment>
    # [1305832665] EXTERNAL COMMAND: ACKNOWLEDGE_SVC_PROBLEM;ip-10-202-161-236;Resources ETL;2;1;0;datadog;alq checking
    'ACKNOWLEDGE_SVC_PROBLEM': namedtuple('E_ServiceAck', 'host, check_name, sticky_ack, notify_ack, persistent_ack, ack_author, payload'),

    # Command Format:
    # ACKNOWLEDGE_HOST_PROBLEM;<host_name>;<sticky>;<notify>;<persistent>;<author>;<comment>
    'ACKNOWLEDGE_HOST_PROBLEM': namedtuple('E_HostAck', 'host, sticky_ack, notify_ack, persistent_ack, ack_author, payload'),

    # Host Downtime
    # [1297894825] HOST DOWNTIME ALERT: ip-10-114-89-59;STARTED; Host has entered a period of scheduled downtime
    # [1297894825] SERVICE DOWNTIME ALERT: ip-10-114-237-165;intake;STARTED; Service has entered a period of scheduled downtime

    'HOST DOWNTIME ALERT': namedtuple('E_HostDowntime', 'host, downtime_start_stop, payload'),
    'SERVICE DOWNTIME ALERT': namedtuple('E_ServiceDowntime', 'host, check_name, downtime_start_stop, payload'),
}

# Regex alternation ends up being tricker than expected, and much less readable
#re_line = re.compile('^\[(\d+)\] (?:EXTERNAL COMMAND: (\w+);)|(?:([^:]+): )(.*)$')
re_line_reg = re.compile('^\[(\d+)\] EXTERNAL COMMAND: (\w+);(.*)$')
re_line_ext = re.compile('^\[(\d+)\] ([^:]+): (.*)$')


class Nagios(AgentCheck):


    def __init__(self, name, init_config, agentConfig, instances=None):
        # Override the name or the events don't make it
        AgentCheck.__init__(self, 'Nagios', init_config, agentConfig, instances)
        self.nagios_tails = {}
        hostname = get_hostname(agentConfig)
        if instances is not None:
            for instance in instances:
                if 'nagios_conf' in instance:
                    conf_path = instance['nagios_conf']
                    nagios_conf = self.parse_nagios_config(conf_path)
                    tailers = []
                    if ('log_file' in nagios_conf) and instance.get('events',False):
                        tailers.append(NagiosEventLogTailer(nagios_conf['log_file'],
                                                            None,
                                                            self.log,
                                                            hostname,
                                                            self.event,
                                                            self.gauge))
                    if ('host_perfdata_file' in nagios_conf) and \
                       ('host_perfdata_file_template' in nagios_conf) and \
                       instance.get('host_perf', False):
                        tailers.append(NagiosHostPerfDataTailer(nagios_conf['host_perfdata_file'],
                                                                nagios_conf['host_perfdata_file_template'],
                                                                self.log,
                                                                hostname,
                                                                self.event,
                                                                self.gauge))
                    if ('service_perfdata_file' in nagios_conf) and \
                       ('service_perfdata_file_template' in nagios_conf) and \
                       instance.get('service_perf', False):
                        tailers.append(NagiosServicePerfDataTailer(nagios_conf['service_perfdata_file'],
                                                                nagios_conf['service_perfdata_file_template'],
                                                                self.log,
                                                                hostname,
                                                                self.event,
                                                                self.gauge))
                    self.nagios_tails[conf_path] = tailers

    @classmethod
    def parse_nagios_config(cls, filename):
        output = {}
        keys = [
            'log_file',
            'host_perfdata_file_template',
            'service_perfdata_file_template',
            'host_perfdata_file',
            'service_perfdata_file',
        ]

        f = None
        try:
            try:
                f = open(filename)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    for key in keys:
                        if line.startswith(key + '='):
                            eq_pos = line.find('=')
                            if eq_pos:
                                output[key] = line[eq_pos + 1:]
                                break
                return output
            except Exception:
                # Can't parse, assume it's just not working
                # Don't return an incomplete config
                return {}
        finally:
            if f is not None:
                f.close()


    def check(self, instance):
        if 'nagios_conf' not in instance:
            self.log.info("Skipping Instance, no log file found")
        for tailer in self.nagios_tails[instance['nagios_conf']]:
            tailer.check()

class NagiosTailer(object):

    def __init__(self, log_path, file_template, logger, hostname, event_func, gauge_func):
        self.log_path = log_path
        self.logger = logger
        self.gen = None
        self.tail = None
        self.hostname = hostname
        self._event = event_func
        self._gauge = gauge_func
        self._line_parsed = 0
        self._event_sent = 0

        if file_template is not None:
            self.compile_file_template(file_template)

        self.tail = TailFile(self.logger,self.log_path,self._parse_line)
        self.gen = self.tail.tail(line_by_line=False, move_end=True)
        self.gen.next()

    def check(self):
        self._event_sent = 0
        self._line_parsed = 0

        # read until the end of file
        try:
            self.logger.debug("Start nagios check for file %s" % (self.log_path))
            self.tail._log = self.logger
            self.gen.next()
            self.logger.debug("Done nagios check for file %s (parsed %s line(s), generated %s event(s))" %
                (self.log_path,self._line_parsed, self._event_sent))
        except StopIteration, e:
            self.logger.exception(e)
            self.logger.warning("Can't tail %s file" % (self.log_path))

    def compile_file_template(self, file_template):
        try:
            # Escape characters that will be interpreted as regex bits
            # e.g. [ and ] in "[SERVICEPERFDATA]"
            regex = re.sub(r'[[\]*]', r'.', file_template)
            regex = re.sub(r'\$([^\$]*)\$', r'(?P<\1>[^\$]*)', regex)
            self.line_pattern = re.compile(regex)
        except Exception, e:
            raise InvalidDataTemplate("%s (%s)"% (file_template, e))


class NagiosEventLogTailer(NagiosTailer):

    def _parse_line(self, line):
        """Actual nagios parsing
        Return True if we found an event, False otherwise
        """
        # first isolate the timestamp and the event type
        try:
            self._line_parsed = self._line_parsed + 1

            m  = re_line_reg.match(line)
            if m is None:
                m = re_line_ext.match(line)
            if m is None:
                return False

            (tstamp, event_type, remainder) = m.groups()
            tstamp = int(tstamp)

            if event_type in IGNORE_EVENT_TYPES:
                self.logger.info("Ignoring nagios event of type %s" % (event_type))
                return False

            # then retrieve the event format for each specific event type
            fields = EVENT_FIELDS.get(event_type, None)
            if fields is None:
                self.logger.warning("Ignoring unknown nagios event for line: %s" % (line[:-1]))
                return False

            # and parse the rest of the line
            parts = map(lambda p: p.strip(), remainder.split(';'))
            # Chop parts we don't recognize
            parts = parts[:len(fields._fields)]

            event = self.create_event(tstamp, event_type, self.hostname, fields._make(parts))

            self._event(event)
            self._event_sent += 1
            self.logger.debug("Nagios event: %s" % (event))

            return True
        except Exception:
            self.logger.exception("Unable to create a nagios event from line: [%s]" % (line))
            return False

    def create_event(self,timestamp, event_type, hostname, fields):
        """Factory method called by the parsers
        """
        # FIXME Oli: kind of ugly to have to go through a named dict for this, and inefficient too
        # but couldn't think of anything smarter
        d = fields._asdict()
        d.update({ 'timestamp': timestamp, 'event_type': event_type })
        # if host is localhost, turn that into the internal host name
        host = d.get('host', None)
        if host == "localhost":
            d["host"] = hostname
        return d

class NagiosPerfDataTailer(NagiosTailer):
    perfdata_field = '' # Should be overriden by subclasses
    metric_prefix = 'nagios'
    pair_pattern = re.compile(r"".join([
            r"'?(?P<label>[^=']+)'?=",
            r"(?P<value>[-0-9.]+)",
            r"(?P<unit>s|us|ms|%|B|KB|MB|GB|TB|c)?",
            r"(;(?P<warn>@?[-0-9.~]*:?[-0-9.~]*))?",
            r"(;(?P<crit>@?[-0-9.~]*:?[-0-9.~]*))?",
            r"(;(?P<min>[-0-9.]*))?",
            r"(;(?P<max>[-0-9.]*))?",
        ]))



    @staticmethod
    def underscorize(s):
        return s.replace(' ', '_').lower()

    def _get_metric_prefix(self, data):
        # Should be overridded by subclasses
        return [self.metric_prefix]

    def _parse_line(self, line):
        matched = self.line_pattern.match(line)
        output = []
        if matched:
            data = matched.groupdict()
            metric_prefix = self._get_metric_prefix(data)

            # Parse the prefdata values, which are a space-delimited list of:
            #   'label'=value[UOM];[warn];[crit];[min];[max]
            perf_data = data.get(self.perfdata_field, '').split(' ')
            for pair in perf_data:
                pair_match = self.pair_pattern.match(pair)
                if not pair_match:
                    continue
                else:
                    pair_data = pair_match.groupdict()

                label = pair_data['label']
                timestamp = data.get('TIMET', None)
                value = float(pair_data['value'])

                device_name = None

                if '/' in label:
                    # Special case: if the label begins
                    # with a /, treat the label as the device
                    # and use the metric prefix as the metric name
                    metric = '.'.join(metric_prefix)
                    device_name = label

                else:
                    # Otherwise, append the label to the metric prefix
                    # and use that as the metric name
                    metric = '.'.join(metric_prefix + [label])

                host_name = data.get('HOSTNAME', self.hostname)

                optional_keys = ['unit', 'warn', 'crit', 'min', 'max']
                tags = []
                for key in optional_keys:
                    attr_val = pair_data.get(key, None)
                    if attr_val is not None and attr_val != '':
                        tags.append("{0}:{1}".format(key,attr_val))

                self._gauge(metric, value, tags, host_name, device_name, timestamp)

class NagiosHostPerfDataTailer(NagiosPerfDataTailer):
    perfdata_field = 'HOSTPERFDATA'

    def _get_metric_prefix(self, line_data):
        return [self.metric_prefix, 'host']


class NagiosServicePerfDataTailer(NagiosPerfDataTailer):
    perfdata_field = 'SERVICEPERFDATA'

    def _get_metric_prefix(self, line_data):
        metric = [self.metric_prefix]
        middle_name = line_data.get('SERVICEDESC', None)
        if middle_name:
            metric.append(middle_name.replace(' ', '_').lower())
        return metric

class InvalidDataTemplate(Exception): pass
