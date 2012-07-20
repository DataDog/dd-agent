import unittest
from checks.net.haproxy import HAProxyEvents, HAProxyMetrics, get_data, process_data
import logging
logging.basicConfig()
import subprocess
import time
import urllib2

MAX_WAIT = 150


class HaproxyTestCase(unittest.TestCase):
	def _wait(self, url):
		loop = 0
		while True:
			try:
				STATS_URL = ";csv;norefresh"
				passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
				passman.add_password(None, url, "datadog", "isdevops")
				authhandler = urllib2.HTTPBasicAuthHandler(passman)
				opener = urllib2.build_opener(authhandler)
				urllib2.install_opener(opener)
				url = "%s%s" % (url,STATS_URL)
				req = urllib2.Request(url)
				request = urllib2.urlopen(req)
				break
			except:
				time.sleep(0.5)
				loop+=1
				if loop >= MAX_WAIT:
					break   

	def setUp(self):
		self.metrics_check = HAProxyMetrics(logging.getLogger())
		self.events_check = HAProxyEvents(logging.getLogger())

		self.process = None
		try:
		    # Start elasticsearch
		    self.process = subprocess.Popen(["haproxy","-f","/tmp/haproxy.cfg"],
		                executable="haproxy",
		                stdout=subprocess.PIPE,
		                stderr=subprocess.PIPE)

		    # Wait for it to really start
		    self._wait("http://localhost:3834/stats")
		except:
			logging.getLogger().exception("Cannot instantiate haproxy")


	def tearDown(self):
		if self.process is not None:
			self.process.terminate()

	def testCheckEvents(self):
		agentConfig = {'haproxy_url': 'http://localhost:3834/stats', 
		'haproxy_user': 'datadog', 
		'haproxy_password':'isdevops',
		'version': '0.1',
		'apiKey': 'toto'}
		

		r = self.events_check.check(logging.getLogger(),agentConfig)

		try:
			data = get_data(agentConfig, logging.getLogger())

		except Exception,e:
			logging.getLogger().exception('Unable to get haproxy statistics %s' % e)
			assert(False)

		new_data = []

		for line in data:
			new_data.append(line.replace("OPEN", "DOWN"))

		process_data(self.events_check, agentConfig, new_data)

		self.assertTrue(len(self.events_check.events) == 1)


	def testCheckMetrics(self):
		agentConfig = {'haproxy_url': 'http://localhost:3834/stats', 
		'haproxy_user': 'datadog', 
		'haproxy_password':'isdevops',
		'version': '0.1',
		'apiKey': 'toto'}
		r = self.metrics_check.check(agentConfig)

		#We run it twice as we want to check counter metrics too
		r = self.metrics_check.check(agentConfig)
		def _check(slf, r):
			slf.assertTrue(type(r) == type([]))
			slf.assertTrue(len(r) > 0)
			slf.assertEquals(len([t for t in r if t[0] == "haproxy.backend.bytes.in_rate"]), 2, r)
			slf.assertEquals(len([t for t in r if t[0] == "haproxy.frontend.session.current"]), 1, r)
		_check(self, r)

		# Same check, with wrong data
		agentConfig = {'haproxy_url': 'http://localhost:3834/stats', 
		'haproxy_user': 'wrong', 
		'haproxy_password':'isdevops',
		'version': '0.1',
		'apiKey': 'toto'}

		r = self.metrics_check.check(agentConfig)
		self.assertFalse(r)






