# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging
import re
import zlib
import unicodedata

# 3rd party
import simplejson as json

log = logging.getLogger(__name__)

# From http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
control_chars = ''.join(map(unichr, range(0, 32) + range(127, 160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))


def remove_control_chars(s):
    if isinstance(s, str):
        sanitized = control_char_re.sub('', s)
    elif isinstance(s, unicode):
        sanitized = ''.join(['' if unicodedata.category(c) in ['Cc','Cf'] else c
                            for c in u'{}'.format(s)])
    if sanitized != s:
        log.warning('Removed control chars from string: ' + s)
    return sanitized

def remove_undecodable_chars(s):
    sanitized = s
    if isinstance(s, str):
        try:
            s.decode('utf8')
        except UnicodeDecodeError:
            sanitized = s.decode('utf8', errors='ignore')
            log.warning(u'Removed undecodable chars from string: ' + s.decode('utf8', errors='replace'))
    return sanitized

def sanitize_payload(item, sanitize_func):
    if isinstance(item, dict):
        newdict = {}
        for k, v in item.iteritems():
            newval = sanitize_payload(v, sanitize_func)
            newkey = sanitize_func(k, log)
            newdict[newkey] = newval
        return newdict
    if isinstance(item, list):
        newlist = []
        for listitem in item:
            newlist.append(sanitize_payload(listitem, sanitize_func))
        return newlist
    if isinstance(item, tuple):
        newlist = []
        for listitem in item:
            newlist.append(sanitize_payload(listitem, sanitize_func))
        return tuple(newlist)
    if isinstance(item, basestring):
        return sanitize_func(item, log)

    return item



class CollectorPayload(object):

    def serialize(self, message):

        try:
            try:
                payload = json.dumps(message)
            except UnicodeDecodeError:
                newmessage = sanitize_payload(message, remove_control_chars)
                try:
                    payload = json.dumps(newmessage)
                except UnicodeDecodeError:
                    log.info('Removing undecodable characters from payload')
                    newmessage = sanitize_payload(newmessage, remove_undecodable_chars)
                    payload = json.dumps(newmessage)
        except UnicodeDecodeError as ude:
            log.error('http_emitter: Unable to convert message to json %s', ude)
            # early return as we can't actually process the message
            return
        except RuntimeError as rte:
            log.error('http_emitter: runtime error dumping message to json %s', rte)
            # early return as we can't actually process the message
            return
        except Exception as e:
            log.error('http_emitter: unknown exception processing message %s', e)
            return


    def emit(self):
        data = self.serialize(self.transform())
        pass

class LegacyCollectorPayload(CollectorPayload):

    def __init__(self, data):
        self.data = data

    def transform(self):
        # No transformation needed here
        return self.data


class MetricsCollectorPayload(CollectorPayload):

    def __init__(self, metrics):
        self.metrics = metrics

    def transform(self):
        metrics_payload = {"series": []}
        for ts in self.metrics:
            metrics_payload["series"].append(
                {
                    "metric": ts[0],
                    "points": [[ts[1], ts[2]]],
                    "type": ts[3].get('type'),
                    "host": ts[3].get('hostname'),
                    "tags": ts[3].get('tags'),
                }

            )

        return metrics_payload



class EventsCollectorPayload(CollectorPayload):

    def __init__(self, events):
        self.events = events

    def transform(self):


class CheckRunsCollectorPayload(CollectorPayload):

    def __init__(self, check_runs):
        self.check_runs = check_runs

    def transform(self):
        # No transformation needed here
        return self.check_runs




