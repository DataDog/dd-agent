import httplib
import urllib2

from util import json, headers

class RabbitMq(object):
    def check(self, logger, agentConfig):

        if 'rabbitmq_status_url' not in agentConfig or \
           'rabbitmq_user' not in agentConfig or \
           'rabbitmq_pass' not in agentConfig or \
            agentConfig['rabbitmq_status_url'] == 'http://www.example.com:55672/json':
            return False

        try:
            logger.debug('getRabbitMQStatus: attempting authentication setup')
            manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            manager.add_password(None, agentConfig['rabbitmq_status_url'], agentConfig['rabbitmq_user'], agentConfig['rabbitmq_pass'])
            handler = urllib2.HTTPBasicAuthHandler(manager)
            opener = urllib2.build_opener(handler)
            urllib2.install_opener(opener)

            logger.debug('getRabbitMQStatus: attempting urlopen')
            req = urllib2.Request(agentConfig['rabbitmq_status_url'], None, headers(agentConfig))

            # Do the request, log any errors
            request = urllib2.urlopen(req)
            response = request.read()

            return json.loads(response)
        except:
            logger.exception('Unable to get RabbitMQ status')
            return False
