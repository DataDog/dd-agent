# stdlib
from hashlib import md5
import logging
import re
import sys
import zlib

# 3rd party
import requests
import simplejson as json

# project
from config import get_version

# urllib3 logs a bunch of stuff at the info level
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.WARN)
requests_log.propagate = True

# From http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
control_chars = ''.join(map(unichr, range(0,32) + range(127,160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))

NO_PROXY = {
# See https://github.com/kennethreitz/requests/issues/879
# and https://github.com/DataDog/dd-agent/issues/1112
    'no': 'pass',
}


def remove_control_chars(s):
    return control_char_re.sub('', s)

def http_emitter(message, log, agentConfig):
    "Send payload"
    url = agentConfig['dd_url']

    log.debug('http_emitter: attempting postback to ' + url)

    # Post back the data
    try:
        payload = json.dumps(message)
    except UnicodeDecodeError:
        message = remove_control_chars(message)
        payload = json.dumps(message)

    zipped = zlib.compress(payload)

    log.debug("payload_size=%d, compressed_size=%d, compression_ratio=%.3f" % (len(payload), len(zipped), float(len(payload))/float(len(zipped))))

    apiKey = message.get('apiKey', None)
    if not apiKey:
        raise Exception("The http emitter requires an api key")

    url = "{0}/intake?api_key={1}".format(url, apiKey)

    try:
        r = requests.post(url, data=zipped, timeout=5,
            headers=post_headers(agentConfig, zipped), proxies=NO_PROXY)

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
    