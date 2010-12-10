import os
import time
import re
from stat import *
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


class TailFile(object):

    def __init__(self,logger,path,callback):
        self._path = path
        self._f = None
        self._inode = None
        self._size = 0
        self._log = logger
        self._callback = callback
    
    def _open_file(self,move_end=False,where=False):

        already_open = False
        #close and reopen to handle logrotate
        if self._f is not None:
            self._f.close()
            self._f = None
            already_open = True
        
        stat = os.stat(self._path)
        inode = stat[ST_INO]
        size = stat[ST_SIZE]

        if already_open:
            if self._inode is not None:
                #Check if file has been removed
                if inode != self._inode:
                    self._log.debug("File removed, reopening")
                    move_end = False
                    where = False
            elif self._size > 0:
                #Check if file has been truncated
                if size < self._size:
                    self._log.debug("File truncated, reopening")
                    move_end = False
                    where = False

        self._inode = inode
        self._size = size

        self._f = open(self._path,'r')
        if move_end:
            self._f.seek(1,os.SEEK_END)
        elif where:
            self._log.debug("Reopening file at {0}".format(where))
            self._f.seek(where)

        return True

    def tail(self,move_end=True):

        self._open_file(move_end=move_end)
        
        done = False
        while True:
            if done:
                break

            where = self._f.tell()
            line = self._f.readline()
            if line:
               done = self._callback(line.rstrip("\n"))
            else:
                yield True
                self._open_file(move_end=False,where=where)
        
class Nagios(object):

    key = "Nagios"

    def __init__(self, hostname):
        """hostname is the name of the machine where the nagios log lives
        """
        self.re_line = re.compile('^\[(\d+)\] ([^:]+): (.*)')
        self.logger = None
        self.gen = None
        self.events = None
        self.apikey = ""
        self.hostname = hostname

    def _parse_line(self, line):

        # first isolate the timestamp and the event type
        try:
            m = self.re_line.match(line)
            if m is None:
                return None
            else:
                (tstamp, event_type, remainder)= m.groups()
                if event_type in IGNORE_EVENT_TYPES:
                    self.logger.info("Ignoring nagios event of type {0}".format(event_type))
                    return None
                tstamp = int(tstamp)
        except Exception, e:
            self.logger.exception("Error while trying to get a nagios event type from line {0}".format(line))
            return None

        # then retrieve the event format for each specific event type
        fields = EVENT_FIELDS.get(event_type, None)
        if fields is None:
            self.logger.warn("Ignoring unkown nagios event for line: [{0}]".format(line))
            return None

        # and parse the rest of the line
        try:
            parts = remainder.split(';')
            event = create_event(tstamp, event_type, self.hostname, fields._make(map(lambda p: p.strip(), parts)))
            event.update({'api_key': self.apikey})
            self.events.append(event)
            self.logger.debug("Nagios event: {0}".format(event))
        except Exception, e:
            self.logger.exception("Unable to create a nagios event from line: [{0}]".format(line))

        return None

    def check(self, logger, agentConfig):

        self.logger = logger

        # Check arguments
        log_path = agentConfig.get('nagios_log',None)
        if log_path is None:
            self.logger.warn("Not checking nagios because nagios_log is not set in config file")
            return False

        self.apikey = agentConfig['apiKey']
        self.events = []
      
        # Build our tail -f 
        if self.gen is None:
            self.gen = TailFile(logger,log_path,self._parse_line).tail(move_end=True)

        # read until the end of file
        self.gen.next() 

        self.logger.debug("Done nagios check for file {0}".format(log_path))
        return self.events

if __name__ == "__main__":
    import logging
    import socket
    logger = logging.getLogger("nagios")    
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    nagios = Nagios(socket.gethostname())

    while True:
        events = nagios.check(logger, {'apiKey':'apikey_2','nagios_log': '/var/log/nagios3/nagios.log'})
        for e in events:
            print "Event:", e
        time.sleep(5)

