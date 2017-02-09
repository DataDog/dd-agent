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





def post_json(url, message, agentConfig, log):

    # Post back the data

    log.debug('http_emitter: attempting postback to ' + url)

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



def http_emitter(message, log, agentConfig, endpoint):
    "Send payload"
    apiKey = message.get('apiKey', None)
    if not apiKey:
        raise Exception("The http emitter requires an api key")
    legacy_url = "{0}/intake/{1}?api_key={2}".format(agentConfig['dd_url'], endpoint, apiKey)
    metrics_endpoint = "{0}/api/v1/series?api_key={1}".format(agentConfig['dd_url'], apiKey)

    metrics = list(message.get('metrics'))
    del message['metrics']

    metrics_payload = {"series": []}

    for ts in metrics:
        metrics_payload["series"].append(
            {
                "metric": ts[0],
                "points": [[ts[1], ts[2]]],
                "type": ts[3].get('type'),
                "host": ts[3].get('hostname'),
                "tags": ts[3].get('tags'),
            }

        )

    post_json(legacy_url, message, agentConfig, log)
    post_json(metrics_endpoint, metrics_payload, agentConfig, log)


def post_headers(agentConfig, payload):
    return {
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/json',
        'Content-Encoding': 'deflate',
        'Accept': 'text/html, */*',
        'Content-MD5': md5(payload).hexdigest(),
        'DD-Collector-Version': get_version()
    }
