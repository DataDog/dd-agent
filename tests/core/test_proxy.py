# stdlib
from unittest import TestCase
import logging

# 3p
from requests.utils import get_environ_proxies
from nose.plugins.attrib import attr

# project
from utils.proxy import set_no_proxy_settings, config_proxy_skip
from utils.dockerutil import DockerUtil

from tornado.web import Application
from tornado.testing import AsyncTestCase

from ddagent import (
    MAX_QUEUE_SIZE,
    MAX_WAIT_FOR_REPLAY,
    THROTTLING_DELAY,
    AgentTransaction
)

from transaction import TransactionManager

log = logging.getLogger('tests')

CONTAINER_TO_RUN = "datadog/squid"
CONTAINER_NAME = "test-squid"
PROXY_PORT = 3128

class TestNoProxy(TestCase):
    @attr(requires="core_integration")
    def test_no_proxy(self):
        """
        Starting with Agent 5.0.0, there should always be a local forwarder
        running and all payloads should go through it. So we should make sure
        that we pass the no_proxy environment variable that will be used by requests
        (See: https://github.com/kennethreitz/requests/pull/945 )
        """
        from os import environ as env

        env["http_proxy"] = "http://localhost:3128"
        env["https_proxy"] = env["http_proxy"]
        env["HTTP_PROXY"] = env["http_proxy"]
        env["HTTPS_PROXY"] = env["http_proxy"]

        set_no_proxy_settings()

        self.assertTrue("no_proxy" in env)

        self.assertEquals(env["no_proxy"], "127.0.0.1,localhost,169.254.169.254")
        self.assertEquals({}, get_environ_proxies(
            "http://localhost:17123/api/v1/series"))

        expected_proxies = {
            'http': 'http://localhost:3128',
            'https': 'http://localhost:3128',
            'no': '127.0.0.1,localhost,169.254.169.254'
        }
        environ_proxies = get_environ_proxies("https://www.google.com")
        self.assertEquals(expected_proxies, environ_proxies, (expected_proxies, environ_proxies))

        # Clear the env variables set
        env.pop("http_proxy", None)
        env.pop("https_proxy", None)
        env.pop("HTTP_PROXY", None)
        env.pop("HTTPS_PROXY", None)

    @attr(requires="core_integration")
    def test_proxy_skip(self):
        """
        Proxy should be skipped when so specified...
        """
        proxies = {
            'http': 'http://localhost:3128',
            'https': 'http://localhost:3128',
            'no': '127.0.0.1,localhost,169.254.169.254,host.foo.bar'
        }

        gen_proxies = config_proxy_skip(proxies, 's3://anything', skip_proxy=True)
        self.assertTrue('http' in gen_proxies)
        self.assertTrue('https' in gen_proxies)
        self.assertEquals(gen_proxies.get('http'), None)
        self.assertEquals(gen_proxies.get('https'), None)

        gen_proxies = config_proxy_skip(proxies, 'https://host.foo.bar', skip_proxy=False)
        self.assertEquals(gen_proxies.get('http'), None)
        self.assertEquals(gen_proxies.get('https'), None)

        gen_proxies = config_proxy_skip(proxies, 'baz', skip_proxy=False)
        self.assertEquals(proxies, gen_proxies)

        proxies.pop('no')
        gen_proxies = config_proxy_skip(proxies, 'baz', skip_proxy=False)
        self.assertEquals(proxies, gen_proxies)


class CustomAgentTransaction(AgentTransaction):

    def on_response(self, response):
        super(CustomAgentTransaction, self).on_response(response)
        if hasattr(self, '_test'):
            self._test.stop()

@attr('unix')
class TestProxy(AsyncTestCase):
    @attr(requires='core_integration')
    def test_proxy(self):
        config = {
            "endpoints": {"https://app.datadoghq.com": ["foo"]},
            "proxy_settings": {
                "host": "localhost",
                "port": PROXY_PORT,
                "user": None,
                "password": None
            }
        }

        app = Application()
        app.skip_ssl_validation = True
        app._agentConfig = config

        trManager = TransactionManager(MAX_WAIT_FOR_REPLAY, MAX_QUEUE_SIZE, THROTTLING_DELAY)
        trManager._flush_without_ioloop = True  # Use blocking API to emulate tornado ioloop
        CustomAgentTransaction.set_tr_manager(trManager)
        app.use_simple_http_client = False # We need proxy capabilities
        app.agent_dns_caching = False
        # _test is the instance of this class. It is needed to call the method stop() and deal with the asynchronous
        # calls as described here : http://www.tornadoweb.org/en/stable/testing.html
        CustomAgentTransaction._test = self
        CustomAgentTransaction.set_application(app)
        CustomAgentTransaction.set_endpoints(config['endpoints'])

        CustomAgentTransaction('body', {}, "") # Create and flush the transaction
        self.wait()
        del CustomAgentTransaction._test
        access_log = self.docker_client.exec_start(
            self.docker_client.exec_create(CONTAINER_NAME, 'cat /var/log/squid/access.log')['Id'])
        self.assertTrue("CONNECT" in access_log) # There should be an entry in the proxy access log
        self.assertEquals(len(trManager._endpoints_errors), 1) # There should be an error since we gave a bogus api_key

    def setUp(self):
        super(TestProxy, self).setUp()
        self.docker_client = DockerUtil().client

        self.docker_client.pull(CONTAINER_TO_RUN)

        self.container = self.docker_client.create_container(CONTAINER_TO_RUN, detach=True, name=CONTAINER_NAME,
            ports=[PROXY_PORT], host_config=self.docker_client.create_host_config(port_bindings={3128: PROXY_PORT}))
        log.info("Starting container: {0}".format(CONTAINER_TO_RUN))
        self.docker_client.start(CONTAINER_NAME)
        for line in self.docker_client.logs(CONTAINER_NAME, stdout=True, stream=True):
            if "Accepting HTTP Socket connections" in line:
                break # Wait for the container to properly start, otherwise we get 'Proxy CONNECT aborted'

    def tearDown(self):
        log.info("Stopping container: {0}".format(CONTAINER_TO_RUN))
        self.docker_client.remove_container(CONTAINER_NAME, force=True)
        super(TestProxy, self).tearDown()
