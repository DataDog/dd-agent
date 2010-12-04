import os
import time
import re
from collections import namedtuple

# Event types we know about but decide to ignore in the parser
IGNORE_EVENT_TYPES = [
    'SERVICE NOTIFICATION'
]

# fields order for each event type, as named tuples
EVENT_FIELDS = {
    'CURRENT HOST STATE':       namedtuple('E_CurrentHostState', 'host, event_state, event_soft_hard, return_code, payload'),
    'CURRENT SERVICE STATE':    namedtuple('E_CurrentServiceState', 'host, check_name, event_state, event_soft_hard, return_code, payload'),
    'SERVICE ALERT':            namedtuple('E_ServiceAlert', 'host, check_name, event_state, event_soft_hard, return_code, payload'),
    'PASSIVE SERVICE CHECK':    namedtuple('E_PassiveServiceCheck', 'host, check_name, return_code, payload'),
    'HOST ALERT':               namedtuple('E_HostAlert', 'host, event_state, event_soft_hard, return_code, payload')
}

def create_event(timestamp, event_type, fields):
    """Factory method called by the parsers
    """
    # FIXME Oli: kind of ugly to have to go through a named dict for this, and inefficient too
    # but couldn't think of anything smarter
    d = fields._asdict()
    d.update({ 'timestamp': timestamp, 'event_type': event_type })
    return d


def tail_file(f,callback,move_end=True):

    if type(f) == str:
        f = open(f,'r')

    if move_end:
        f.seek(1, os.SEEK_END)

    done = False
    while True:
        if done:
            break

        where = f.tell()
        line = f.readline()
        if line:
           done = callback(line.rstrip("\n"))
        else:
            yield True
            f.seek(where)
        
class Nagios(object):

    key = "Nagios"

    def __init__(self):
        self.re_line = re.compile('^\[(\d+)\] (.*?):(.*)')
        self.logger = None
        self.gen = None
        self.events = None

    def _parse_line(self, line):

        # first isolate the timestamp and the event type
        try:
            m = self.re_line.match(line)
            (tstamp, event_type, remainder)= m.groups()
            if event_type in IGNORE_EVENT_TYPES:
                self.logger.info("Ignoring nagios event of type {0}".format(event_type))
                return None
            tstamp = int(tstamp)
        except:
            self.logger.warn("Error while trying to get a nagios event type from line {0}".format(line))
            return None

        # then retrieve the event format for each specific event type
        fields = EVENT_FIELDS.get(event_type, None)
        if fields is None:
            self.logger.warn("Ignoring unkown nagios event for line: [{0}]".format(line))
            return None

        # and parse the rest of the line
        try:
            parts = remainder.split(';')
            event = create_event(tstamp, event_type, fields._make(map(lambda p: p.strip(), parts)))
            self.events.append(event)
            self.logger.debug("Nagios event: {0}".format(event))
        except:
            self.logger.warn("Unable to create a nagios event from line: [{0}]".format(line))

        return None

    def check(self, logger, agentConfig):

        self.logger = logger

        # Check arguments
        log_path = agentConfig.get('nagios_log',None)
        if log_path is None:
            self.logger.warn("Not checking nagios because nagios_log is not set in config file")
            return False

        self.events = []
      
        # Build our tail -f 
        if self.gen is None:
            self.gen = tail_file(log_path,self._parse_line,move_end=False)

        # read until the end of file
        self.gen.next() 

        self.logger.debug("Done nagios check for file {0}".format(log_path))
        return self.events

if __name__ == "__main__":
    import logging
    logger = logging.getLogger("nagios")    
    logger.setLevel(logging.WARN)
    logger.addHandler(logging.StreamHandler())
    nagios = Nagios()

    while True:
        nagios.check(logger, {'nagios_log': '/var/log/nagios3/nagios.log'})
        time.sleep(5)

