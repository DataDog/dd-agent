#!/usr/bin/python
####
#
#  Copyright (c) 2008-2012 Aerospike, Inc. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
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

import sys                  # please do not remove. used for stand alone build

import socket                   # socket needs no introduction
import struct                   # gives us a parser/encoder for binary data

from ctypes import create_string_buffer      # gives us pre-allocated buffers

from time import time, sleep    # try to limit expansion of symbol tables?
import types
import thread
import Queue

try:
    import bcrypt
    hasbcrypt = True
except:
    # bcrypt not installed.
    # This should only be fatal when authentication is required.
    hasbcrypt = False

# AS_PROTO
# Offset  name meaning
# 0     version (1 byte)      the current version number = 2
# 1     type (1 byte)         AS_INFO = 1; AS_MSG = 3
# 2     size (6 bytes)        bytes to follow

# AS_MSG
# 0     header_sz              22 bytes currently
# 1     info1 (1 byte)         Bitfield of meaning see below
# 1     info2 (1 byte)         Bitfield of meaning see below
# 1     info3 (1 byte)         Bitfield of meaning see below
# 1     unused (1 byte)        Bitfield of meaning see below
# 1     result_code (1 bytes)  result of request
# 4     generation (4 bytes)   the incoming generation id, or returned generation id
# 8     record_ttl             record's TTL - seconds - when it will expire
# 12    transaction_ttl        transactions TTL - milliseconds - when it will expire
# 16    n_fields (2 bytes)     number of fields to follow
# 20    n_ops (2 bytes)        number of operations to follow
# 22    data (sz bytes)        payload

# 'info1' is a bitfield
# AS_MSG_INFO1_READ             (1 << 0)        // contains a read operation
# AS_MSG_INFO1_GET_ALL          (1 << 1)        // get all bins, period
# AS_MSG_INFO1_GET_ALL_NODATA   (1 << 2)        // get all bins WITHOUT data (currently unimplemented)
# AS_MSG_INFO1_VERIFY           (1 << 3)        // verify is a GET transaction that includes data, and assert if the data aint right

# AS_MSG_INFO2_WRITE                (1 << 0)        // contains a write semantic
# AS_MSG_INFO2_DELETE           (1 << 1)        // fling a record into the belly of Moloch
# AS_MSG_INFO2_GENERATION           (1 << 2)        // pay attention to the generation
# AS_MSG_INFO2_GENERATION_GT        (1 << 3)        // apply write if new generation >= old, good for restore
# AS_MSG_INFO2_GENERATION_DUP   (1 << 4)        // if a generation collision, create a duplicate
# AS_MSG_INFO2_WRITE_UNIQUE     (1 << 5)        // write only if it doesn't exist
# AS_MSG_INFO2_WRITE_BINUNIQUE  (1 << 6)

# define AS_MSG_INFO3_LAST                  (1 << 0)        // this is the last of a multi-part message
# define AS_MSG_INFO3_TRACE             (1 << 1)        // apply server trace logging for this transaction
# define AS_MSG_INFO3_TOMBSTONE         (1 << 2)        // if set on response, a version was a delete tombstone

AS_MSG_INFO1_READ = 1
AS_MSG_INFO1_GET_ALL = 2
AS_MSG_INFO1_GET_ALL_NODATA = 4
AS_MSG_INFO1_VERIFY = 8

AS_MSG_INFO2_WRITE = 1
AS_MSG_INFO2_DELETE = 2
AS_MSG_INFO2_GENERATION = 4
AS_MSG_INFO2_GENERATION_GT = 8
AS_MSG_INFO2_GENERATION_DUP = 16
AS_MSG_INFO2_WRITE_UNIQUE  = 32
AS_MSG_INFO2_WRITE_BINUNIQUE = 64

AS_MSG_INFO3_LAST = 1
AS_MSG_INFO3_TRACE = 2
AS_MSG_INFO3_TOMBSTONE = 4

# result_codes are as follows
# 0 success
# 1 not success

# AS_MSG_FIELD
# offset    name            meaning
# 0         sz (4 bytes)   number of bytes to follow
# 4         type (1 byte)   the type of the field
# 5         data (sz bytes) field-specific data

# types are:
# 0 namespace, a UTF-8 string
# 1 table, a UTF-8 string
# 2 key, one byte of type, then a type-specific set of bytes (see particle below)
# 3 bin, used for secondary access, one byte of namelength, the name, one byte of type, then the type-specific data

# AS_MSG_BIN
# offset    name           meaning
# 0         sz (4 bytes)      number of bytes to follow
# 4         op (1 byte)       operation to apply to bin
# 5         particle_type (1) type of following data
# 6         version (1)       can read multiple versions of the same record at once
# 7         name_len (1)      length of following utf8 encoded name
# 8         name (size = name_len)   utf8 encoded name
# 8+name_len data (size = sz - (3 + name_len))  particle specific data

# ops are:
# READ -    1
# WRITE -   2
# WRITE_UNIQUE - 3 write a globally (?) unique value
# WRITE_NOW -   4 write a timestamp of the current server value

# particle types are:
# INTEGER - 1    32-bit value
# BIGNUM - 2 either an arbitrary precision integer, or a string-coded float, unsure yet
# STRING - 3 UTF8 encoded
# ??
# BLOB - 5 your arbitrary binary data
#


#
# Result codes
#

CL_RESULTCODE_OK = 0
CL_RESULTCODE_FAIL = 1
CL_RESULTCODE_FAIL_NOTFOUND = 2
CL_RESULTCODE_FAIL_GENERATION = 3
CL_RESULTCODE_FAIL_PARAMETER = 4
CL_RESULTCODE_FAIL_KEY_EXISTS = 5
CL_RESULTCODE_FAIL_BIN_EXISTS = 6


#
# COMPATIBILITY COMPATIBILITY COMPATIBILITY
#
# So the 'struct' class went through lots of (good) improvements in 2.5, but we want to support
# old use as well as new. Write a few functions similar to the 2.5 ones, and either use builtin or
# pure based on what's available
#
#

ERROR_CODES = [1, 50, 51, 52, 53, 54, 55, 56, 60, 61, 62, 65, 70, 80, 81, -1]

def my_unpack_from(fmtStr, buf, offset  ):
    sz = struct.calcsize(fmtStr)
    return struct.unpack(fmtStr, buf[offset:offset+sz])

def my_pack_into(fmtStr, buf, offset, *args):
    tmp_array = struct.pack(fmtStr, *args)
    buf[offset:offset+len(tmp_array)] = tmp_array

# 2.5+ has this nice partition call
def partition_25(s, sep):
    return( s.partition(sep) )

# 2.4- doesn't
def partition_old(s, sep):
    idx = s.find(sep)
    if idx == -1:
        return(s, "", "")
    return( s[:idx], sep, s[idx+1:] )


g_proto_header = None
g_struct_header_in = None
g_struct_header_out = None
g_partition = None

# 2.5, this will succeed
try:
    g_proto_header = struct.Struct( '! Q' )
    g_struct_header_in = struct.Struct( '! Q B 4x B I 8x H H' )
    g_struct_header_out = struct.Struct( '! Q B B B B B B I I I H H' )
    g_struct_admin_header_in = struct.Struct( '! Q B B B B 12x' )
    g_struct_admin_header_out = struct.Struct( '! Q B B B B 12x' )
    g_partition = partition_25

# pre 2.5, if there's no Struct submember, so use my workaround pack/unpack
except:
    struct.unpack_from = my_unpack_from
    struct.pack_into = my_pack_into
    g_partition = partition_old

