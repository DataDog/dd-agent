'''
Monitor the Windows Event Log
'''
from datetime import datetime, timedelta
import time

from checks import AgentCheck

SOURCE_TYPE_NAME = 'api'
EVENT_TYPE = 'win32_log_event'

class Win32EventLog(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.last_ts = {}

    def check(self, instance):
        try:
            import wmi
        except ImportError:
            self.log.error("Unable to import 'wmi' module")
            return

        host = instance.get('host')
        user = instance.get('username')
        password = instance.get('password')
        tags = instance.get('tags')
        w = wmi.WMI(host, user=user, password=password)

        # Store the last timestamp by instance
        instance_key = self._instance_key(instance)
        if instance_key not in self.last_ts:
            self.last_ts[instance_key] = datetime.now()
            return

        # Find all events in the last check that match our search by running a 
        # straight WQL query against the event log
        last_ts = self.last_ts[instance_key]
        q = EventLogQuery(
                ltype=instance.get('type'),
                user=instance.get('user'),
                source_name=instance.get('source_name'),
                log_file=instance.get('log_file'),
                start_ts=last_ts
            )
        events = w.query(q.to_wql())

        # Save any events returned to the payload as Datadog events
        for ev in [events[0]]:
            log_ev = LogEvent(ev, self.agentConfig.get('api_key', ''),
                self.hostname, tags, self._get_tz_offset())

            # Since WQL only compares on the date and NOT the time, we have to
            # do a secondary check to make sure events are after the last
            # timestamp
            if log_ev.is_after(last_ts):
                self.event(log_ev.to_event_dict())

        # Update the last time checked
        self.last_ts[instance_key] = datetime.now()

    def _instance_key(self, instance):
        ''' Generate a unique key per instance for use with keeping track of
        state for each instance '''
        return '%s'.format(instance)

    def _get_tz_offset(self):
        ''' Return the timezone offset for the current local time
        '''
        offset = time.timezone if (time.daylight == 0) else time.altzone
        return offset / 60 / 60 * -1

class EventLogQuery(object):
    def __init__(self, ltype=None, user=None, source_name=None, log_file=None,
        start_ts=None):
        self.filters = [
            ('Type', self._convert_event_types(ltype)),
            ('User', user),
            ('SourceName', source_name),
            ('LogFile', log_file)
        ]
        self.start_ts = start_ts

    def to_wql(self):
        ''' Return this query as a WQL string '''
        wql = """
        SELECT Message, SourceName, TimeGenerated, Type, User
        FROM Win32_NTLogEvent
        WHERE TimeGenerated >= "%s"
        """ % (self._dt_to_wmi(self.start_ts))
        for name, vals in self.filters:
            wql = self._add_filter(name, vals, wql)
        return wql

    def _add_filter(self, name, vals, q):
        if not vals:
            return q
        # A query like (X = Y) does not work, unless there are multiple
        # statements inside the parentheses, such as (X = Y OR Z = Q)
        if len(vals) == 1:
            vals = vals[0]
        if not isinstance(vals, list):
            q += '\nAND %s = "%s"' % (name, vals)
        else:
            q += "\nAND (%s)" % (' OR '.join(['%s = "%s"' % (name, l) for l in vals]))
        
        return q

    def _dt_to_wmi(self, dt):
        ''' A wrapper around wmi.from_time to get a WMI-formatted time from a 
        time struct. '''
        import wmi
        return wmi.from_time(year=dt.year, month=dt.month, day=dt.day,
            hours=dt.hour, minutes=dt.minute, seconds=dt.second, microseconds=0,
            timezone=0)

    def _convert_event_types(self, types):
        ''' Detect if we are running on <= Server 2003. If so, we should convert
        the EventType values to integers '''
        return types

class LogEvent(object):
    def __init__(self, ev, api_key, hostname, tags, tz_offset):
        self.event = ev
        self.api_key = api_key
        self.hostname = hostname
        self.tags = tags
        self.tz_offset = tz_offset
        self.timestamp = self._wmi_to_ts(self.event.TimeGenerated)

    def to_event_dict(self):
        return {
            'timestamp': self.timestamp,
            'event_type': EVENT_TYPE,
            'api_key': self.api_key,
            'msg_title': self._msg_title(self.event),
            'msg_text': self.event.Message,
            'aggregation_key': self._aggregation_key(self.event),
            'alert_type': self._alert_type(self.event),
            'source_type_name': SOURCE_TYPE_NAME,
            'host': self.hostname,
            'tags': self.tags
        }

    def is_after(self, ts):
        ''' Compare this event's timestamp to a give timestamp '''
        if self.timestamp >= int(time.mktime(ts.timetuple())):
            return True
        return False

    def _wmi_to_ts(self, wmi_ts):
        ''' Convert a wmi formatted timestamp into an epoch using wmi.to_time()
        '''
        import wmi
        year, month, day, hour, minute, second, microsecond, tz = wmi.to_time(wmi_ts)
        dt = datetime(year=year, month=month, day=day, hour=hour,
            second=second, microsecond=microsecond)
        return int(time.mktime(dt.timetuple())) + (self.tz_offset * 60 * 60)

    def _msg_title(self, event):
        return '%s/%s' % (event.Logfile, event.SourceName)

    def _alert_type(self, event):
        event_type = event.Type
        try:
            # For Server 2003, event type is a number 
            event_type = int(event_type)
            event_type = LogEventType.from_wmi(event_type)
        except ValueError:
            # Not an integer, just treat as a string
            pass

        # Convert to a Datadog alert type
        if event_type == 'Warning':
            return 'warning'
        elif event_type == 'Error':
            return 'error'
        return 'info'

    def _aggregation_key(self, event):
        return event.SourceName

class LogEventType(object):
    ''' A basic class for converting between EventTypes number values and
        strings for <= Windows Server 2003 
    '''
    ERROR = 1
    WARN = 2
    INFO = 3
    SECURITY_AUDIT_SUCCESS = 4
    SECURITY_AUDIT_FAILURE = 5

    @classmethod
    def from_wmi(cls, val):
        if val == cls.ERROR:
            return 'Error'
        elif val == cls.WARNING:
            return 'Warning'
        elif val == cls.INFO:
            return 'Information'
        elif val == cls.SECURITY_AUDIT_SUCCESS:
            return 'Security Audit Success'
        elif val == cls.SECURITY_AUDIT_FAILURE:
            return 'Security Audit Failure'
        raise Exception('Invalid WMI EventType: %s' % (val))

    @classmethod
    def to_wmi(cls, val):
        if val == 'Error':
            return cls.ERROR
        if val == 'Warning':
            return cls.WARN
        if val == 'Information':
            return cls.INFO
        if val == 'Security Audit Success':
            return cls.SECURITY_AUDIT_SUCCESS
        if val == 'Security Audit Failure':
            return cls.SECURITY_AUDIT_FAILURE
        raise Exception('Invalid WMI EventType: %s' % (val))

if __name__ == "__main__":
    check, instances = Win32EventLog.from_yaml('conf.d/win32_event_log.yaml')
    for instance in instances:
        check.check(instance)
        # Run check again so "last time" is populated
        check.check(instance)
    print check.get_events()