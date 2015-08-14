#!/usr/bin/python
####
#
#  Copyright (c) 2008-2012 Aerospike, Inc. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
####
# CitrusLeaf Aerospike python library
#
#

from ctypes import create_string_buffer
import socket
import struct
import sys                  # please do not remove. used for stand alone build
from time import time
import types

import log

try:
    import bcrypt
    hasbcrypt = True
except ImportError:
    # bcrypt not installed.
    # This should only be fatal when authentication is required.
    hasbcrypt = False


ERROR_CODES = [1, 50, 51, 52, 53, 54, 55, 56, 60, 61, 62, 65, 70, 80, 81, -1]
logger = None


def set_logger(obj):

    global logger
    logger = obj


def get_logger():

    global logger
    return logger


def log_message(msg, error_flag=False):

    global logger
    if logger is not None and error_flag is True:
        log.print_log(logger, msg, error_flag=True)
    elif logger is not None and error_flag is False:
        log.print_log(logger, msg)


def my_unpack_from(fmtStr, buf, offset):
    sz = struct.calcsize(fmtStr)
    return struct.unpack(fmtStr, buf[offset:offset + sz])


def my_pack_into(fmtStr, buf, offset, *args):
    tmp_array = struct.pack(fmtStr, *args)
    buf[offset:offset + len(tmp_array)] = tmp_array

# 2.5+ has this nice partition call


def partition_25(s, sep):
    return(s.partition(sep))

# 2.4- doesn't


def partition_old(s, sep):
    idx = s.find(sep)
    if idx == -1:
        return(s, "", "")
    return(s[:idx], sep, s[idx + 1:])


g_proto_header = None
g_struct_header_in = None
g_struct_header_out = None
g_partition = None

# 2.5, this will succeed
try:
    g_proto_header = struct.Struct('! Q')
    g_struct_header_in = struct.Struct('! Q B 4x B I 8x H H')
    g_struct_header_out = struct.Struct('! Q B B B B B B I I I H H')
    g_struct_admin_header_in = struct.Struct('! Q B B B B 12x')
    g_struct_admin_header_out = struct.Struct('! Q B B B B 12x')
    g_partition = partition_25

# pre 2.5, if there's no Struct submember, so use my workaround pack/unpack
except:
    struct.unpack_from = my_unpack_from
    struct.pack_into = my_pack_into
    g_partition = partition_old


def receivedata(sock, sz):
    pos = 0
    while pos < sz:
        chunk = sock.recv(sz - pos)
        if pos == 0:
            data = chunk
        else:
            data += chunk
        pos += len(chunk)
    return data


