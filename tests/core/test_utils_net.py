# stdlib
from unittest import TestCase
from mock import MagicMock, patch
import socket
from urlparse import urlparse
from time import sleep

# 3p
from nose.plugins.skip import SkipTest

# project
from utils.net import inet_pton, _inet_pton_win
from utils.net import IPV6_V6ONLY, IPPROTO_IPV6
from utils.net import DNSCache
from config import get_url_endpoint

DEFAULT_ENDPOINT = "https://app.datadoghq.com"

class TestUtilsNet(TestCase):
    DNS_TTL = 3

    def test__inet_pton_win(self):

        if _inet_pton_win != inet_pton:
            raise SkipTest('socket.inet_pton is available, no need to test')

        # only test what we need this function for
        self.assertEqual(inet_pton(socket.AF_INET, '192.168.1.1'), '\xc0\xa8\x01\x01')
        self.assertRaises(socket.error, inet_pton, socket.AF_INET, 'foo')
        self.assertEqual(inet_pton(socket.AF_INET6, '::1'),
                         '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01')
        self.assertRaises(socket.error, inet_pton, socket.AF_INET6, 'foo')

    def test_constants(self):
        if not hasattr(socket, 'IPPROTO_IPV6'):
            self.assertEqual(IPPROTO_IPV6, 41)

        if not hasattr(socket, 'IPV6_V6ONLY'):
            self.assertEqual(IPV6_V6ONLY, 27)

    def test_dns_cache(self):
        side_effects = [(None, None, ['1.1.1.1', '2.2.2.2']),
                        (None, None, ['3.3.3.3'])]
        mock_resolve = MagicMock(side_effect=side_effects)
        cache = DNSCache(self.DNS_TTL)
        with patch('socket.gethostbyaddr', mock_resolve):
            ip = cache.resolve('foo')
            self.assertTrue(ip in side_effects[0][2])
            sleep(self.DNS_TTL + 1)
            ip = cache.resolve('foo')
            self.assertTrue(ip in side_effects[1][2])

        # resolve intake
        endpoint = get_url_endpoint(DEFAULT_ENDPOINT)
        location = urlparse(endpoint)
        ip = cache.resolve(location.netloc)
        self.assertNotEqual(ip, location.netloc)
