# stdlib
from unittest import TestCase
import socket
import threading
import Queue
from collections import defaultdict

# 3p
import mock

# project
from dogstatsd import mapto_v6, get_socket_address
from dogstatsd import Server, init
from utils.net import IPV6_V6ONLY, IPPROTO_IPV6


class TestFunctions(TestCase):
    def test_mapto_v6(self):
        self.assertIsNone(mapto_v6('foo'))
        self.assertIsNone(mapto_v6('192.'))
        self.assertEqual(mapto_v6('192.168.1.1'), '::ffff:192.168.1.1')
        self.assertEqual(mapto_v6('::1'), '::1')
        self.assertEqual(mapto_v6('ff00::'), 'ff00::')

    def test_get_socket_address(self):
        with mock.patch('dogstatsd.socket.getaddrinfo') as getaddrinfo:
            getaddrinfo.return_value = [(2, 2, 17, '', ('192.168.1.1', 80))]
            self.assertEqual(get_socket_address('example.com', 80), ('::ffff:192.168.1.1', 80, 0, 0))
            getaddrinfo.return_value = [(30, 2, 17, '', ('::1', 80, 0, 0))]
            self.assertEqual(get_socket_address('example.com', 80), ('::1', 80, 0, 0))
        self.assertIsNone(get_socket_address('foo', 80))

    @mock.patch('dogstatsd.get_config')
    @mock.patch('dogstatsd.Server')
    def test_init(self, s, gc):
        gc.return_value = defaultdict(str)
        gc.return_value['non_local_traffic'] = True
        gc.return_value['use_dogstatsd'] = True

        init()

        # if non_local_traffic was passed, use IPv4 wildcard
        s.assert_called_once()
        args, _ = s.call_args
        self.assertEqual(args[1], '0.0.0.0')


class TestServer(TestCase):
    def test_init(self):
        s = Server(None, 'localhost', '1234')

        self.assertIsNone(s.sockaddr)
        self.assertIsNone(s.socket)

    @mock.patch('dogstatsd.select')
    def test_start(self, select):
        select.select.side_effect = [KeyboardInterrupt, SystemExit]
        s1 = Server(mock.MagicMock(), '::1', '1234')
        s1.start()
        self.assertEqual(s1.socket.family, socket.AF_INET6)

        s2 = Server(mock.MagicMock(), '127.0.0.1', '2345')
        s2.start()
        self.assertEqual(s2.socket.family, socket.AF_INET6)

        s2 = Server(mock.MagicMock(), 'foo', '80')
        s2.start()
        self.assertFalse(s2.running)

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