class Socket:

    """Citrusleaf socket: container class for a socket, which allows
    incrementing of timers and statuses easily"""

    def __init__(self, host_obj):
        self.s = None
        self.host_obj = host_obj

    def connect(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as msg:
            log_message(
                " first exception - can't even create socket- don't dun host",
                error_flag=True)
            return False
        try:
            self.host_obj.last_contact = time()
            self.s.settimeout(0.7)
            self.s.connect(self.host_obj.sockaddr[0])
        except socket.error as msg:
            log_message(" connect exception ", error_flag=True)
            self.s.close()
            self.host_obj.markBad()
            log_message(
                'could not open socket, maybe its not up?', error_flag=True)
            return False
        self.host_obj.markGood()
        return True

    def send(self, data):
        try:
            r = self.s.sendall(data)
        except socket.error as msg:
            log_message(" send exception " + str(msg), error_flag=True)
            return False
        if r is not None:
            log_message(
                " send returned error but not exception ", error_flag=True)
            return False
        return True

    def recv(self, data):
        return receivedata(self.s, data)

    # Close in case of a successful connection
    def close(self):
        self.host_obj.markGood()
        if (len(self.host_obj.idle_sockets) < 128):
            # make sure it doesn't expirei in q
            self.s.settimeout(None)
            self.host_obj.idle_sockets.append(self)
        else:
            self.s.close()
            self.s = None
        return

    # return with error
    def close_err(self):
        self.host_obj.markBad()
        self.s.close()
        self.s = None


def hashpassword(password):
    if not hasbcrypt:
        log_message(
            "Authentication failed: bcrypt not installed.", error_flag=True)
        sys.exit(1)

    if password is None:
        password = ""

    if len(password) != 60 or password.startswith("$2a$") is False:
        password = bcrypt.hashpw(password, "$2a$10$7EqJtq98hPqEX7fNZaFWoO")

    return password


def adminWriteHeader(sz, command, field_count):
    send_buf = create_string_buffer(sz)      # from ctypes

    sz = (2 << 48) | (sz - 8)

    if g_struct_admin_header_out is not None:
        g_struct_admin_header_out.pack_into(
            send_buf, 0, sz, 0, 0, command, field_count)
    else:
        struct.pack_into(
            '! Q B B B B 12x', send_buf, 0, sz, 0, 0, command, field_count)

    return send_buf


def adminParseHeader(data):
    if g_struct_admin_header_in is not None:
        rv = g_struct_admin_header_in.unpack(data)
    else:
        rv = struct.unpack('! Q B B B B 12x', data)

    return rv


def authenticate(sock, user, password):
    sz = len(user) + len(password) + 34  # 2 * 5 + 24
    send_buf = adminWriteHeader(sz, 0, 2)

    fmtStr = "! I B %ds I B %ds" % (len(user), len(password))
    struct.pack_into(
        fmtStr, send_buf, 24, len(user) + 1, 0, user, len(password) + 1, 3,
        password)

    try:
        sock.sendall(send_buf)
        recv_buff = receivedata(sock, 24)
        rv = adminParseHeader(recv_buff)
        return rv[2]
    except (
            socket.error, socket.herror, socket.gaierror,
            socket.timeout) as msg:
        log_message("Authentication exception: " + str(msg), error_flag=True)
        return -1


def citrusleaf_info_request(
        host, port, buf, user=None, password=None, debug=False,
        use_this_sock=None):

    # request over TCP
    try:

        if use_this_sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect((host, int(port)))
            if user is not None:
                rc = authenticate(sock, user, password)

                if rc != 0:
                    log_message(
                        "Authentication failed for " + str(user) + ":" + str(
                            rc))
                    sock.close()
                    return rc
        else:
            sock = use_this_sock

        sock.send(buf)

        if debug:
            log_message("info get response")
        # get response
        rsp_hdr = sock.recv(8)
        if debug:
            log_message("response is: ")
            myHexlify(rsp_hdr)
        q = struct.unpack_from("! Q", rsp_hdr, 0)
        sz = q[0] & 0xFFFFFFFFFFFF
        if debug:
            log_message("recv header length " + str(sz))
        if sz > 0:
            rsp_data = receivedata(sock, sz)
            if debug:
                log_message("recv body ")
                myHexlify(rsp_data)
        if use_this_sock is None:
            sock.close()
    except Exception as ex:
        return -1

    # parse out responses
    if sz == 0:
        return None

    if debug:
        log_message("receive as string: " + str(rsp_data))

    return(rsp_data)


def citrusleaf_info(
        host,
        port,
        names=None,
        user=None,
        password=None,
        debug=False,
        sock=None):

    # Passed a set of names: created output buffer
    if names is None:
        q = (2 << 56) | (1 << 48)
        if g_proto_header is not None:
            buf = g_proto_header.pack(q)
        else:
            buf = struct.pack('! Q', q)

    elif isinstance(names, types.StringType):
        q = (2 << 56) | (1 << 48) | (len(names) + 1)
        fmtStr = "! Q %ds B" % len(names)
        buf = struct.pack(fmtStr, q, names, 10)

    else:
        names_l = []
        for name in names:
            names_l.append(name)
            names_l.append("\n")
        namestr = "".join(names_l)
        q = (2 << 56) | (1 << 48) | (len(namestr))
        fmtStr = "! Q %ds" % len(namestr)
        buf = struct.pack(fmtStr, q, namestr)

    if debug:
        log_message("request buffer: ")
        myHexlify(buf)

    rsp_data = citrusleaf_info_request(
        host,
        port,
        buf,
        user,
        password,
        debug,
        use_this_sock=sock)

    if isinstance(rsp_data, int) or rsp_data is None:
        return rsp_data

    # if the original request was a single string, return a single string
    if isinstance(names, types.StringType):

        lines = rsp_data.split("\n")
        name, sep, value = g_partition(lines[0], "\t")

        if name != names:
            msg = " problem: requested name " + str(names) + " got name "
            msg += str(name) + " " + str(user) + " " + str(password)
            log_message(msg)
            return(-1)
        return value

    else:
        rdict = dict()
        for line in rsp_data.split("\n"):
            # this accounts for the trailing '\n'
            if len(line) < 1:
                continue
            if debug:
                log_message(" found line " + str(line))
            name, sep, value = g_partition(line, "\t")
            if debug:
                log_message(
                    "    name: " + str(name) + " value: " + str(value))
            rdict[name] = value

        return rdict


def myHexlify(buf):
    log_message("my hexlify: length " + str(len(buf)))
    for i, c in enumerate(buf):
        log_message("%02x " % ord(c))
        if i % 16 == 15:
            log_message("")
        if i % 16 == 7:
            log_message(": ")
