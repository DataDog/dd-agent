import urllib, urllib2
import httplib
from hashlib import md5
from pprint import pformat as pp
from util import json, headers

def http_emitter(message, logger, agentConfig):
    try: 
        logger.debug('http_emitter: start')    
        # Post back the data
        logger.debug('http_emitter: json convert')
        payload = json.dumps(message)

        logger.debug('http_emitter: json converted, hash')
        logger.debug('http_emitter:\n%s' % pp(message))

        payloadHash = md5(payload).hexdigest()
        postBackData = urllib.urlencode({'payload' : payload, 'hash' : payloadHash})

        logger.debug('http_emitter: hashed')
        logger.debug('http_emitter: attempting postback: ' + agentConfig['ddUrl'])
        
        # Build the request handler
        request = urllib2.Request(agentConfig['ddUrl'] + '/intake/', postBackData, headers(agentConfig))
        
        # Do the request, log any errors
        response = urllib2.urlopen(request)
        
        logger.debug('http_emitter: postback response: ' + str(response.read()))
            
    except urllib2.HTTPError, e:
        logger.error('http_emitter: HTTPError = ' + str(e))
        
    except urllib2.URLError, e:
        logger.error('http_emitter: URLError = ' + str(e))
        
    except httplib.HTTPException, e: # Added for case #26701
        logger.error('http_emitter: HTTPException')
            
    except Exception, e:
        import traceback
        logger.error('http_emitter: Exception = ' + traceback.format_exc())

    else:
        logger.debug('http_emitter: completed')