#
# Connection / Cluster pool
#
# Class which contains all the currently known information about
# the cluster. the set of hosts, the set of connections,
# status. Eventually, it'll have hints about what connections
# work with what digests
#

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
    """Citrusleaf socket: container class for a socket, which allows incrementing of timers and statuses easily"""
    def __init__(self, host_obj):
        self.s = None
        self.host_obj = host_obj

    def connect(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, msg:
            print " first exception - can't even create socket - don't dun host "
            return False
        try:
            self.host_obj.last_contact = time()
            self.s.settimeout( 0.7 )
            self.s.connect(self.host_obj.sockaddr[0])
        except socket.error, msg:
            print " connect exception "
            self.s.close()
            self.host_obj.markBad()
            print 'could not open socket, maybe its not up?'
            return False
        self.host_obj.markGood()
        return True

    def send(self, data ):
        try:
            r = self.s.sendall(data)
        except socket.error, msg:
            print " send exception ",msg
            return False
        if r != None:
            print " send returned error but not exception "
            return False
        return True

#   def send(self, data ):
#       try:
#           r = self.s.send(data)
#       except socket.error, msg:
#           print " send exception ",msg
#           return False
#       if r != len(data):
#           print " send wrong length wanted ",len(data)," got ",r
#           return False
#       return True

    # it's better to let this throw
    def recv(self, data ):
        return receivedata(self.s, data)

#   def recv(self, data ):
#       try:
#           pos = 0
#           while pos < data:
#               b = self.s.recv(data)
#               if pos == 0:
#                   r = b
#               else:
#                   r += b
#               pos += len(b)
#       except socket.error, msg:
#           print " recv exception ",msg
#           return False
#       return r

    # Close in case of a successful connection
    def close(self ):
        self.host_obj.markGood()
        if ( len( self.host_obj.idle_sockets ) < 128 ):
            self.s.settimeout( None )                   # make sure it doesn't expirei in q
            self.host_obj.idle_sockets.append( self )
        else:
            self.s.close()
            self.s = None
        return

    # return with error
    def close_err(self ):
        self.host_obj.markBad()
        self.s.close()
        self.s = None

def hashpassword(password):
    if hasbcrypt == False:
        print "Authentication failed: bcrypt not installed."
        sys.exit(1)

    if password == None:
        password = ""

    if len(password) != 60 or password.startswith("$2a$") == False:
        password = bcrypt.hashpw(password, "$2a$10$7EqJtq98hPqEX7fNZaFWoO")

    return password

def adminWriteHeader(sz, command, field_count):
    send_buf = create_string_buffer(sz);      # from ctypes
    # sz = (0 << 56) | (2 << 48) | (sz - 8)
    sz = (2 << 48) | (sz - 8)

    if g_struct_admin_header_out != None:
        g_struct_admin_header_out.pack_into(send_buf, 0, sz, 0, 0, command, field_count)
    else:
        struct.pack_into('! Q B B B B 12x', send_buf, 0, sz, 0, 0, command, field_count)

    return send_buf

def adminParseHeader(data):
    if g_struct_admin_header_in != None:
        rv = g_struct_admin_header_in.unpack(data)
    else:
        rv = struct.unpack('! Q B B B B 12x', data)

    return rv

def authenticate(sock, user, password):
    sz = len(user) + len(password) + 34  # 2 * 5 + 24
    send_buf = adminWriteHeader(sz, 0, 2)

    fmtStr = "! I B %ds I B %ds" % (len(user), len(password))
    struct.pack_into(fmtStr, send_buf, 24, len(user)+1, 0, user, len(password)+1, 3, password)

    try:
        sock.sendall(send_buf)
        recv_buff = receivedata(sock, 24)
        rv = adminParseHeader(recv_buff)
        return rv[2]
    except Exception, msg:
        print "Authentication exception: ", msg
        return -1;


class Host:
    """Citrusleaf Host: container class for all the little bits that make up a host"""

    def __init__(self, cluster):
        self.sockaddr = []  # list of sockaddrs where this node can be found
        self.last_contact = 0
        self.state = "unknown"
        self.idle_sockets = [ ]
        self.node = 0
        self.cluster = cluster    # think of it as a parent pointer

    def markBad(self):
        print "Marking bad: ",self.node," ",self.sockaddr[0]
        self.state = "bad"
        self.last_contact = time()
        if self not in self.cluster.hosts_bad :
            try:
                self.cluster.hosts_good.remove(self)
            except:
                pass
            try:
                self.cluster.hosts_unknown.remove(self)
            except:
                pass
            self.cluster.hosts_bad.append(self)

    def markGood(self):
#       print "Marking good: ",self.node," ",self.sockaddr[0]
        self.state = "good"
        self.last_contact = time()
        if self not in self.cluster.hosts_good :
            try:
                self.cluster.hosts_bad.remove(self)
            except:
                pass
            try:
                self.cluster.hosts_unknown.remove(self)
            except:
                pass
            self.cluster.hosts_good.append(self)


    # called to get a connection to this host,
    # either from the pool or by creating a new connection
    # through a connect call

    def getConnection(self):
        try:
            s = self.idle_sockets.pop(0)
            s.s.settimeout(0.4)
#           print "host ",self.sockaddr[0]," reusing connection"
            # test connection?
            return s
        except:
            pass
        s = Socket(self)
        if s.connect() == True:
            if self.cluster.user != None:
                rc = authenticate(s.s, self.cluster.user, self.cluster.password)

                if rc != 0:
                    print "Authentication failed for ", self.cluster.user, ": ", rc
                    s.close_err()
                    return None

            return s
        else:
            print "host ",self.sockaddr[0]," connection failed"
        return None

    def close(self):
        try:
            while True:
                s = self.idle_sockets.pop()
                s.close()
        except:
            pass
        self.idle_sockets = None


class CitrusleafCluster:
    """Citrusleaf Cluster contains state information about all hosts in a cluster, suitable for sending and receiving requests"""

    def __init__(self):
        # this host set contain lists objects: (host, port) that have been externally assocated with the cluster
        self.host_names = set()
        # Unique list of good hosts: list for random access
        self.hosts_good = [ ]
        # try to round-robbin the hosts for now
        self.last_good_host_index = 0
        # this list has hosts that are known-bad. Don't need random as much, but nice to keep consistant
        self.hosts_bad = [ ]
        # another list of hosts.
        self.hosts_unknown = [ ]
        # a name is sometimes suitable?
        self.cluster_name = None
        # User name in UTF-8 encoded bytes.
        self.user = None
        # Password in hashed format in bytes.
        self.password = None
        # If you want debug messages from the crawler, set this true
        self.crawler_debug = False
        self.crawler_disable = False
        thread.start_new_thread(CitrusleafCluster.crawler, (self,) )

    # Set user and password for servers that require authentication.
    def setUser(self, user, password):
        if user != None:
            self.user = user
            self.password = hashpassword(password)

    # adds a new host identifier to this cluster
    # The host identifier will be reduced to a set of actual Host objects, which
    # are individual interfaces (DNS may resolve to multiple hosts, or the cluster
    # may inform of more hosts on this cluster thought its own protocols)
    def addHost(self, host, port):

        # test for preexistance - debounce for multiple adds
        if (host,port) in self.host_names:
            print "add host: submitted host ",host,":",port," twice\n"
            return
        self.host_names.add( (host,port) )

        # reduce host-port into addresses, which instantiate Hosts, thus
        # added to the Hosts hashes

        for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            sa = res[4]
#           print "addHost: add host: sa ",sa

            try:
                node = citrusleaf_info(sa[0], sa[1], "node", self.user, self.password)
            except Exception, ex:
                print "exception ",ex," for host ",sa
                continue

            addme = True
            for h in self.hosts_good:
                if h.node == node:
                    addme = False
                    break
            if addme == True:
                for h in self.hosts_bad:
                    if h.node == node:
                        addme = False
                        break
            if addme == True:
                for h in self.hosts_unknown:
                    if h.node == node:
                        addme = False
                        break

            if addme == True:
                host_obj = Host(self)
                host_obj.af , host_obj.socktype, host_obj.proto, canonname, sa = res
                host_obj.node = node
                host_obj.sockaddr.append(sa)
                self.hosts_unknown.append( host_obj )


    # iterate through the bad list, move to the good list if a connection is formed
    def retestBad(self):
        for host in self.hosts_bad:
            r = citrusleaf_info(host.sockaddr[0][0], host.sockaddr[0][1], "version", self.user, self.password)
            host.last_contact = time()
            if (r == None or r == -1):
#               print "host ",host.node," still bad"
                continue
            # good now!
            self.hosts_bad.remove(host)
            self.hosts_good.append(host)

    # choose an active host from the pool, and get one of its connections
    # todo: pass in the key and you can get up your chances of talking to the
    # right host the first time
    def getConnection(self):
        c = None

        # try unknown hosts
        # print "cluster get connection: ",len(self.hosts_unknown)," unknown hosts"
        for host in self.hosts_unknown:
            c = host.getConnection()
            if c != None:
                return c

        # get connection from host
        while c == None and len(self.hosts_good) > 0:
            self.last_good_host_index = self.last_good_host_index % len(self.hosts_good)
            c = self.hosts_good[ self.last_good_host_index ].getConnection()
            self.last_good_host_index += 1

        if len(self.hosts_good) == 0:
            print "cluster says: no good hosts, really"

        return c

    #
    # This function is spawned as a thread. It keeps an eye on the cluster,
    # continually crawling, adding new nodes and removing old nodes. It uses
    # the internal 'info' calls.
    def crawler(self):

        while self.crawler_disable == False:

            if self.crawler_debug:
                print "Running crawler"

            # set of sockaddrs
            new_cluster_hosts = set()
            # list of newly dead hosts
            dead_cluster_hosts = set()

            # why not
            self.retestBad()

            # list of all good host objects in the system
            all_hosts = list(self.hosts_good)
            all_hosts.extend(self.hosts_unknown)

            for host in all_hosts:

                if self.crawler_debug:
                    print "crawler: pinging cluster member ",host.node," at ",host.sockaddr

                r = citrusleaf_info(host.sockaddr[0][0], host.sockaddr[0][1], "services", self.user, self.password)

                if self.crawler_debug:
                    print "crawler:   ping service response ",r

                if r == -1 or r in ERROR_CODES:
                    if self.crawler_debug:
                        print "crawler: request to ",host.sockaddr," returned error - mark sucky"
                    dead_cluster_hosts.add(host)
                    continue

                if r == None:
                    if self.crawler_debug:
                        print "crawler: request to ",host.sockaddr," returned no data"
                    continue

                services = r.split(";")
                for service in services:
                    if service != "":
                        # convert string to sockaddr
                        hp = service.split(":")
                        new_cluster_hosts.add( (hp[0], int(hp[1]) ) )

            # have a potentially host
            for new_sa in new_cluster_hosts:
                # scan through the list of known hosts
                in_all_host = False
                for all_host in all_hosts:
                    if new_sa in all_host.sockaddr:
                        in_all_host = True
                        break
                # new IP for sure, get the node info, see if this is a new IP for the same host
                if in_all_host == False:
                    node = citrusleaf_info(new_sa[0], new_sa[1], "node", self.user, self.password)
                    if node == None or node == -1:
                        print "could not get node from ",new_sa
                    else:
                        for all_host in all_hosts:
                            if all_host.node == node:
                                all_host.sockaddr.append(new_sa)
                                in_all_host = True
                                break

                        #it's a new one, insert
                        if in_all_host == False:
                            if self.crawler_debug:
                                print "crawler: new host: ",new_sa
                            new_host = Host(self)
                            new_host.node = node
                            new_host.sockaddr.append(new_sa)
                            self.hosts_unknown.append(new_host)


            # what about the list of dead hosts?
            for dead_host in dead_cluster_hosts:
                try:
                    self.hosts_good.remove(dead_host)
                    self.hosts_bad.append(dead_host)
                except:
                    if self.crawler_debug:
                        print "something went wrong when deleting ",hostStr
                        print "cluster hosts now ",self.hosts
                        print "cluster nodes now ",self.nodes
            if self.crawler_debug:
                print "--- clustercrawl: good: ",len(self.hosts_good)," bad ",len(self.hosts_bad)," unk ",len(self.hosts_unknown)
            sleep(2)

        print "Crawler thread terminated"

    def close(self):
        # this section must stop the crawler thread - need to get a signal back
        self.crawler_disable = True
        self.host_names = None
        for host in hosts_good:
            host.close()
        self.hosts_good = None
        for host in hosts_bad:
            host.close()
        self.hosts_bad = None

    def toString(self):
        if self.cluster_name != None:
            r = "cluster name: %s " % self.cluster_name
        else:
            r = ""
        r = r + ("%d hosts : " % len(self.host_names))
        for n in self.host_names:
            r = r + " %s:%s" % (n[0], n[1])
        return( r )


#
# This is a 'static' to find one of the clusters in the cluster definition list,
# or to create a new cluster object and insert it into those tables
#

g_clusters = { }

def cluster_setHost(cluster, host, port):
    global g_clusters
    cluster.addHost(host, port)
    g_clusters[(host,port)] = cluster

def cluster_setName(cluster, cluster_name):
    global g_clusters
    cluster.cluster_name = cluster_name
    g_clusters[cluster_name] = cluster

def getCluster_byhost( host, port ):
    global g_clusters
    if host == None or port == None :
        return None

    # look in the global cluster dict, see if anything like that is here
    cluster = g_clusters.get( (host, port ), None )
    if cluster != None:
        return cluster

    # make new cluster class object, insert into dict
    cluster = CitrusleafCluster()
    cluster_setHost(cluster, host, port)
    return cluster

def getCluster_byname( cluster_name ):
    global g_clusters
    cluster = g_clusters.get( cluster_name, None )
    if cluster != None:
        return cluster

    # make new cluster, insert into dict
    cluster = CitrusleafCluster()
    cluster_setName(cluster_name)
    return cluster


#
#
# Object and callback based python interface
#
#

# create inifinite FIFO queue
as_queue = Queue.Queue(0)

num_workers_lock = thread.allocate_lock()
num_workers = 0

def CitrusleafWorkerThread(ignore_me):
    global num_workers_lock, num_workers, as_queue
    # I'm a new worker and I'm OK (prefer the 'with' statement, but want to support Centos 5.3)
    num_workers_lock.acquire()
    num_workers = num_workers + 1
    num_workers_lock.release()

    # save a global lookup when you can
    my_as_queue = as_queue

    while True:
        try:
            as_op = my_as_queue.get(True, 5)            # block for at most 5 seconds
        except:
            # only reasonable exception is timedout
            # if I'm not the last thread, kill self since few in queue
            print "citrusleaf worker thread timed out on queue"
            num_workers_lock.acquire()
            if num_workers > 1:
                print "Citrusleaf: thread destroy"
                num_workers = num_workers - 1
                num_workers_lock.release()
                return
            num_workers_lock.release()
            continue

        try:
            if (as_op.debug):
                print "citrusleaf worker thread got message"
            as_op.act()
        except:         # exception in these cases: kill thread no matter what
            num_workers_lock.acquire()
            num_workers = num_workers - 1
            num_workers_lock.release()
            return


# call when you're finished, so we can gracefully cleanup all lingering TCP
# connections, threads, whatever.
# python's especially upset about threads.

def CitrusleafCleanup():
    global num_workers_lock, num_workers, as_queue
    # send integers, wait for death
    n_threads = 0
    num_workers_lock.acquire()
    n_threads = num_workers
    num_workers_lock.release()
    for i in xrange(n_threads):
        as_queue.put(0)         # putting an integer will throw an exception and shit will stop

    while num_workers > 0:
        sleep(0.1)


class CitrusleafOperation:

    def __init__ (self):
        self.cluster = None
        self.namespace = None
        self.set = ""
        self.key = None
        self.bin = None         # either a single value, or an iterated set:
                                # what to get
        self.values = None      # A dictionary that contains key-value bins to set or was just gotten
        self.generation = None
        self.expiration = 0
        self.delete = False
        self.result_code = 0

        self.callback = None # either set the callback or the queue!
        self.queue = None

        self.autoretry = True
        self.debug = False

    # external call to do the thing in question
    def submit(self):
        global as_queue

        # manage how many worker threads there are
        # current default: no more than 20 workers
        # add threads if the queue size is greater than 40
        start_thread = False;
        num_workers_lock.acquire()
        if num_workers == 0:
            start_thread = True
        elif num_workers < 20 and as_queue.qsize() > 40:
            start_thread = True
        num_workers_lock.release()

        if start_thread == True:
            if self.debug == True:
                print "Citrusleaf: creating new thread"
            thread.start_new_thread(CitrusleafWorkerThread, (True,) ) # long way to go to pass no parameters

        if self.debug == True:
            print "received submit, enqueueing"
        as_queue.put(self)

    # called from worker thread context: do the work
    def act(self):

        # validate some input
        if (self.cluster == None):
            print "operation has no cluster assigned, can't act"
            self.result_code = -1
            self.callback()
            return
        if (self.namespace == None):
            print "operation has no namespace, can't act"
            self.result_code = -1
            self.callback()
            return
        if (self.key == None):
            print "operation has no key, can't act"
            self.result_code = -1
            self.callback()
            return

        # Do the action we came here to do
        if (self.delete != False):
            if (self.debug):
                if (self.bins):
                    print "citrusleaf: bins set on delete command, ignoring"
                if (self.values):
                    print "citrusleaf: values set on delete command, ignoring"
            self.result_code = delete(self.cluster, self.namespace, self.set, self.key, self.autoretry, self.debug)

        elif (self.values != None):
            if self.debug == True:
                print "PUT request for namespace ",self.namespace," set ",self.set," key ",self.key," values ",self.values
            self.result_code = put( self.cluster, self.namespace, self.set, self.key, self.values, self.expiration, self.generation , self.autoretry, self.debug )

        else:
            if self.debug == True:
                print "GET request for namespace ",self.namespace," set ",self.set," key ",self.key," bin ",self.bin
            self.result_code, self.generation, self.values = get( self.cluster, self.namespace, self.set, self.key, self.bin, self.autoretry, self.debug )

        # now callback or queue the response
        if self.callback != None:
            if self.debug:
                print "calling callback "
            self.callback(self)
        else:
            if self.debug:
                print "inserting reply on queue"
            self.queue.put(self)
        return

#
# Make an info request of the buffer
#


def citrusleaf_info_request(host, port, buf, user=None, password=None, debug=False, use_this_sock=None):

    # request over TCP
    try:

        if use_this_sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect((host, int(port) ))
            if user != None:
                rc = authenticate(sock, user, password)

                if rc != 0:
                    print "Authentication failed for ", user, ": ", rc
                    sock.close()
                    return rc
        else:
            sock = use_this_sock

        """if user != None:
            rc = authenticate(sock, user, password)

            if rc != 0:
                print "Authentication failed for ", user, ": ", rc
                sock.close()
                return rc
        """

        sock.send(buf)

        if debug:
            print "info get response"
        # get response
        rsp_hdr = sock.recv(8)
        if debug:
            print "response is: "
            myHexlify(rsp_hdr)
        q = struct.unpack_from("! Q",rsp_hdr, 0)
        sz = q[0] & 0xFFFFFFFFFFFF
        if debug:
            print "recv header length ",sz
        if sz > 0:
            rsp_data = receivedata(sock, sz)
            if debug:
                print "recv body "
                myHexlify(rsp_data)
        if use_this_sock is None:
            sock.close()
    except Exception , ex:
#       print "info request got exception ",type(ex)," ",ex
        return -1

    # parse out responses
    if sz == 0:
        return None

    if debug:
        print "receive as string: ",rsp_data

    return( rsp_data )



#
# Citrusleaf Info Command
#
# This is a special purpose request to do things to the citrusleaf cluster
# for a given node.
#
# pass in the command - which is a command string, and a dict
# of name-value pairs.
#
# Wire format is cmd:name=value;name=value....
#
# Returns: values, a dict of with the name being the index, and the value being the value


def citrusleaf_info_command( host, port, cmd, user=None, password=None, parameters=None, debug=False, sock=None ):

    # Passed a set of names: created output buffer
    param_l = []
    param_l.append(cmd)
    param_l.append(":")
    if parameters != None:
        for name, value in parameters.iteritems():
            param_l.append(name)
            param_l.append("=")
            param_l.append(value)
            param_l.append(";")
        del param_l[len(param_l)-1]
    param_l.append("\n")
    paramstr = "".join(param_l)
    # sometimes this string is unicode, if the parameters input were unicode not string
    # force to string just to be sure - this may be required elsewhere -
    # different versions of python are different about how they type stuff like this
    paramstr = str(paramstr)

    q = (2 << 56) | (1 << 48) | (len(paramstr))
    fmtStr = "! Q %ds" % len(paramstr)
    buf = struct.pack(fmtStr, q, paramstr )

    if debug:
        print "info cmd request buffer: "
        myHexlify(buf)

    rsp_data = citrusleaf_info_request(host, port, buf, user, password, debug, use_this_sock=sock)

    if debug:
        print "citrusleaf info: response ",rsp_data
    return rsp_data

#
# Citrusleaf Info request
#
# This is a special purpose request to get informational name-value pairs
# from a given node. It's good for discovering the rest of the cluster,
# or trying to figure out which cluster members have which parts of the key space
#
# host, port are self explanatory
# 'names' is an iterable list of values to get, or None to get all
#  being really nice, also supporting a single string as a name instead of requiring a list
#
# Returns: values, a dict of with the name being the index, and the value being the value


def citrusleaf_info( host, port, names=None, user=None, password=None, debug=False, sock=None ):

    # Passed a set of names: created output buffer
    if names == None:
        q = (2 << 56) | (1 << 48)
        if g_proto_header != None:
            buf = g_proto_header.pack(q)
        else:
            buf = struct.pack('! Q',q)

    elif type(names) == types.StringType:
        q = (2 << 56) | (1 << 48) | (len(names) + 1)
        fmtStr = "! Q %ds B" % len(names)
        buf = struct.pack(fmtStr, q, names, 10 )

    else: # better be iterable of strings
        # annoyingly, join won't post-pend a seperator. So make a new list
        # with all the seps in
        names_l = []
        for name in names:
            names_l.append(name)
            names_l.append("\n")
        namestr = "".join(names_l)
        q = (2 << 56) | (1 << 48) | (len(namestr))
        fmtStr = "! Q %ds" % len(namestr)
        buf = struct.pack(fmtStr, q, namestr )


    if debug:
        print "request buffer: "
        myHexlify(buf)

    rsp_data = citrusleaf_info_request( host, port, buf, user, password, debug, use_this_sock=sock)

    if type(rsp_data) == int or rsp_data is None:
        return rsp_data

    # if the original request was a single string, return a single string
    if type(names) == types.StringType:

        lines = rsp_data.split("\n")
        name, sep, value = g_partition(lines[0],"\t")

        if name != names:
            print " problem: requested name ",names," got name ",name, " ", user, " ", password
            return(-1)
        return value

    else:
        rdict = dict()
        for line in rsp_data.split("\n"):
            if len(line) < 1:       # this accounts for the trailing '\n' - cheaper than chomp
                continue
            if debug:
                print " found line ",line
            name, sep, value = g_partition(line,"\t")
            if debug:
                print "    name: ",name," value: ",value
            rdict[name] = value

        return rdict


# there is probably a cooler way to do this using some kind of reduce
# function. One where the lambda would return ord(c) or ord(c) + '\n'
#

def myHexlify(buf):
    print "my hexlify: length ",len(buf)
    for i, c in enumerate(buf):
        print "%02x " % ord(c) ,
        if i % 16 == 15:
            print ""
        if i % 16 == 7:
            print ": ",
    print

# host and port are strings, data is the prebuilt buffer
#
# returns: result_code, generation, dictionary of responses
#
# dictionary is:
#   bin name => value

def citrusleafTransaction ( cluster , data, autoretry = True, debug = False ):

# default return
    result_code = -1
    generation = None
    op_dict = None

    while autoretry == True:
        s = cluster.getConnection()
        if s == None:
            print " failing request because no good hosts"
            return result_code, generation, op_dict

#       print " making transaction to ",s.host_obj.sockaddr[0]
        op_dict = None

        try:
            s.send( data )
            header_data = s.recv(30)    # fetch header
            proto_type,result_code,generation,n_fields,n_ops,sz = parse_header(header_data, debug)
            if (sz):
#               print "reading remainder of data ",sz," bytes"
                body_data = s.recv( sz )
                op_dict = parse_body( n_fields, n_ops, body_data, debug )
        except Exception, msg:
            print "Transaction did not complete for some reason: ",msg
            s.close_err()
            continue

# successful request out here
        s.close()
        return result_code, generation, op_dict

# precompile is better: will be used lots
# Q is version + type + length
# B header size (22)
# B info , B info2, B info3, B unused (so uninteresting on read, bring them into one value)
# B result code (0 is OK)
# I generation
# I record_ttl
# I transaction_ttl
# H n_fields
# H n_ops
#
# struct.Struct is a great optimization, but is >= 2.5, so code
# both ways, sorry for the ugly


#
# returns
# ( type, result_code, generation, n_fields, n_ops, sz )
# sz is remainder of the message (not the size in the header)
# record_ttl is not interesting thus not returned
# transaction_ttl is not interesting thus not returned
# same with the info fields

def parse_header( buf, debug = False ):

    if (debug == True):
        print "parse header: received header: "
        myHexlify(buf)

    if g_struct_header_in != None:
        rv = g_struct_header_in.unpack(buf)
    else:
        rv = struct.unpack('! Q B 4x B I 8x H H', buf)

    version = (rv[0] >> 56) & 0xff
    proto_type = (rv[0] >> 48) & 0xff
    sz = (rv[0] & 0xFFFFFFFFFFFF)

    if (version != 2):
        print "protocol version mismatch! expecting 2 got ",version
    if (rv[1] != 22):
        print "protocol header parse: unexpected header size",rv[1]

    return (proto_type, rv[2], rv[3], rv[4], rv[5], sz-22)

# input: the number of fields and the number of ops and the buffer itself
#   (todo: parse fields, currently nothing returns fields)
# return:
def parse_body( n_fields, n_ops, buf, debug = False ):

    if (n_fields != 0):
        print "todo: parse body with nfields, error"
        return None

    # short circut
    if (n_ops == 0):
        if (len(buf) > 0):
            print "parse body: curious, told no ops but there's data here"
        return None

    # loud debugging
    if debug:
        print "read body: "
        myHexlify(buf)

    # print "parse body: buf size ",len(buf)," nops to parse: ",n_ops

    bin_dict = { }
    offset = 0;
    for i in xrange(n_ops):
        # FAIL: struct's p format is not working, seems to me
        # sz, op, p_type, bin_name = g_struct_bin.unpack_from(buf,offset)
        sz, op, p_type, vers, bin_sz = struct.unpack_from("! I B B B B", buf, offset)
        offset = offset + 8
        fmtStr = "%ds" % bin_sz
        bin_name = struct.unpack_from(fmtStr, buf, offset)
        bin_name = bin_name[0]
        offset = offset + bin_sz

        # print "parse body: op receive: sz ",sz," op ",op," ptype ",p_type, "version ",vers," bin name ",bin_name

        p_size = sz - (4 + len(bin_name))

        # deal with the bin's binary data - convert to a value and jam into the dict

        # TODO! take the different versions and put them in different buckets

        # None!
        if (p_type == 0):
            bin_dict[bin_name] = None

        # integer!
        elif (p_type == 1):
            val_int = struct.unpack_from("! Q",buf,offset)
            bin_dict[bin_name] = val_int[0]
            offset = offset + 8

        # strings and blobs are the same in python
        elif (p_type == 3 or p_type == 4):
#           print "bin read: string psize ",p_size
            up_str = "%ds" % p_size
            val_str = struct.unpack_from(up_str,buf,offset)
#           print "found string: bin ",bin_name," value ",val_str
            bin_dict[bin_name] = val_str[0]
            offset += p_size

    return bin_dict


# put is more and more complicated!
# return a result code only, whether the put suceeded or not
#
# record_ttl is the time from now, in seconds, when the database will auto-remove the record
# transaction_ttl is the lifetime of the transaction, in milliseconds (currently not implemented)
# the generation count is the current generation of the record, used for locking read-modify-write
# auto-retry allows
#
# stringsAsBlobs is a special argument that treats all incoming strings as 'blob' types to the server
#

#if you want to insert through digest then set key as the digest value and digest parameter as True
def put( cluster, namespace, sett, key, values, record_ttl = None, transaction_ttl = None, generation = None, autoretry = True, debug=False, stringsAsBlobs=False):
    # for fastest action, create the entire buffer size up front

    # print "put: ns:",namespace," set:",sett," key:",key

    sz = 30; # header
    if type(key)==types.StringType:
        lenkey = len(key)
        sz += (3 * 5) + len(namespace) + len(sett) + lenkey + 1   # fields
    elif type(key)==types.IntType:
        lenkey = 8 # integer is of fixed 8 bytes
        sz += (3 * 5) + len(namespace) + len(sett) + lenkey + 1   # fields
    elif type(key)==types.ListType:
        lenkey = 20 # digest is of fixed 20 bytes
        sz += (3 * 5) + len(namespace) + len(sett) + lenkey   # fields

    # the size of the ops portion is harder - and calculate the number of ops while you're here
    try:
        for bin,value in values.iteritems():

            if (type(bin) != types.StringType):
                print "Citrusleaf: bin names must be string, instead is ",type(bin)
                return -1

            if type(value) == types.StringType:
                sz += 8 + len(bin) + len(value)
            elif type(value) == types.IntType:
                sz += 8 + len(bin) + 8
            elif value == None:
                sz += 8 + len(bin)
            else:
                print "Citrusleaf: found bin of unknown type ",type(value)
                return -1,0,None
    except:
        print "Value of type ",type(values)," is not a dict. Use a dict with strings as the keys, and value as the value"
        return -1

    n_bins = len(values)

    buf = create_string_buffer(sz)      # from ctypes - important to going fast!
    offset = 0

    # NB - the efficient way to do this is One Fell Swoop, which means you don't
    # need to create the 'struct' object, or the string buffer directly - let struct do it
    # but let's fact it, I need a little practice here
    #
    # 3 is nfields, 1 is n_ops

    info1 = 0
    info2 = AS_MSG_INFO2_WRITE
    info3 = 0

    if record_ttl == None:
        record_ttl = 0

    if transaction_ttl == None:
        transaction_ttl = 0

    if generation == None:
        generation = 0
    else:
        info2 = info2 | AS_MSG_INFO2_CAS

    if stringsAsBlobs == None:
        stringsAsBlobs = False

    # pack up that first quadword
    sz = (2 << 56) | (3 << 48) | (sz - 8)

    if g_struct_header_out != None:
        g_struct_header_out.pack_into(buf, offset, sz, 22, info1, info2, info3, 0, 0, generation, record_ttl, transaction_ttl, 3 , n_bins )
        offset += g_struct_header_out.size
    else:
        h_buf = struct.pack_into( '! Q B B B B B B I I I H H', buf, offset, sz, 22, info1, info2, info3, 0, 0, generation, record_ttl, transaction_ttl, 3 , n_bins  )
        offset += 30

    # now the fields. There's always three (until there are more ....)
    if type(key) == types.StringType:
        fmtStr = "! I B %ds I B %ds I B B %ds" % (len(namespace), len(sett), lenkey)
        struct.pack_into(fmtStr, buf, offset, len(namespace)+1, 0, namespace, len(sett)+1, 1, sett, lenkey+2, 2, 3, key)
        offset += (3 * 5) + len(namespace) + len(sett) + lenkey + 1
    elif type(key) == types.IntType:
        fmtStr = "! I B %ds I B %ds I B B Q" % (len(namespace), len(sett))
        struct.pack_into(fmtStr, buf, offset, len(namespace)+1, 0, namespace, len(sett)+1, 1, sett, lenkey+2, 2, 1, key)
        offset += (3 * 5) + len(namespace) + len(sett) + lenkey + 1
    elif type(key) == types.ListType:
        fmtStr = "! I B %ds I B %ds I B 20B" % (len(namespace), len(sett))
        struct.pack_into(fmtStr, buf, offset, len(namespace)+1, 0, namespace, len(sett)+1, 1, sett, lenkey+1, 4, key[0], key[1], key[2], key[3], key[4], key[5], key[6], key[7], key[8], key[9], key[10], key[11], key[12], key[13], key[14], key[15], key[16], key[17], key[18], key[19])
        offset += (3 * 5) + len(namespace) + len(sett) + lenkey

    # now one bin - just hard code op 2 (write), particle type 3 (string)
    # note: perhaps the p-string thing isn't working as expected!?!?
    # that would be cooler than this
    for bin, value in values.iteritems():

        if (type(value) == types.StringType):
            bin_sz = 4 + len(bin) + len(value)
            fmtStr = "! I B B B B %ds %ds" % (len(bin), len(value))
            # type 4 is blob - represent strings as blobs
            if (stringsAsBlobs==True):
                struct.pack_into(fmtStr, buf, offset, bin_sz, 2, 4, 0, len(bin), bin, value)
            else:
                struct.pack_into(fmtStr, buf, offset, bin_sz, 2, 3, 0, len(bin), bin, value)
        elif (type(value) == types.IntType):
            bin_sz = 4 + len(bin) + 8
            fmtStr = "! I B B B B %ds Q" % len(bin)
            struct.pack_into(fmtStr, buf, offset, bin_sz, 2, 1, 0, len(bin), bin, value)
        elif (value == None):
            bin_sz = 4 + bin(len)
            fmtStr = "! I B B B B %s" % len(bin)
            struct.pack_into(fmtStr, buf, offset, bin_sz, 2, 0, 0, len(bin), bin)

        offset += bin_sz + 4

    # loud debugging
    if debug:
        print "transmit put buffer: "
        myHexlify(buf)

    result_code, generation, bins = citrusleafTransaction(cluster, buf, autoretry, debug)

    return result_code


#
# Pass bin as None (or ignore the parameter) to select all
# Or pass in a list or tuple to get those bins
# or pass in a string to get just that bin
#
# The response is (result_code, generation, bins)

def get( cluster, namespace, sset, key, bin = None, autoretry = True, debug=False ):

    # figure out the size of the whole output message
    sz = 30; # header
    if type(key)==types.StringType:
        lenkey = len(key)
        sz += (3 * 5) + len(namespace) + len(sset) + lenkey + 1   # fields
    elif type(key)==types.IntType:
        lenkey = 8 # integer is of fixed 8 bytes
        sz += (3 * 5) + len(namespace) + len(sset) + lenkey + 1   # fields
    elif type(key)==types.ListType:
        lenkey = 20 # digest is of fixed 20 bytes
        sz += (3 * 5) + len(namespace) + len(sset) + lenkey   # fields

    # the size of the ops portion is harder - and calculate the number of ops while you're here
    if (type(bin) == types.StringType):
        sz += 8 + len(bin)
        n_bins = 1
    elif (getattr(bin,'__iter__',False) != False):
        for b in bin:
            if type(b) == types.StringType:
                sz += 8 + len(b)
            else:
                print "Citrusleaf: found bin of unknown type ",type(b)
                return -1,0,None
        n_bins = len(bin)
    elif (type(bin) == types.NoneType):
        n_bins = 0
    else:
        print "Citrusleaf: bin type unknown ",type(bin)
        return -1,0,None

    if debug:
        print "transmitting get request for ",n_bins," bins"

    buf = create_string_buffer(sz);     # from ctypes
    offset = 0

    # this is a read op
    info1 = AS_MSG_INFO1_READ
    if (bin == None):
        info1 = info1 | AS_MSG_INFO1_GET_ALL
    info2 = 0
    info3 = 0

    sz = (2 << 56) | (3 << 48) | (sz - 8)

    if g_struct_header_out != None:
        g_struct_header_out.pack_into(buf, offset, sz, 22, info1, info2, info3, 0, 0, 0, 0, 0, 3 , n_bins )
        offset += g_struct_header_out.size
    else:
        h_buf = struct.pack_into( '! Q B B B B B B I I I H H', buf, offset, sz, 22, info1, info2, info3, 0, 0, 0, 0, 0, 3 , n_bins  )
        offset += 30

    # now the fields, which will locate the record. There's always three
    if type(key) == types.StringType:
        fmtStr = "! I B %ds I B %ds I B B %ds" % (len(namespace), len(sset), lenkey)
        struct.pack_into(fmtStr, buf, offset, len(namespace)+1, 0, namespace, len(sset)+1, 1, sset, lenkey+2, 2, 3, key)
        offset += (3 * 5) + len(namespace) + len(sset) + lenkey + 1
    elif type(key) == types.IntType:
        fmtStr = "! I B %ds I B %ds I B B Q" % (len(namespace), len(sset))
        struct.pack_into(fmtStr, buf, offset, len(namespace)+1, 0, namespace, len(sset)+1, 1, sset, lenkey+2, 2, 1, key)
        offset += (3 * 5) + len(namespace) + len(sset) + lenkey + 1
    elif type(key) == types.ListType:
        fmtStr = "! I B %ds I B %ds I B 20B" % (len(namespace), len(sset))
        struct.pack_into(fmtStr, buf, offset, len(namespace)+1, 0, namespace, len(sset)+1, 1, sset, lenkey+1, 4, key[0], key[1], key[2], key[3], key[4], key[5], key[6], key[7], key[8], key[9], key[10], key[11], key[12], key[13], key[14], key[15], key[16], key[17], key[18], key[19])
        offset += (3 * 5) + len(namespace) + len(sset) + lenkey

    if (type(bin) == types.StringType):
        # now one bin - just hard code op 1 (read), null particle type (get), bin name
        bin_sz = 4 + len(bin)
        fmtStr = "! I B B B B %ds" % len(bin)
        struct.pack_into(fmtStr, buf, offset, bin_sz, 1 , 0, 0, len(bin), bin)
        offset = offset + bin_sz

    # if it's an iterable, use each contained as a bin
    elif (getattr(bin,'__iter__',False) != False):
        for b in bin:
            if (type(b) == types.StringType):
                # now one bin - just hard code op 1 (read), particle type 3 (string)
                bin_sz = 4 + len(b)
                fmtStr = "! I B B B B %ds" % len(b)
                struct.pack_into(fmtStr, buf, offset, bin_sz, 1 , 0, 0, len(b), b)
                offset = offset + bin_size
    elif (type(bin) == types.NoneType):
        pass
    else:
        print "Citrusleaf could not format output request: bin type ",bin," is unknown"
        return -1, 0, None

    # loud debugging
    if debug:
        print "transmit get buffer: "
        myHexlify(buf)

#   if (code == 0):
#       print "transaction returned success"
#   else:
#       print "trasaction returned failure ",code

    return citrusleafTransaction(cluster, buf, autoretry, debug)


def delete(cluster, namespace, sset, key, generation=None, transaction_ttl=None, autoretry=True, debug=False ):

# figure out the size of the whole output message
    sz = 30; # header
    if type(key)==types.StringType:
        lenkey = len(key)
        sz += (3 * 5) + len(namespace) + len(sset) + lenkey + 1   # fields
    elif type(key)==types.IntType:
        lenkey = 8 # integer is of fixed 8 bytes
        sz += (3 * 5) + len(namespace) + len(sset) + lenkey + 1   # fields
    elif type(key)==types.ListType:
        lenkey = 20 # digest is of fixed 20 bytes
        sz += (3 * 5) + len(namespace) + len(sset) + lenkey   # fields

    buf = create_string_buffer(sz);     # from ctypes
    offset = 0

    # NB - the efficient way to do this is One Fell Swoop, which means you don't
    # need to create the 'struct' object, or the string buffer directly - let struct do it
    # but let's fact it, I need a little practice here
    #
    # 3 is nfields, 1 is n_ops
    info1 = 0
    info2 = AS_MSG_INFO2_WRITE | AS_MSG_INFO2_DELETE
    if generation != None:
        info2 = info2 | AS_MSG_INFO2_CAS
    else:
        generation = 0
    info3 = 0

    sz = (2 << 56) | (3 << 48) | (sz - 8)

    if transaction_ttl == None:
        transaction_ttl = 0

    if g_struct_header_out != None:
        g_struct_header_out.pack_into(buf, offset, sz, 22, info1, info2, info3, 0, 0, generation, 0, transaction_ttl, 3 , 0 )
        offset += g_struct_header_out.size
    else:
        h_buf = struct.pack_into( '! Q B B B B B B I I I H H', buf, offset, sz, 22, info1, info2, info3, 0, 0, generation, 0, transaction_ttl, 3 , 0  )
        offset += 30

    # now the fields, which will locate the record. There's always three
    if type(key) == types.StringType:
        fmtStr = "! I B %ds I B %ds I B B %ds" % (len(namespace), len(sset), lenkey)
        struct.pack_into(fmtStr, buf, offset, len(namespace)+1, 0, namespace, len(sset)+1, 1, sset, lenkey+2, 2, 3, key)
        offset += (3 * 5) + len(namespace) + len(sset) + lenkey + 1
    elif type(key) == types.IntType:
        fmtStr = "! I B %ds I B %ds I B B Q" % (len(namespace), len(sset))
        struct.pack_into(fmtStr, buf, offset, len(namespace)+1, 0, namespace, len(sset)+1, 1, sset, lenkey+2, 2, 1, key)
        offset += (3 * 5) + len(namespace) + len(sset) + lenkey + 1
    elif type(key) == types.ListType:
        fmtStr = "! I B %ds I B %ds I B 20B" % (len(namespace), len(sset))
        struct.pack_into(fmtStr, buf, offset, len(namespace)+1, 0, namespace, len(sset)+1, 1, sset, lenkey+1, 4, key[0], key[1], key[2], key[3], key[4], key[5], key[6], key[7], key[8], key[9], key[10], key[11], key[12], key[13], key[14], key[15], key[16], key[17], key[18], key[19])
        offset += (3 * 5) + len(namespace) + len(sset) + lenkey

    result_code, generation, bins = citrusleafTransaction(cluster, buf, autoretry, debug)
    return result_code

class UserRole(object):
    name = None
    roles = None

def parseRoles(data, offset, user):
    sz = struct.unpack_from("! B", data, offset)
    sz = sz[0]
    offset += 1
    i = 0

    while i < sz:
        role_len = struct.unpack_from("! B", data, offset)
        role_len = role_len[0]
        offset += 1
        fmtStr = "%ds" % role_len
        role = struct.unpack_from(fmtStr, data, offset)
        role = role[0]
        user.roles.append(role)
        offset += role_len
        i += 1

    return offset

def parseUsers(data, sz, users):
    offset = 0

    while offset < sz:
        code, field_count = struct.unpack_from('! x B x B 12x', data, offset)

        if code != 0:
            if code == 50:  # query end
                return -1
            return code

        user = UserRole()
        user.name = None
        user.roles = []

        offset += 16
        i = 0

        while i < field_count:
            field_len, field_id = struct.unpack_from("! I B", data, offset)
            field_len -= 1
            offset += 5

            if field_id == 0:  # user
                fmtStr = "%ds" % field_len
                user.name = struct.unpack_from(fmtStr, data, offset)
                user.name = user.name[0]
                offset += field_len
            elif field_id == 10: # roles
                offset = parseRoles(data, offset, user)
            else:
                offset += field_len

            i += 1

        users.append(user)

    return 0

def readUserBlocks(sock):
    users = []
    status = 0

    while status == 0:
        header_data = sock.recv(8)

        if g_proto_header != None:
            rv = g_proto_header.unpack(header_data)
        else:
            rv = struct.unpack('! Q', header_data)

        sz = (rv[0] & 0xFFFFFFFFFFFF)

        if sz > 0:
            body_data = sock.recv(sz)
            status = parseUsers(body_data, sz, users)
        else:
            break

    return status, users

def readUsers(cluster, send_buf):
    sock = cluster.getConnection()
    if sock == None:
        print "Failed to connect"
        return -1, None

    try:
        sock.send(send_buf)
        status, users = readUserBlocks(sock)
        sock.close()

        if status < 0:
            status = 0

        return status, users
    except Exception, msg:
        print "Query users exception: ", msg
        sock.close_err()
        return -1, None

def queryUser(cluster, user):
    sz = len(user) + 29  # 1 * 5 + 24
    send_buf = adminWriteHeader(sz, 9, 1)

    fmtStr = "! I B %ds" % (len(user))
    struct.pack_into(fmtStr, send_buf, 24, len(user)+1, 0, user)

    status, users = readUsers(cluster, send_buf)

    if status == 0:
        return status, users[0]

    return status, None

def queryUsers(cluster):
    sz = 24
    send_buf = adminWriteHeader(sz, 9, 0)
    return readUsers(cluster, send_buf)

def __readStatus(sock):

    """
        This function is responsible for reading status code from response
        message block.
        Message format is as followed,
        Scheme        - 1 byte   - authentication scheme
       [Resultcode    - 1 byte   - result codes]
        Command       - 1 byte   - Command ID
        FieldCount    - 1 byte   - number ID/value pairs
        Unused        - 12 bytes - reseved for padding
        Fields        - N/A      - ID/value pairs

        @params:
            sock : Socket instance which is given by cluster.getConnection()

        @return_values:
            status_code [Int]
            Status will be one of the following,
                OK                                               - 0
                Unknown Server Error                             - 1
                Last 'proto' in a Chunked Sequence               - 50
                Security Not Supported                           - 51
                Security Not Enabled                             - 52
                Security Scheme Not Supported                    - 53
                Unrecognized Command ID                          - 54
                Unrecognized Field ID                            - 55
                Illegal State (e.g. valid but unexpected command)- 56
                No User or Unrecognized User                     - 60
                User Already Exists                              - 61
                No Password or Bad Password                      - 62
                Expired Password                                 - 63
                Forbidden Password                               - 64
                No Credential or Bad Credential                  - 65
                No Role(s) or Unrecognized Role(s)               - 70
                No Privileges or Unrecognized Privileges         - 71
                Not Authenticated                                - 80
                Role/Privilege Violation                         - 81

    """

    # reading header of the message
    header_data = sock.recv(8)

    if g_proto_header != None:
        rv = g_proto_header.unpack(header_data)
    else:
        rv = struct.unpack('! Q', header_data)

    # get the actual size of the message
    sz = (rv[0] & 0xFFFFFFFFFFFF)

    status_code = -1

    if sz > 0:
        data = sock.recv(sz)
        # get status code from read message
        # please check doc string for the location of status code
        status_code = struct.unpack_from('! x B 14x', data, 0)

        status_code = status_code[0] if type(status_code) == tuple else status_code

    return status_code

def _sendMessage(cluster, buf):

    """
        This function is responsible for sending a message
        to aerospike DB over a socket and get the result
        in form of status back.

        @params:
            cluster   - CitrusleafCluster instance
            buf       - message buffer to be sent across

        @return_values:
            status    - Integer status value
            -1        - In case of any unknown exception
    """
    # get socket instance to be used for communication
    sock = cluster.getConnection()
    if sock == None:
        print "Failed to connect"
        return -1

    try:
        # send message across
        sock.send(buf)

        # get status of the request
        status = __readStatus(sock)
        sock.close()

        if status < 0:
            status = 0

        return status
    except Exception, msg:
        print msg
        sock.close_err()
        return -1

def dropUser(cluster, user):

    """
        This function will drop a particular `user` from a given `cluster`.

        @params:
            cluster     - CitruleafCluster instance
            user        - <String> username present on a DB

        @return_values:
            status      - an integer status code
    """

    # field_count * 5 + 24
    # UNKNOWNS :: What 5 & 24 mean???
    sz = len(user) + 29 # 1 * 5 + 24
    # Header size in bytes

    # write message header in a buffer
    send_buf = adminWriteHeader(sz, 2, 1)

    fmtStr = "! I B %ds" % (len(user))
    struct.pack_into(fmtStr, send_buf, 24, len(user)+1, 0, user)

    # Actually drops the user
    status = _sendMessage(cluster, send_buf)

    return status

def _packRoles(buf, offset, roles):

    """
        This function is responsible for packing roles list in
        message buffer.

        @params:
            buf     - message buffer to be sent across
            offset  - offset from where roles' list will be packed
            roles   - roles' list

        @return_values:
            None

        This function will update message buffer, which will be used later.
    """
    roles_string = ''.join( [ role for role in roles ] )

    """
    field_length = 1 byte for field_type +
                   1 byte for role_count +
                   for role in roles:
                       1 byte for len(role) +
                       len(role) bytes for role
    """
    struct.pack_into("! I B B", buf, offset,
                    len(roles_string)+2+len(roles), 10, len(roles))

    """
    4 bytes --> field length
    1 byte  --> field type
    1 byte  --> role count
    -------
    6 bytes
    """
    offset += 6

    for role in roles:
        fmtStr = "B %ds" % ( len(role) )
        struct.pack_into(fmtStr, buf, offset,
                        len(role), role)
        offset += len(role) + 1

def createUser(cluster, user, password, roles=["read"]):

    """
        This function is responsible for creating a user with
        given username, password and roles.
        It will not allow you to create a user w/o any roles.

        @params:
            cluster        - CitrusleafCluster instance
            user           - <String> username
            password       - <String> password to be set
            roles          - <list> a list of roles to assgined to a user, default -> ["read"]

        @return_values:
            status         - an integer status code
    """

    if not roles:
        # user can't be created w/o any roles
        print "Roles list is empty or None."
        return -1

    roles_string = ''.join( [ role for role in roles ] )

    # total size of the message
    """
    USER FIELD :
        Length  - 4 bytes
        Type    - 1 byte
        Value   - len(user) bytes
    PASSWORD FIELD :
        Length  - 4 bytes
        Type    - 1 byte
        Value   - len(user) bytes
    ROLES FIELD :
        Field Length     - 4 bytes
        Field Type       - 1 byte
        Role Count       - 1 byte
        Role[i].Len      - 1 byte
        Role[i].Value    - len(Value) bytes
    """
    sz = len(user) + len(password) + len(roles_string) + len(roles) + 5 + 5 + 6 + 24

    # write message header, 3 is field's count
    send_buf = adminWriteHeader(sz, 1, 3)

    # pack username and password first
    fmtStr = "! I B %ds I B %ds" % ( len(user), len(password) )

    struct.pack_into(fmtStr, send_buf, 24,
                     len(user)+1, 0, user,
                     len(password)+1, 1, password)

    # update the offset to pack roles
    offset = 24 + 10 + len(user) + len(password)

    # pack roles in send buffer
    _packRoles(send_buf, offset, roles)

    # send the message and get response
    status = _sendMessage(cluster, send_buf)

    return status

def setPassword(cluster, user, password):

    """
        This function is responsible for setting password
        for a given user.

        @params:
            cluster        - CitrusleafCluster instance
            user           - <String> username
            password       - <String> password to be set

        @return_values:
            status         - an integer status code
    """

    # get total size of the message buffer
    sz = len(user) + len(password) + 2 * 5 + 24

    # write header in message buffer
    send_buf = adminWriteHeader(sz, 3, 2)

    fmtStr = "! I B %ds I B %ds" % ( len(user), len(password) )

    # pack user and password details in message buffer
    struct.pack_into(fmtStr, send_buf, 24,
                    len(user)+1, 0, user,
                    len(password)+1, 1, password)

    # send message and receive response status
    status = _sendMessage(cluster, send_buf)

    return status

def changePassword(cluster, user, old_password, new_password):

    """
        This function is responsible for changing the password for
        existing user.

        @params:
            cluster        - CitrusleafCluster instance
            user           - <String> username
            old_password   - <String> current password for a user
            new_password   - <String> new password to be set

        @return_values:
            status         - an integer status code
    """

    # get the total size of the buffer
    sz = len(user) + len(old_password) + len(new_password) + 3 * 5 + 24

    # write the header of the message in a buffer
    send_buf = adminWriteHeader(sz, 4, 3)

    fmtStr = "! I B %ds I B %ds I B %ds" % ( len(user),
                                len(old_password), len(new_password) )

    # pack in all necessary fields in a buffer
    struct.pack_into(fmtStr, send_buf, 24,
                    len(user)+1, 0, user,
                    len(old_password)+1, 2, old_password,
                    len(new_password)+1, 1, new_password)

    # send the message and receive response status
    status = _sendMessage(cluster, send_buf)

    return status

def _doRolesOperation(cluster, user, roles, opn):

    """
        This function is responsible for invoking particular
        action on `roles` to a `user`.

        @params:
            cluster        - CitrusleafCluster instance
            user           - <String> username
            roles          - <list> roles' list to be assigned to a user
            opn            - <int> either 5{GRANT} / 6{REVOKE} / 7{REPLACE}

        @return_values:
            status         - an integer status code
    """
    if opn not in [5 ,6 ,7]:
        print "Invalid role operation."
        return -1

    if not roles:
        print "No point in granting empty roles' list."
        return -1

    roles_string = ''.join( [ role for role in roles ] )

    # get total size of the buffer
    sz = len(user) + len(roles_string) + len(roles) + 5 + 6 + 24

    # write message header
    send_buf = adminWriteHeader(sz, opn, 2)

    fmtStr = "! I B %ds" % ( len(user) )

    # pack user in message buffer
    struct.pack_into(fmtStr, send_buf, 24,
                    len(user)+1, 0, user)

    offset = 24 + 5 + len(user)

    # pack roles list in message buffer
    _packRoles(send_buf, offset, roles)

    # send message and receive response status
    status = _sendMessage(cluster, send_buf)

    return status

def grantRoles(cluster, user, roles=[]):

    """
        This function is responsible for granting particular
        set of `roles` to a `user`.

        @params:
            cluster        - CitrusleafCluster instance
            user           - <String> username
            roles          - <list> roles' list to be assigned to a user

        @return_values:
            status         - an integer status code
    """
    return  _doRolesOperation(cluster, user, roles, 5)

def revokeRoles(cluster, user, roles=[]):

    """
        This function is responsible for revoking `roles`
        for a given `user`.

        @params:
            cluster        - CitrusleafCluster instance
            user           - <String> username
            roles          - <list> roles' list to be assigned to a user

        @return_values:
            status         - an integer status code
    """
    return _doRolesOperation(cluster, user, roles, 6)

def replaceRoles(cluster, user, roles=[]):

    """
        This function is responsible for replacing existing roles with new
        for a given user.

        @params:
            cluster        - CitrusleafCluster instance
            user           - <String> username
            roles          - <list> roles' list to be assigned to a user

        @return_values:
            status         - an integer status code

    """
    return _doRolesOperation(cluster, user, roles, 7)
