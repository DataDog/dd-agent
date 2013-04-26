import re
from checks.log_parser import LogParserCheck, LogParser
from util import namedtuple, get_hostname


class NagiosParsingError(Exception): pass
class InvalidDataTemplate(Exception): pass


class Nagios(LogParserCheck):

    key = "Nagios"

    def create_event(self, event_data):
        timestamp, event_type, fields = event_data

        # FIXME Oli: kind of ugly to have to go through a named dict for this, and inefficient too
        # but couldn't think of anything smarter
        d = fields._asdict()
        d.update({'timestamp': timestamp, 'event_type': event_type, 'api_key': self.agentConfig.get('api_key', '')})
        # if host is localhost, turn that into the internal host name
        host = d.get('host', None)
        if host == "localhost":
            d["host"] = get_hostname(self.agentConfig)

        self.log.debug("Nagios event: %s" % (d))
        self.event(d)

    def check(self, instance):

        # Check arguments
        cfg_path = instance.get('cfg_file', None)
        log_path = instance.get('log_file', None)
        event_log = instance.get('event_log', True)
        perf_data = instance.get('perf_data', False)
        if cfg_path is None and log_path is None:
            raise Exception("Not checking nagios because 'cfg_file' is not set in nagios config")

        tags = instance.get('tags', None)

        instance_key = self._instance_key(instance)

        parsers = []
        if instance_key in self.parsers:
            parsers = self.parsers[instance_key]

        # Build our tail -f
        if len(parsers) == 0:
            nagios_config = {}
            if cfg_path:
                nagios_config = self.parse_nagios_config(cfg_path)

                if perf_data:
                    host_parser = NagiosHostPerfData(self.log, nagios_config)
                    service_parser = NagiosServicePerfData(self.log, nagios_config)

                    if not host_parser.tail and not service_parser.tail:
                        raise Exception("The Nagios check is configured to check performance data, but failed to parse any of the perfdata files. Please ensure that the file and file_template fields for at least one of host or service perfdata is filled in correctly in the nagios config file.")

                    if host_parser.tail:
                        parsers.append(host_parser)
                    if service_parser.tail:
                        parsers.append(service_parser)

            if event_log:
                log_file = nagios_config.get('log_file', log_path)
                if not log_file:
                    raise Exception("Nagios check is configured to parse the event log, but failed to do so. Please ensure the value for log_file is correct.")

                nagios_log_parser = NagiosLogParser(self.log, log_file)
                parsers.append(nagios_log_parser)

            self.parsers[instance_key] = parsers

        # read until the end of file
        for parser in parsers:
            parser.parse_file()
            events = parser._get_events()
            for event in events:
                self.create_event(event)

            metrics = parser._get_metrics()
            for metric in metrics:
                self.gauge(metric['metric'], float(metric['value']), tags=tags, hostname=metric['hostname'], device_name=metric['device_name'])

    @staticmethod
    def parse_agent_config(agentConfig):
        cfg_file = agentConfig.get('nagios_perf_cfg', None)
        log_file = agentConfig.get('nagios_log', None)

        if not log_file and not cfg_file:
            return False

        instance = {}

        if cfg_file:
            instance['cfg_file'] = cfg_file
            instance['perf_data'] = True

        if log_file:
            instance['log_file'] = log_file
            instance['event_log'] = True

        return {
            'instances': [instance]
        }

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
        finally:
            if f is not None:
                f.close()
        return output


class NagiosLogParser(LogParser):

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
    RE_LINE_REG = re.compile('^\[(\d+)\] EXTERNAL COMMAND: (\w+);(.*)$')
    RE_LINE_EXT = re.compile('^\[(\d+)\] ([^:]+): (.*)$')

    def _parse_line(self, line):
        """Actual nagios parsing
        Return True if we found an event, False Otherwise
        """

        # We need to use try/catch here because a specific return value
        # of True or False is expected, and one line failing shouldn't
        # cause the entire thing to fail
        try:
            self._line_parsed = self._line_parsed + 1

            m = self.RE_LINE_REG.match(line)
            if m is None:
                m = self.RE_LINE_EXT.match(line)
            if m is None:
                return False

            (tstamp, event_type, remainder) = m.groups()
            tstamp = int(tstamp)

            # then retrieve the event format for each specific event type
            fields = self.EVENT_FIELDS.get(event_type, None)
            if fields is None:
                self.log.warn("Ignoring unkown nagios event for line: %s" % (line[:-1]))
                return False

            # and parse the rest of the line
            parts = map(lambda p: p.strip(), remainder.split(';'))
            # Chop parts we don't recognize
            parts = parts[:len(fields._fields)]

            self.event_data.append((tstamp, event_type, fields._make(parts)))

            return True
        except Exception, e:
            self.log.exception(e)
            return False


class NagiosPerfData(LogParser):
    perfdata_field = ''  # Should be overriden by subclasses
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

    def __init__(self, logger, line_pattern, log_path):
        if isinstance(line_pattern, (str, unicode)):
            self.line_pattern = re.compile(line_pattern)
        else:
            self.line_pattern = line_pattern

        LogParser.__init__(self, logger, log_path)

    @staticmethod
    def template_regex(file_template):
        try:
            # Escape characters that will be interpreted as regex bits
            # e.g. [ and ] in "[SERVICEPERFDATA]"
            regex = re.sub(r'[[\]*]', r'.', file_template)
            regex = re.sub(r'\$([^\$]*)\$', r'(?P<\1>[^\$]*)', regex)
            return re.compile(regex)
        except Exception, e:
            raise InvalidDataTemplate("%s (%s)" % (file_template, e))

    @staticmethod
    def underscorize(s):
        return s.replace(' ', '_').lower()

    def _get_metric_prefix(self, data):
        raise NotImplementedError()

    def _parse_line(self, line):
        matched = self.line_pattern.match(line)
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
                timestamp = data.get('TIMET', '')
                value = pair_data['value']
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

                host_name = data.get('HOSTNAME', None)

                self.metric_data.append({
                    'metric': metric,
                    'value': value,
                    'hostname': host_name,
                    'device_name': device_name,
                    'timestamp': timestamp
                })
            # Matches have been processed
            return True

        # No matches
        return False


class NagiosHostPerfData(NagiosPerfData):
    perfdata_field = 'HOSTPERFDATA'

    def __init__(self, logger, nagios_config):
        host_perfdata_file_template = nagios_config.get('host_perfdata_file_template', None)
        host_perfdata_file = nagios_config.get('host_perfdata_file', None)

        self.tail = None
        if host_perfdata_file_template and host_perfdata_file:
            host_pattern = NagiosPerfData.template_regex(host_perfdata_file_template)
            NagiosPerfData.__init__(self, logger, host_pattern, host_perfdata_file)

    def _get_metric_prefix(self, line_data):
        return [self.metric_prefix, 'host']


class NagiosServicePerfData(NagiosPerfData):
    perfdata_field = 'SERVICEPERFDATA'

    def __init__(self, logger, nagios_config):
        service_perfdata_file_template = nagios_config.get('service_perfdata_file_template', None)
        service_perfdata_file = nagios_config.get('service_perfdata_file', None)

        self.tail = None
        if service_perfdata_file_template and service_perfdata_file:
            service_pattern = NagiosPerfData.template_regex(service_perfdata_file_template)
            return NagiosPerfData.__init__(self, logger, service_pattern, service_perfdata_file)

    def _get_metric_prefix(self, line_data):
        metric = [self.metric_prefix]
        middle_name = line_data.get('SERVICEDESC', None)
        if middle_name:
            metric.append(self.underscorize(middle_name))
        return metric
