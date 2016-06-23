# stdlib
from unittest import TestCase
import socket
import threading
import Queue

# 3p
import mock

# project
from dogstatsd import mapto_v6, normalize_host
from dogstatsd import Server
from utils.net import IPV6_V6ONLY, IPPROTO_IPV6


class TestFunctions(TestCase):
    def test_mapto_v6(self):
        self.assertIsNone(mapto_v6('foo'))
        self.assertIsNone(mapto_v6('192.'))
        self.assertEqual(mapto_v6('192.168.1.1'), '::ffff:192.168.1.1')
        self.assertEqual(mapto_v6('::1'), '::1')
        self.assertEqual(mapto_v6('ff00::'), 'ff00::')

    def test_normalize_host(self):
        with mock.patch('dogstatsd.socket.gethostbyname') as gethostbyname:
            gethostbyname.return_value = '192.168.1.1'
            self.assertEqual(normalize_host('example.com'), '::ffff:192.168.1.1')
            gethostbyname.return_value = 'foobar'
            self.assertEqual(normalize_host('example.com'), '::1')
        self.assertEqual(normalize_host('foo'), '::1')


class TestServer(TestCase):
    @mock.patch('dogstatsd.normalize_host')
    def test_init(self, nh):
        s = Server(None, 'localhost', '1234')
        self.assertEqual(s.port, 1234)
        self.assertIsNone(s.socket)
        nh.assertCalledOnceWith('localhost')

    @mock.patch('dogstatsd.select')
    def test_start(self, select):
        select.select.side_effect = [KeyboardInterrupt, SystemExit]
        s1 = Server(mock.MagicMock(), '::1', '1234')
        s1.start()
        self.assertEqual(s1.socket.family, socket.AF_INET6)

        s2 = Server(mock.MagicMock(), '127.0.0.1', '2345')
        s2.start()
        self.assertEqual(s2.socket.family, socket.AF_INET6)

    def _get_socket(self, addr, port):
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        sock.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)
        sock.bind((addr, port))
        return sock

    def test_connection_v4(self):
        # start the server with a v4 mapped address
        sock = self._get_socket('::ffff:127.0.0.1', 12345)
        results = Queue.Queue()

        def listen():
            while True:
                res = sock.recvfrom(1024)
                results.put(res)

        thread = threading.Thread(target=listen)
        thread.daemon = True
        thread.start()

        # send packets with a v4 client
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.sendto('msg4', ('127.0.0.1', 12345))
        msg = results.get(True, 1)
        self.assertEqual(msg[0], 'msg4')

        # send packets with a v6 client
        client_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        client_sock.sendto('msg6', ('::1', 12345))
        self.assertRaises(Queue.Empty, results.get, True, 1)

    def test_connection_v6(self):
        # start the server with a v6 address
        sock = self._get_socket('::1', 12345)
        results = Queue.Queue()

        def listen():
            while True:
                res = sock.recvfrom(1024)
                results.put(res)

        thread = threading.Thread(target=listen)
        thread.daemon = True
        thread.start()

        # send packets with a v4 client
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.sendto('msg4', ('127.0.0.1', 12345))
        self.assertRaises(Queue.Empty, results.get, True, 1)

        # send packets with a v6 client
        client_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        client_sock.sendto('msg6', ('::1', 12345))
        msg = results.get(True, 1)
        self.assertEqual(msg[0], 'msg6')
