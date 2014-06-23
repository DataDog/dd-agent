import os
import httplib
import urllib2
import socket
from urlparse import urlsplit

class UnixHTTPConnection(httplib.HTTPConnection, object):
    """Class used in conjuction with UnixSocketHandler to make urllib2
    compatible with Unix sockets."""
    def __init__(self, unix_socket):
        self._unix_socket = unix_socket
    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._unix_socket)
        self.sock = sock
    def __call__(self, *args, **kwargs):
        httplib.HTTPConnection.__init__(self, *args, **kwargs)
        return self


class UnixSocketHandler(urllib2.AbstractHTTPHandler):
    """Class that makes Unix sockets work with urllib2 without any additional
    dependencies."""
    def unix_open(self, req):
        full_path = "%s%s" % urlsplit(req.get_full_url())[1:3]
        path = os.path.sep
        for part in full_path.split("/"):
            path = os.path.join(path, part)
            if not os.path.exists(path):
                break
            unix_socket = path
        # add a host or else urllib2 complains
        url = req.get_full_url().replace(unix_socket, "/localhost")
        new_req = urllib2.Request(url, req.get_data(), dict(req.header_items()))
        new_req.timeout = req.timeout
        return self.do_open(UnixHTTPConnection(unix_socket), new_req)
    unix_request = urllib2.AbstractHTTPHandler.do_request_

urllib2.install_opener(urllib2.build_opener(UnixSocketHandler()))

uri = 'unix://var/run/docker.sock/containers/json'



if True:
    req = urllib2.Request(uri, None)
    try:
        request = urllib2.urlopen(req)
    except urllib2.URLError, e:
        if "Errno 13" in str(e):
            raise Exception("Unable to connect to socket. dd-agent user must be part of the 'docker' group")
        raise
    response = request.read()