# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from hashlib import md5
import logging
import re
import zlib
import unicodedata

# 3p
import requests
import simplejson as json

# project
from config import get_version

from utils.proxy import set_no_proxy_settings
set_no_proxy_settings()

# urllib3 logs a bunch of stuff at the info level
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.WARN)
requests_log.propagate = True

# From http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
control_chars = ''.join(map(unichr, range(0, 32) + range(127, 160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))


def remove_control_chars(s, log):
    if isinstance(s, str):
        sanitized = control_char_re.sub('', s)
    elif isinstance(s, unicode):
        sanitized = ''.join(['' if unicodedata.category(c) in ['Cc','Cf'] else c
                            for c in u'{}'.format(s)])
    if sanitized != s:
        log.warning('Removed control chars from string: ' + s)
    return sanitized

def remove_undecodable_chars(s, log):
    sanitized = s
    if isinstance(s, str):
        try:
            s.decode('utf8')
        except UnicodeDecodeError:
            sanitized = s.decode('utf8', errors='ignore')
            log.warning(u'Removed undecodable chars from string: ' + s.decode('utf8', errors='replace'))
    return sanitized

def sanitize_payload(item, log, sanitize_func):
    if isinstance(item, dict):
        newdict = {}
        for k, v in item.iteritems():
            newval = sanitize_payload(v, log, sanitize_func)
            newkey = sanitize_func(k, log)
            newdict[newkey] = newval
        return newdict
    if isinstance(item, list):
        newlist = []
        for listitem in item:
            newlist.append(sanitize_payload(listitem, log, sanitize_func))
        return newlist
    if isinstance(item, tuple):
        newlist = []
        for listitem in item:
            newlist.append(sanitize_payload(listitem, log, sanitize_func))
        return tuple(newlist)
    if isinstance(item, basestring):
        return sanitize_func(item, log)

    return item

def http_emitter(message, log, agentConfig, endpoint):
    "Send payload"
    url = agentConfig['dd_url']

    log.debug('http_emitter: attempting postback to ' + url)

    # Post back the data
    try:
        try:
            payload = json.dumps(message)
        except UnicodeDecodeError:
            newmessage = sanitize_payload(message, log, remove_control_chars)
            try:
                payload = json.dumps(newmessage)
            except UnicodeDecodeError:
                log.info('Removing undecodable characters from payload')
                newmessage = sanitize_payload(newmessage, log, remove_undecodable_chars)
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

    zipped = zlib.compress(payload)

    log.debug("payload_size=%d, compressed_size=%d, compression_ratio=%.3f"
              % (len(payload), len(zipped), float(len(payload))/float(len(zipped))))

    apiKey = message.get('apiKey', None)
    if not apiKey:
        raise Exception("The http emitter requires an api key")

    url = "{0}/intake/{1}?api_key={2}".format(url, endpoint, apiKey)

    try:
        headers = post_headers(agentConfig, zipped)
        r = requests.post(url, data=zipped, timeout=5, headers=headers)

        r.raise_for_status()

        if r.status_code >= 200 and r.status_code < 205:
            log.debug("Payload accepted")

    except Exception:
        log.exception("Unable to post payload.")
        try:
            log.error("Received status code: {0}".format(r.status_code))
        except Exception:
            pass


def post_headers(agentConfig, payload):
    return {
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/json',
        'Content-Encoding': 'deflate',
        'Accept': 'text/html, */*',
        'Content-MD5': md5(payload).hexdigest(),
        'DD-Collector-Version': get_version()
    }
