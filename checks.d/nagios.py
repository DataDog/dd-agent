import time
import re
from checks import AgentCheck
from util import namedtuple, get_hostname
from checks.utils import TailFile


class NagiosParsingError(Exception): pass
class InvalidDataTemplate(Exception): pass


class Nagios(AgentCheck):

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

    key = "Nagios"
    RE_LINE_REG = re.compile('^\[(\d+)\] EXTERNAL COMMAND: (\w+);(.*)$')
    RE_LINE_EXT = re.compile('^\[(\d+)\] ([^:]+): (.*)$')

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        # Regex alternation ends up being tricker than expected, and much less readable
        self.gen = None
        self.tail = None
        self.event_count = 0

        self._line_parsed = 0

    def create_event(self, timestamp, event_type, fields):
        hostname = get_hostname(self.agentConfig)

        # FIXME Oli: kind of ugly to have to go through a named dict for this, and inefficient too
        # but couldn't think of anything smarter
        d = fields._asdict()
        d.update({'timestamp': timestamp, 'event_type': event_type, 'api_key': self.agentConfig.get('api_key', '')})
        # if host is localhost, turn that into the internal host name
        host = d.get('host', None)
        if host == "localhost":
            d["host"] = hostname

        self.log.debug("Nagios event: %s" % (d))
        self.event_count = self.event_count + 1
        self.event(d)

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

            if event_type in self.IGNORE_EVENT_TYPES:
                self.log.info("Ignoring nagios event of type %s" % (event_type))
                return False

            # then retrieve the event format for each specific event type
            fields = self.EVENT_FIELDS.get(event_type, None)
            if fields is None:
                self.log.warn("Ignoring unkown nagios event for line: %s" % (line[:-1]))
                return False

            # and parse the rest of the line
            parts = map(lambda p: p.strip(), remainder.split(';'))
            # Chop parts we don't recognize
            parts = parts[:len(fields._fields)]

            self.create_event(tstamp, event_type, fields._make(parts))

            return True
        except Exception, e:
            self.log.exception(e)
            return False

    def check(self, instance):

        # Check arguments
        log_path = instance.get('log_file', None)
        if log_path is None:
            raise Exception("Not checking nagios because 'log_file' is not set in nagios config")

        self._line_parsed = 0
        self.event_count = 0

        cfg_path = instance.get('cfg_file', None)

        tail = None
        gen = None
        perf_data_parsers = None

        instance_key = self._instance_key(instance)

        if instance_key in self.tails:
            tail = self.tails[instance_key]
            gen = self.gens[instance_key]

        if instance_key in self.perf_data_parsers:
            perf_data_parsers = self.perf_data_parsers[instance_key]

        # Build our tail -f
        if self.gen is None:
            self.tail = TailFile(self.log, log_path, self._parse_line)
            self.gen = self.tail.tail(line_by_line=False)

        if perf_data_parsers is None and cfg_path is not None:
            perf_data_parsers = NagiosPerfData.init(self.log, cfg_path)
            self.perf_data_parsers[instance_key] = perf_data_parsers

        # read until the end of file
        try:
            self.log.debug("Start nagios check for file %s" % (log_path))
            self.tail._log = self.log
            self.gen.next()
            self.log.debug("Done nagios check for file %s (parsed %s line(s), generated %s event(s))" %
                (log_path, self._line_parsed, self.event_count))
        except StopIteration, e:
            self.log.warn("Can't tail %s file" % (log_path))
            raise

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('nagios_log'):
            return False

        return {
            'instances': [{
                'log_file': agentConfig.get('nagios_log')
            }]
        }


