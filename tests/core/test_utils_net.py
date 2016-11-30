# stdlib
from unittest import TestCase
import socket

# 3p
from nose.plugins.skip import SkipTest

# project
from utils.net import inet_pton, _inet_pton_win
from utils.net import IPV6_V6ONLY, IPPROTO_IPV6


class TestUtilsNet(TestCase):
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
