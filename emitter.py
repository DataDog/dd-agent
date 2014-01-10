import zlib
import sys
from pprint import pformat as pp
from util import json, md5, get_os
from config import get_ssl_certificate

def get_http_library(proxy_settings, use_forwarder):
    #There is a bug in the https proxy connection in urllib2 on python < 2.6.3
    if use_forwarder:
        # We are using the forwarder, so it's local trafic. We don't use the proxy
        import urllib2

    elif proxy_settings is None or int(sys.version_info[1]) >= 7\
        or (int(sys.version_info[1]) == 6 and int(sys.version_info[2]) >= 3):
        # Python version >= 2.6.3
        import urllib2

    else:
        # Python version < 2.6.3
        import urllib2proxy as urllib2
    return urllib2 

def post_headers(agentConfig, payload):
    return {
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/json',
        'Content-Encoding': 'deflate',
        'Accept': 'text/html, */*',
        'Content-MD5': md5(payload).hexdigest()
    }

def http_emitter(message, logger, agentConfig):
    "Send payload"

    logger.debug('http_emitter: attempting postback to ' + agentConfig['dd_url'])

    # Post back the data
    payload = json.dumps(message)
    zipped = zlib.compress(payload)

    logger.debug("payload_size=%d, compression_ration=%d" %(len(zipped), len(payload)/len(zipped)))

    # Build the request handler
    apiKey = message.get('apiKey', None)
    if not apiKey:
        raise Exception("The http emitter requires an api key")

    url = "%s/intake?api_key=%s" % (agentConfig['dd_url'], apiKey)
    headers = post_headers(agentConfig, zipped)

    proxy_settings = agentConfig.get('proxy_settings', None)
    urllib2 = get_http_library(proxy_settings, agentConfig['use_forwarder'])

    try:
        request = urllib2.Request(url, zipped, headers)
        # Do the request, logger any errors
        opener = get_opener(logger, proxy_settings, agentConfig['use_forwarder'], urllib2)
        if opener is not None:
            urllib2.install_opener(opener)
        response = urllib2.urlopen(request)
        try:
            logger.debug('http_emitter: postback response: ' + str(response.read()))
        finally:
            response.close()
    except urllib2.HTTPError, e:
        if e.code == 202:
            logger.debug("http payload accepted")
        else:
            raise

def get_opener(logger, proxy_settings, use_forwarder, urllib2):
    if use_forwarder:
        # We are using the forwarder, so it's local trafic. We don't use the proxy
        return None

    if proxy_settings is None:
        # urllib2 will figure out how to connect automatically        
        return None

    proxy_url = '%s:%s' % (proxy_settings['host'], proxy_settings['port'])
    if proxy_settings.get('user') is not None:
        proxy_auth = proxy_settings['user']
        if proxy_settings.get('password') is not None:
            proxy_auth = '%s:%s' % (proxy_auth, proxy_settings['password'])
        proxy_url = '%s@%s' % (proxy_auth, proxy_url)
        
    proxy = {'https': proxy_url}
    logger.info("Using proxy settings %s" % proxy)
    proxy_handler = urllib2.ProxyHandler(proxy)
    opener = urllib2.build_opener(proxy_handler)
    return opener
