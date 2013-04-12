import time
import re
from checks import AgentCheck
from util import namedtuple, get_hostname
from checks.utils import TailFile


class NagiosParsingError(Exception): pass


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

    # Regex alternation ends up being tricker than expected, and much less readable
    RE_LINE_REG = re.compile('^\[(\d+)\] EXTERNAL COMMAND: (\w+);(.*)$')
    RE_LINE_EXT = re.compile('^\[(\d+)\] ([^:]+): (.*)$')

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        self.gens = {}
        self.tails = {}
        self.perf_data_parsers = {}

        self._line_parsed = 0

    def _instance_key(*args):
        """ Return a key unique for this instance """
        return '|'.join([str(a) for a in args])

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
        Return True if we found an event, False otherwise
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

        tail = None
        gen = None

        instance_key = self._instance_key(instance)

        if instance_key in self.tails:
            tail = self.tails[instance_key]
            gen = self.gens[instance_key]

        # Build our tail -f
        if gen is None:
            tail = TailFile(self.log, log_path, self._parse_line)
            gen = self.tail.tail(line_by_line=False)
            self.tails[instance_key] = tail
            self.gens[instance_key] = gen

        # read until the end of file
        try:
            self.log.debug("Start nagios check for file %s" % (log_path))
            tail._log = self.log
            gen.next()
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
