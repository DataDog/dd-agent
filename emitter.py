# stdlib
from hashlib import md5
import logging
import re
import sys
import zlib

# 3rd party
import requests
import simplejson as json

# urllib3 logs a bunch of stuff at the info level
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.WARN)
requests_log.propagate = True

# From http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
control_chars = ''.join(map(unichr, range(0,32) + range(127,160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))

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

    proxy = get_proxy_settings(log, agentConfig.get('proxy_settings'),
        agentConfig['use_forwarder'])

    try:
        if proxy is None:
            r = requests.post(url, data=zipped, timeout=10,
                headers=post_headers(agentConfig, zipped))
        else:
            # This shouldn't happen.
            # Starting from 5.0.0, the forwarder should be running on every platform
            # and so there shouldn't be any need for a proxy connection
            r = requests.post(url, data=zipped, timeout=10,
                headers=post_headers(agentConfig, zipped), proxies=proxy)

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
        'Content-MD5': md5(payload).hexdigest()
    }

def get_proxy_settings(log, proxy_settings, use_forwarder):
    if use_forwarder or proxy_settings is None:
        # We are using the forwarder, so it's local trafic. We don't use the proxy
        log.debug("Not using proxy settings")
        return None

    proxy_url = '%s:%s' % (proxy_settings['host'], proxy_settings['port'])

    if proxy_settings.get('user') is not None:
        proxy_auth = proxy_settings['user']
        if proxy_settings.get('password') is not None:
            proxy_auth = '%s:%s' % (proxy_auth, proxy_settings['password'])
        proxy_url = '%s@%s' % (proxy_auth, proxy_url)

    proxy_url = "http://{0}".format(proxy_url)
    log.debug("Using proxy settings %s" % proxy_url.replace(proxy_settings['password'], "*" * 6))
    return {'https': proxy_url}
