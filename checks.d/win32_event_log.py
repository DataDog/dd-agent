'''
Monitor the Windows Event Log
'''
# stdlib
import calendar
from datetime import datetime, timedelta

# project
from checks.wmi_check import WinWMICheck, to_time, from_time
from utils.containers import hash_mutable
from utils.timeout import TimeoutException

SOURCE_TYPE_NAME = 'event viewer'
EVENT_TYPE = 'win32_log_event'

class Win32EventLogWMI(WinWMICheck):
    EVENT_PROPERTIES = [
        "Message",
        "SourceName",
        "TimeGenerated",
        "Type",
        "User",
        "InsertionStrings",
        "EventCode"
    ]
    NAMESPACE = "root\\CIMV2"
    CLASS = "Win32_NTLogEvent"

    def __init__(self, name, init_config, agentConfig, instances=None):
        WinWMICheck.__init__(self, name, init_config, agentConfig,
                            instances=instances)
        self.last_ts = {}

    def check(self, instance):
        # Connect to the WMI provider
        host = instance.get('host', "localhost")
        username = instance.get('username', "")
        password = instance.get('password', "")
        instance_tags = instance.get('tags', [])
        notify = instance.get('notify', [])

        user = instance.get('user')
        ltypes = instance.get('type', [])
        source_names = instance.get('source_name', [])
        log_files = instance.get('log_file', [])
        event_ids = instance.get('event_id', [])
        message_filters = instance.get('message_filters', [])

        instance_hash = hash_mutable(instance)
        instance_key = self._get_instance_key(host, self.NAMESPACE, self.CLASS, instance_hash)

        # Store the last timestamp by instance
        if instance_key not in self.last_ts:
            self.last_ts[instance_key] = datetime.utcnow()
            return

        query = {}
        filters = []
        last_ts = self.last_ts[instance_key]
        query['TimeGenerated'] = ('>=', self._dt_to_wmi(last_ts))
        if user:
            query['User'] = ('=', user)
        if ltypes:
            query['Type'] = []
            for ltype in ltypes:
                query['Type'].append(('=', ltype))
        if source_names:
            query['SourceName'] = []
            for source_name in source_names:
                query['SourceName'].append(('=', source_name))
        if log_files:
            query['LogFile'] = []
            for log_file in log_files:
                query['LogFile'].append(('=', log_file))
        if event_ids:
            query['EventCode'] = []
            for event_id in event_ids:
                query['EventCode'].append(('=', event_id))
        if message_filters:
            query['NOT Message'] = []
            query['Message'] = []
            for filt in message_filters:
                if filt[0] == '-':
                    query['NOT Message'].append(('LIKE', filt[1:]))
                else:
                    query['Message'].append(('LIKE', filt))

        filters.append(query)

        wmi_sampler = self._get_wmi_sampler(
            instance_key,
            self.CLASS, self.EVENT_PROPERTIES,
            filters=filters,
            host=host, namespace=self.NAMESPACE,
            username=username, password=password,
            and_props=['Message']
        )

        try:
            wmi_sampler.sample()
        except TimeoutException:
            self.log.warning(
                u"[Win32EventLog] WMI query timed out."
                u" class={wmi_class} - properties={wmi_properties} -"
                u" filters={filters} - tags={tags}".format(
                    wmi_class=self.CLASS, wmi_properties=self.EVENT_PROPERTIES,
                    filters=filters, tags=instance_tags
                )
            )
        else:
            for ev in wmi_sampler:
                # for local events we dont need to specify a hostname
                hostname = None if (host == "localhost" or host == ".") else host
                log_ev = LogEvent(ev, hostname, instance_tags, notify,
                                self.init_config.get('tag_event_id', False))

                # Since WQL only compares on the date and NOT the time, we have to
                # do a secondary check to make sure events are after the last
                # timestamp
                if log_ev.is_after(last_ts):
                    self.event(log_ev.to_event_dict())
                else:
                    self.log.debug('Skipping event after %s. ts=%s' % (last_ts, log_ev.timestamp))

            # Update the last time checked
            self.last_ts[instance_key] = datetime.utcnow()


    def _dt_to_wmi(self, dt):
        ''' A wrapper around wmi.from_time to get a WMI-formatted time from a
            time struct.
        '''
        return from_time(year=dt.year, month=dt.month, day=dt.day,
                         hours=dt.hour, minutes=dt.minute,
                         seconds=dt.second, microseconds=0, timezone=0)


class LogEvent(object):
    def __init__(self, ev, hostname, tags, notify_list, tag_event_id):
        self.event = ev
        self.hostname = hostname
        self.tags = self._tags(tags, ev.EventCode) if tag_event_id else tags
        self.notify_list = notify_list
        self.timestamp = self._wmi_to_ts(self.event['TimeGenerated'])

    @property
    def _msg_title(self):
        return '{logfile}/{source}'.format(
            logfile=self.event['Logfile'],
            source=self.event['SourceName'])

    @property
    def _msg_text(self):
        msg_text = ""
        if 'Message' in self.event:
            msg_text = "{message}\n".format(message=self.event['Message'])
        elif 'InsertionStrings' in self.event:
            msg_text = "\n".join([i_str for i_str in self.event['InsertionStrings']
                                  if i_str.strip()])

        if self.notify_list:
            msg_text += "\n{notify_list}".format(
                notify_list=' '.join([" @" + n for n in self.notify_list]))

        return msg_text

    @property
    def _alert_type(self):
        event_type = self.event['Type']
        # Convert to a Datadog alert type
        if event_type == 'Warning':
            return 'warning'
        elif event_type == 'Error':
            return 'error'
        return 'info'

    @property
    def _aggregation_key(self):
        return self.event['SourceName']

    def to_event_dict(self):
        event_dict = {
            'timestamp': self.timestamp,
            'event_type': EVENT_TYPE,
            'msg_title': self._msg_title,
            'msg_text': self._msg_text.strip(),
            'aggregation_key': self._aggregation_key,
            'alert_type': self._alert_type,
            'source_type_name': SOURCE_TYPE_NAME,
            'tags': self.tags
        }
        if self.hostname:
            event_dict['host'] = self.hostname

        return event_dict

    def is_after(self, ts):
        ''' Compare this event's timestamp to a give timestamp. '''
        if self.timestamp >= int(calendar.timegm(ts.timetuple())):
            return True
        return False

    def _wmi_to_ts(self, wmi_ts):
        ''' Convert a wmi formatted timestamp into an epoch.
        '''
        year, month, day, hour, minute, second, microsecond, tz = to_time(wmi_ts)
        tz_delta = timedelta(minutes=int(tz))
        if '+' in wmi_ts:
            tz_delta = - tz_delta

        dt = datetime(year=year, month=month, day=day, hour=hour, minute=minute,
                      second=second, microsecond=microsecond) + tz_delta
        return int(calendar.timegm(dt.timetuple()))

    def _tags(self, tags, event_code):
        ''' Inject additional tags into the list already supplied to LogEvent.
        '''
        tags_list = []
        if tags is not None:
            tags_list += list(tags)
        tags_list.append("event_id:{event_id}".format(event_id=event_code))
        return tags_list
