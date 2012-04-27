import urllib, urllib2
import httplib
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from pprint import pformat as pp
from util import json, headers


def format_body(message, logger):
    payload = json.dumps(message)
    payloadHash = md5(payload).hexdigest()
    postBackData = urllib.urlencode({'payload' : payload, 'hash' : payloadHash})
    return postBackData

def http_emitter(message, logger, agentConfig):
    try: 
        logger.debug('http_emitter: start')    

        # Post back the data
        postBackData = format_body(message, logger)
        logger.debug('http_emitter: attempting postback to ' + agentConfig['ddUrl'])
        
        # Build the request handler
        apiKey = message.get('apiKey', None)
        if apiKey:
            request = urllib2.Request("%s/intake?api_key=%s" % (agentConfig['ddUrl'], apiKey), postBackData, headers(agentConfig))
            # Do the request, log any errors
            response = urllib2.urlopen(request)
            
            logger.debug('http_emitter: postback response: ' + str(response.read()))
        else:
            logger.error("No api key, not sending payload")
            
    except urllib2.HTTPError, e:
        if e.code != 202:
            logger.exception('http_emitter: HTTPError = ' + str(e))
    except urllib2.URLError, e:
        logger.exception('http_emitter: URLError = ' + str(e))
    except httplib.HTTPException, e:
        logger.exception('http_emitter: HTTPException = ' + str(e))
    except:
        logger.exception('http_emitter')
