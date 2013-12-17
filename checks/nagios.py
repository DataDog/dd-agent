import time
import re
from util import namedtuple, get_hostname
from utils import TailFile

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

def create_event(timestamp, event_type, hostname, fields):
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

class Nagios(object):

    key = "Nagios"

    def __init__(self, hostname):
        """hostname is the name of the machine where the nagios log lives
        """
        # Regex alternation ends up being tricker than expected, and much less readable
        #self.re_line = re.compile('^\[(\d+)\] (?:EXTERNAL COMMAND: (\w+);)|(?:([^:]+): )(.*)$')
        self.re_line_reg = re.compile('^\[(\d+)\] EXTERNAL COMMAND: (\w+);(.*)$')
        self.re_line_ext = re.compile('^\[(\d+)\] ([^:]+): (.*)$')

        self.logger = None
        self.gen = None
        self.tail = None
        self.events = None
        self.apikey = ""
        self.hostname = hostname

        self._line_parsed = 0

    def _parse_line(self, line):
        """Actual nagios parsing
        Return True if we found an event, False otherwise
        """
        # first isolate the timestamp and the event type
        try:
            self._line_parsed = self._line_parsed + 1

            m  = self.re_line_reg.match(line)
            if m is None:
                m = self.re_line_ext.match(line)
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
                self.logger.warn("Ignoring unkown nagios event for line: %s" % (line[:-1]))
                return False

            # and parse the rest of the line
            parts = map(lambda p: p.strip(), remainder.split(';'))
            # Chop parts we don't recognize
            parts = parts[:len(fields._fields)]

            event = create_event(tstamp, event_type, self.hostname, fields._make(parts))
            event.update({'api_key': self.apikey})

            self.events.append(event)
            self.logger.debug("Nagios event: %s" % (event))

            return True
        except Exception:
            self.logger.exception("Unable to create a nagios event from line: [%s]" % (line))
            return False

    def check(self, logger, agentConfig, move_end=True):

        self.logger = logger

        # Check arguments
        log_path = agentConfig.get('nagios_log',None)
        if log_path is None:
            self.logger.debug("Not checking nagios because nagios_log is not set in config file")
            return False

        self.apikey = agentConfig['api_key']
        self.events = []
        self._line_parsed = 0

        # Build our tail -f
        if self.gen is None:
            self.tail = TailFile(logger,log_path,self._parse_line)
            self.gen = self.tail.tail(line_by_line=False, move_end=move_end)

        # read until the end of file
        try:
            self.logger.debug("Start nagios check for file %s" % (log_path))
            self.tail._log = self.logger
            self.gen.next()
            self.logger.debug("Done nagios check for file %s (parsed %s line(s), generated %s event(s))" %
                (log_path,self._line_parsed,len(self.events)))
        except StopIteration, e:
            self.logger.exception(e)
            self.logger.warn("Can't tail %s file" % (log_path))

        return self.events

def parse_log(api_key, log_file):
    import logging
    import socket
    import sys

    logger = logging.getLogger("ddagent.checks.nagios")
    nagios = Nagios(get_hostname())

    events = nagios.check(logger, {'api_key': api_key, 'nagios_log': log_file}, move_end=False)
    for e in events:
        yield e

if __name__ == "__main__":
    import logging
    import socket

    logger = logging.getLogger("ddagent.checks.nagios")
    nagios = Nagios(get_hostname())

    config = {'api_key':'apikey_2','nagios_log': '/var/log/nagios3/nagios.log'}
    events = nagios.check(logger, config,move_end = False)
    while True:
        #for e in events:
        #    print "Event:", e
        time.sleep(5)
        events = nagios.check(logger, config)