class NagiosPerfData(object):
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

    def __init__(self, logger, line_pattern, datafile):
        if isinstance(line_pattern, (str, unicode)):
            self.line_pattern = re.compile(line_pattern)
        else:
            self.line_pattern = line_pattern

        self.logger = logger

        self.log_path = datafile

        self._gen = None
        self._values = None
        self._error_count = 0L
        self._line_count = 0L
        self.parser_state = {}

    @classmethod
    def init(cls, logger, cfg_path):
        parsers = []
        if cfg_path:
            nagios_config = cls.parse_nagios_config(cfg_path)

            host_parser = NagiosHostPerfData.init(logger, nagios_config)
            if host_parser:
                parsers.append(host_parser)

            service_parser = NagiosServicePerfData.init(logger, nagios_config)
            if service_parser:
                parsers.append(service_parser)

        return parsers

    @staticmethod
    def template_regex(file_template):
        try:
            # Escape characters that will be interpreted as regex bits
            # e.g. [ and ] in "[SERVICEPERFDATA]"
            #regex = re.sub(r'[[\]*]', r'.', file_template)
            regex = re.sub(r'\$([^\$]*)\$', r'(?P<\1>[^\$]*)', regex)
            return re.compile(regex)
        except Exception, e:
            raise InvalidDataTemplate("%s (%s)"% (file_template, e))


    @staticmethod
    def underscorize(s):
        return s.replace(' ', '_').lower()

    @classmethod
    def parse_nagios_config(cls, filename):
        output = {}
        keys = [
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
            except:
                # Can't parse, assume it's just not working
                # Don't return an incomplete config
                return {}
        finally:
            if f is not None:
                f.close()

    def _get_metric_prefix(self, data):
        # Should be overridded by subclasses
        return [self.metric_prefix]

    def _parse_line(self, logger, line):
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
                timestamp = data.get('TIMET', '')
                value = pair_data['value']
                attributes = {'metric_type': 'gauge'}

                if '/' in label:
                    # Special case: if the label begins
                    # with a /, treat the label as the device
                    # and use the metric prefix as the metric name
                    metric = '.'.join(metric_prefix)
                    attributes['device_name'] = label

                else:
                    # Otherwise, append the label to the metric prefix
                    # and use that as the metric name
                    metric = '.'.join(metric_prefix + [label])

                host_name = data.get('HOSTNAME', None)
                if host_name:
                    attributes['host_name'] = host_name

                optional_keys = ['unit', 'warn', 'crit', 'min', 'max']
                for key in optional_keys:
                    attr_val = pair_data.get(key, None)
                    if attr_val is not None and attr_val != '':
                        attributes[key] = attr_val

                output.append((
                    metric,
                    timestamp,
                    value,
                    attributes
                ))
        return output

    def check(self, agentConfig, move_end=True):
        if self.log_path:
            self._freq = int(agentConfig.get('check_freq', 15))
            self._values = []
            self._events = []

            # Build our tail -f
            if self._gen is None:
                self._gen = TailFile(self.logger, self.log_path, self._line_parser).tail(line_by_line=False, move_end=move_end)

            # read until the end of file
            try:
                self._gen.next()
                self.logger.debug("Done dogstream check for file %s, found %s metric points" % (self.log_path, len(self._values)))
            except StopIteration, e:
                self.logger.exception(e)
                self.logger.warn("Can't tail %s file" % self.log_path)

            check_output = self._aggregate(self._values)
            if self._events:
                check_output.update({"dogstreamEvents": self._events})
            return check_output
        else:
            return {}


class NagiosHostPerfData(NagiosPerfData):
    perfdata_field = 'HOSTPERFDATA'

    @classmethod
    def init(cls, logger, nagios_config):
        host_perfdata_file_template = nagios_config.get('host_perfdata_file_template', None)
        host_perfdata_file = nagios_config.get('host_perfdata_file', None)

        if host_perfdata_file_template and host_perfdata_file:
            host_pattern = cls.template_regex(host_perfdata_file_template)
            return cls(logger, host_pattern, host_perfdata_file)
        else:
            return None

    def _get_metric_prefix(self, line_data):
        return [self.metric_prefix, 'host']


class NagiosServicePerfData(NagiosPerfData):
    perfdata_field = 'SERVICEPERFDATA'

    @classmethod
    def init(cls, logger, nagios_config):
        service_perfdata_file_template = nagios_config.get('service_perfdata_file_template', None)
        service_perfdata_file = nagios_config.get('service_perfdata_file', None)

        if service_perfdata_file_template and service_perfdata_file:
            service_pattern = cls.template_regex(service_perfdata_file_template)
            return cls(logger, service_pattern, service_perfdata_file)
        else:
            return None

    def _get_metric_prefix(self, line_data):
        metric = [self.metric_prefix]
        middle_name = line_data.get('SERVICEDESC', None)
        if middle_name:
            metric.append(middle_name.replace(' ', '_').lower())
        return metric

if __name__ == "__main__":
    import logging

    nagios = Nagios('nagios', {'init_config': {}, 'instances': {}}, {'api_key': 'apikey_2', 'nagios_log': '/var/log/nagios3/nagios.log'})
    logger = logging.getLogger("ddagent.checks.nagios")
    nagios = Nagios(get_hostname())

    config = {'api_key': 'apikey_2', 'nagios_log': '/var/log/nagios3/nagios.log'}
    events = nagios.check(logger, config)
    while True:
        #for e in events:
        #    print "Event:", e
        time.sleep(5)
        events = nagios.check(logger, config)
