import urllib, urllib2
import httplib
import zlib

from pprint import pformat as pp
from util import json, md5


def format_body(message):
    payload = json.dumps(message)
    return zlib.compress(payload)

def post_headers(agentConfig, payload):
    return {
        'User-Agent': 'Datadog Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/json',
        'Content-Encoding': 'deflate',
        'Accept': 'text/html, */*',
        'Content-MD5': md5(payload).hexdigest()
    }

def http_emitter(message, logger, agentConfig):
    try:
        logger.debug('http_emitter: start')

        # Post back the data
        postBackData = format_body(message)

        logger.debug('http_emitter: attempting postback to ' + agentConfig['dd_url'])

        # Build the request handler
        apiKey = message.get('apiKey', None)
        if apiKey:
            url = "%s/intake?api_key=%s" % (agentConfig['dd_url'], apiKey)
            headers = post_headers(agentConfig, postBackData)
            request = urllib2.Request(url, postBackData, headers)
            # Do the request, log any errors
            response = urllib2.urlopen(request)

            logger.debug('http_emitter: postback response: ' + str(response.read()))
        else:
            logger.error("No api key, not sending payload")
    except SystemExit, KeyboardInterrupt:
        raise
    except urllib2.HTTPError, e:
        if e.code != 202:
            logger.exception('http_emitter: HTTPError = ' + str(e))
    except urllib2.URLError, e:
        logger.exception('http_emitter: URLError = ' + str(e))
    except httplib.HTTPException, e:
        logger.exception('http_emitter: HTTPException = ' + str(e))
    except:
        #FIXME mattp: can we limit this to Exception?
        logger.exception('http_emitter')
