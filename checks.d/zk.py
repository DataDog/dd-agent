'''
Parses the response from zookeeper's `stat` admin command, which looks like:

```
Zookeeper version: 3.2.2--1, built on 03/16/2010 07:31 GMT
Clients:
 /10.42.114.160:32634[1](queued=0,recved=12,sent=0)
 /10.37.137.74:21873[1](queued=0,recved=53613,sent=0)
 /10.37.137.74:21876[1](queued=0,recved=57436,sent=0)
 /10.115.77.32:32990[1](queued=0,recved=16,sent=0)
 /10.37.137.74:21891[1](queued=0,recved=55011,sent=0)
 /10.37.137.74:21797[1](queued=0,recved=19431,sent=0)

Latency min/avg/max: -10/0/20007
Received: 101032173
Sent: 0
Outstanding: 0
Zxid: 0x1034799c7
Mode: leader
Node count: 487
```

'''

from checks import AgentCheck
import socket
import struct
from StringIO import StringIO

class Zookeeper(AgentCheck):
    def check(self, instance):
        host = instance.get('host', 'localhost')
        port = int(instance.get('port', 2181))
        tags = instance.get('tags', [])

        sock = socket.socket()
        buf = StringIO()
        chunk_size = 1024
        try:
            # Connect to the zk client port and send the stat command
            sock.connect((host, port))
            sock.sendall('stat')

            # Read the response into a StringIO buffer
            chunk = sock.recv(chunk_size)
            buf.write(chunk)
            num_reads = 1
            max_reads = 10000
            while chunk:
                if num_reads > max_reads:
                    # Safeguard against an infinite loop
                    raise Exception("Read %s bytes before exceeding max reads of %s. " % (buf.tell(), max_reads))
                chunk = sock.recv(chunk_size)
                buf.write(chunk)
                num_reads += 1
        finally:
            sock.close()

        # Parse the response
        metrics, new_tags = self.parse_stat(buf)

        # Write the data
        tags.extend(new_tags)
        for metric, value in metrics:
            self.gauge(metric, value, tags=tags)

    @staticmethod
    def parse_stat(buf):
        ''' `buf` is a readable file-like object
            returns a tuple: ([(metric_name, value)], tags)
        '''
        metrics = []
        buf.seek(0)
        start_line = buf.readline()

        # Clients:
        buf.readline() # skip the Clients: header
        num_clients = 0
        client_line = buf.readline().strip()
        if client_line:
            num_clients += 1
        while client_line:
            client_line = buf.readline().strip()
            if client_line:
                num_clients += 1
        metrics.append(('zookeeper.clients', num_clients))

        # Latency min/avg/max: -10/0/20007
        _, value = buf.readline().split(':')
        l_min, l_avg, l_max = [int(v) for v in value.strip().split('/')]
        metrics.append(('zookeeper.latency.min', l_min))
        metrics.append(('zookeeper.latency.avg', l_avg))
        metrics.append(('zookeeper.latency.max', l_max))

        # Received: 101032173
        _, value = buf.readline().split(':')
        metrics.append(('zookeeper.bytes_received', long(value.strip())))

        # Sent: 1324
        _, value = buf.readline().split(':')
        metrics.append(('zookeeper.bytes_sent', long(value.strip())))

        # Outstanding: 0
        _, value = buf.readline().split(':')
        metrics.append(('zookeeper.bytes_outstanding', long(value.strip())))

        # Zxid: 0x1034799c7
        _, value = buf.readline().split(':')
        # Parse as a 64 bit hex int
        zxid = long(value.strip(), 16)
        # convert to bytes
        zxid_bytes = struct.pack('>q', zxid)
        # the higher order 4 bytes is the epoch
        (zxid_epoch,) = struct.unpack('>i', zxid_bytes[0:4])
        # the lower order 4 bytes is the count
        (zxid_count,) = struct.unpack('>i', zxid_bytes[4:8])

        metrics.append(('zookeeper.zxid.epoch', zxid_epoch))
        metrics.append(('zookeeper.zxid.count', zxid_count))

        # Mode: leader
        _, value = buf.readline().split(':')
        tags = [u'mode:' + value.strip().lower()]

        # Node count: 487
        _, value = buf.readline().split(':')
        metrics.append(('zookeeper.nodes', long(value.strip())))

        return metrics, tags

if __name__ == "__main__":
    import logging, pprint
    zk = Zookeeper('zk', {}, {})
    zk.check({'host': 'localhost', 'port': 2181, 'tags': ['thing']})
    pprint.pprint(zk.get_metrics())
