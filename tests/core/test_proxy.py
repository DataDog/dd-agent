# stdlib
from unittest import TestCase
import logging
from time import sleep

# 3p
from requests.utils import get_environ_proxies
from nose.plugins.attrib import attr

# project
from utils.proxy import set_no_proxy_settings
from utils.dockerutil import DockerUtil

from tornado.web import Application

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

class TestProxy(TestCase):
    @attr(requires='core_integration')
    def test_proxy(self):
        config = {
            "endpoints": {"https://app.datadoghq.com": ["foo"]},
            "proxy_settings": {
                "host": "localhost",
                "port": 3128,
                "user": None,
                "password": None
            }
        }

        app = Application()
        app.skip_ssl_validation = True
        app._agentConfig = config

        trManager = TransactionManager(MAX_WAIT_FOR_REPLAY, MAX_QUEUE_SIZE, THROTTLING_DELAY)
        trManager._flush_without_ioloop = True  # Use blocking API to emulate tornado ioloop
        AgentTransaction.set_tr_manager(trManager)
        app.use_simple_http_client = False # We need proxy capabilities
        AgentTransaction.set_application(app)
        AgentTransaction.set_endpoints(config['endpoints'])
        AgentTransaction._use_blocking_http_client = True # Use the synchronous HTTP client

        def get_log(logfile):
            return self.docker_client.exec_start(
                self.docker_client.exec_create(CONTAINER_NAME, 'cat ' + logfile)['Id'])

        while("Accepting HTTP Socket connections" not in get_log('/var/log/squid/cache.log')):
            sleep(1) # Give time for the container to properly start, otherwise we get 'Proxy CONNECT aborted'

        AgentTransaction('body', {}, "") # Create and flush the transaction
        self.assertTrue("CONNECT" in get_log('/var/log/squid/access.log')) # There should be an entry in the proxy access log
        self.assertEquals(len(trManager._endpoints_errors), 2) # There should be an error since we gave a bogus api_key

    def setUp(self):
        self.docker_client = DockerUtil().client

        self.docker_client.pull(CONTAINER_TO_RUN)

        self.container = self.docker_client.create_container(CONTAINER_TO_RUN, detach=True, name=CONTAINER_NAME,
            ports=[3128], host_config=self.docker_client.create_host_config(port_bindings={3128: 3128}))
        log.info("Starting container: {0}".format(CONTAINER_TO_RUN))
        self.docker_client.start(CONTAINER_NAME)

    def tearDown(self):
        log.info("Stopping container: {0}".format(CONTAINER_TO_RUN))
        self.docker_client.remove_container(CONTAINER_NAME, force=True)
