# stdlib
from unittest import TestCase

# 3p
from requests.utils import get_environ_proxies

# project
from utils.proxy import set_no_proxy_settings


class TestProxy(TestCase):
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
