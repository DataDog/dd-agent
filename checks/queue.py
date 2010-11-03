import platform
pythonVersion = platform.python_version_tuple()

if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
	import json
else:
	import minjson

import httplib
import urllib2
import traceback


class RabbitMq(object):
	def check(self, logger, agentConfig):
		logger.debug('getRabbitMQStatus: start')

		if 'rabbitMQStatusUrl' not in agentConfig or \
		   'rabbitMQUser' not in agentConfig or \
		   'rabbitMQPass' not in agentConfig or \
			agentConfig['rabbitMQStatusUrl'] == 'http://www.example.com:55672/json':

			logger.debug('getRabbitMQStatus: config not set')
			return False

		logger.debug('getRabbitMQStatus: config set')

		try:
			logger.debug('getRabbitMQStatus: attempting authentication setup')
			manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
			manager.add_password(None, agentConfig['rabbitMQStatusUrl'], agentConfig['rabbitMQUser'], agentConfig['rabbitMQPass'])
			handler = urllib2.HTTPBasicAuthHandler(manager)
			opener = urllib2.build_opener(handler)
			urllib2.install_opener(opener)

			logger.debug('getRabbitMQStatus: attempting urlopen')
			req = urllib2.Request(agentConfig['rabbitMQStatusUrl'], None, headers)

			# Do the request, log any errors
			request = urllib2.urlopen(req)
			response = request.read()

		except urllib2.HTTPError, e:
			logger.error('Unable to get RabbitMQ status - HTTPError = ' + str(e))
			return False

		except urllib2.URLError, e:
			logger.error('Unable to get RabbitMQ status - URLError = ' + str(e))
			return False

		except httplib.HTTPException, e:
			logger.error('Unable to get RabbitMQ status - HTTPException = ' + str(e))
			return False

		except Exception, e:
			logger.error('Unable to get RabbitMQ status - Exception = ' + traceback.format_exc())
			return False
			
		try:

			if int(pythonVersion[1]) >= 6:
				logger.debug('getRabbitMQStatus: json read')
				status = json.loads(response)

			else:
				logger.debug('getRabbitMQStatus: minjson read')
				status = minjson.safeRead(response)

		except Exception, e:
			logger.error('Unable to load RabbitMQ status JSON - Exception = ' + traceback.format_exc())
			return False

		logger.debug('getRabbitMQStatus: completed, returning')
		return status
		