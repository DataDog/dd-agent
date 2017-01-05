# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

'''
As of zookeeper 3.4.0, the `mntr` admin command is provided for easy parsing of zookeeper stats.
This check first parses the `stat` admin command for a version number.
If the zookeeper version supports `mntr`, it is also parsed.

Duplicate information is being reported by both `mntr` and `stat` to keep backwards compatability.
Example:
    `stat` reports: zookeeper.latency.avg
    `mntr` reports: zookeeper.avg.latency
If available, make use of the data reported by `mntr` not `stat`.
The duplicate `stat` reports are only kept for backward compatability.

Besides the usual zookeeper state of `leader`, `follower`, `observer` and `standalone`,
this check will report three other states:

    `down`: the check cannot connect to zookeeper
    `inactive`: the zookeeper instance has lost connection to the cluster
    `unknown`: an unexpected error has occured in this check

States can be accessed through the gauge `zookeeper.instances.<state>,
through the set `zookeeper.instances`, or through the `mode:<state>` tag.

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

`stat` tested with Zookeeper versions 3.0.0 to 3.4.5

The following is an example of the `mntr` commands output:

```
zk_version  3.4.5-cdh4.4.0--1, built on 09/04/2013 01:46 GMT
zk_avg_latency  0
zk_max_latency  0
zk_min_latency  0
zk_packets_received 4
zk_packets_sent 3
zk_num_alive_connections    1
zk_outstanding_requests 0
zk_server_state standalone
zk_znode_count  4
zk_watch_count  0
zk_ephemerals_count 0
zk_approximate_data_size    27
zk_open_file_descriptor_count   29
zk_max_file_descriptor_count    4096
```

`mntr` tested with ZooKeeper 3.4.5
'''
# stdlib
from collections import defaultdict
from distutils.version import LooseVersion # pylint: disable=E0611,E0401
from StringIO import StringIO
import re
import socket
import struct

# project
from checks import AgentCheck


class ZKConnectionFailure(Exception):
    """ Raised when we are unable to connect or get the output of a command. """
    pass


class ZKMetric(tuple):
    """
    A Zookeeper metric.
    Tuple with an optional metric type (default is 'gauge').
    """
    def __new__(cls, name, value, m_type="gauge"):
        return super(ZKMetric, cls).__new__(cls, [name, value, m_type])


class ZookeeperCheck(AgentCheck):
    """
    ZooKeeper AgentCheck.

    Parse content from `stat` and `mntr`(if available) commmands to retrieve health cluster metrics.
    """
    version_pattern = re.compile(r'Zookeeper version: ([^.]+)\.([^.]+)\.([^-]+)', flags=re.I)

    SOURCE_TYPE_NAME = 'zookeeper'

    STATUS_TYPES = [
        'leader',
        'follower',
        'observer',
        'standalone',
        'down',
        'inactive',
    ]

    # `mntr` information to report as `rate`
    _MNTR_RATES = set(
        [
            'zk_packets_received',
            'zk_packets_sent',
        ]
    )

    def check(self, instance):
        host = instance.get('host', 'localhost')
        port = int(instance.get('port', 2181))
        timeout = float(instance.get('timeout', 3.0))
        expected_mode = (instance.get('expected_mode') or '').strip()
        tags = instance.get('tags', [])
        cx_args = (host, port, timeout)
        sc_tags = ["host:{0}".format(host), "port:{0}".format(port)] + list(set(tags))
        hostname = self.hostname
        report_instance_mode = instance.get("report_instance_mode", True)

        zk_version = None  # parse_stat will parse and set version string

        # Send a service check based on the `ruok` response.
        # Set instance status to down if not ok.
        try:
            ruok_out = self._send_command('ruok', *cx_args)
        except ZKConnectionFailure:
            # The server should not respond at all if it's not OK.
            status = AgentCheck.CRITICAL
            message = 'No response from `ruok` command'
            self.increment('zookeeper.timeouts')

            if report_instance_mode:
                self.report_instance_mode(hostname, 'down', tags)
            raise
        else:
            ruok_out.seek(0)
            ruok = ruok_out.readline()
            if ruok == 'imok':
                status = AgentCheck.OK
            else:
                status = AgentCheck.WARNING
            message = u'Response from the server: %s' % ruok
        finally:
            self.service_check(
                'zookeeper.ruok', status, message=message, tags=sc_tags
            )

        # Read metrics from the `stat` output.
        try:
            stat_out = self._send_command('stat', *cx_args)
        except ZKConnectionFailure:
            self.increment('zookeeper.timeouts')
            if report_instance_mode:
                self.report_instance_mode(hostname, 'down', tags)
            raise
        except Exception as e:
            self.warning(e)
            self.increment('zookeeper.datadog_client_exception')
            if report_instance_mode:
                self.report_instance_mode(hostname, 'unknown', tags)
            raise
        else:
            # Parse the response
            metrics, new_tags, mode, zk_version = self.parse_stat(stat_out)

            # Write the data
            if mode != 'inactive':
                for metric, value, m_type in metrics:
                    submit_metric = getattr(self, m_type)
                    submit_metric(metric, value, tags=tags + new_tags)

            if report_instance_mode:
                self.report_instance_mode(hostname, mode, tags)

            if expected_mode:
                if mode == expected_mode:
                    status = AgentCheck.OK
                    message = u"Server is in %s mode" % mode
                else:
                    status = AgentCheck.CRITICAL
                    message = u"Server is in %s mode but check expects %s mode"\
                              % (mode, expected_mode)
                self.service_check('zookeeper.mode', status, message=message,
                                   tags=sc_tags)

        # Read metrics from the `mntr` output
        if zk_version and LooseVersion(zk_version) > LooseVersion("3.4.0"):
            try:
                mntr_out = self._send_command('mntr', *cx_args)
            except ZKConnectionFailure:
                self.increment('zookeeper.timeouts')
                if report_instance_mode:
                    self.report_instance_mode(hostname, 'down', tags)
                raise
            except Exception as e:
                self.warning(e)
                self.increment('zookeeper.datadog_client_exception')
                if report_instance_mode:
                    self.report_instance_mode(hostname, 'unknown', tags)
                raise
            else:
                metrics, mode = self.parse_mntr(mntr_out)
                mode_tag = "mode:%s" % mode
                if mode != 'inactive':
                    for metric, value, m_type in metrics:
                        submit_metric = getattr(self, m_type)
                        submit_metric(metric, value, tags=tags + [mode_tag])

                if report_instance_mode:
                    self.report_instance_mode(hostname, mode, tags)

    def report_instance_mode(self, hostname, mode, tags):
        gauges = defaultdict(int)
        if mode not in self.STATUS_TYPES:
            mode = "unknown"

        tags = tags + ['mode:%s' % mode]
        self.set('zookeeper.instances', hostname, tags=tags)
        gauges[mode] = 1

        for k, v in gauges.iteritems():
            gauge_name = 'zookeeper.instances.%s' % k
            self.gauge(gauge_name, v)

    def _send_command(self, command, host, port, timeout):
        sock = socket.socket()
        sock.settimeout(timeout)
        buf = StringIO()
        chunk_size = 1024
        # try-finally and try-except to stay compatible with python 2.4
        try:
            try:
                # Connect to the zk client port and send the stat command
                sock.connect((host, port))
                sock.sendall(command)

                # Read the response into a StringIO buffer
                chunk = sock.recv(chunk_size)
                buf.write(chunk)
                num_reads = 1
                max_reads = 10000
                while chunk:
                    if num_reads > max_reads:
                        # Safeguard against an infinite loop
                        raise Exception("Read %s bytes before exceeding max reads of %s. "
                                        % (buf.tell(), max_reads))
                    chunk = sock.recv(chunk_size)
                    buf.write(chunk)
                    num_reads += 1
            except (socket.timeout, socket.error):
                raise ZKConnectionFailure()
        finally:
            sock.close()
        return buf

    def parse_stat(self, buf):
        ''' `buf` is a readable file-like object
            returns a tuple: (metrics, tags, mode, version)
        '''
        metrics = []
        buf.seek(0)

        # Check the version line to make sure we parse the rest of the
        # body correctly. Particularly, the Connections val was added in
        # >= 3.4.4.
        start_line = buf.readline()
        match = self.version_pattern.match(start_line)
        if match is None:
            return (None, None, "inactive", None)
            raise Exception("Could not parse version from stat command output: %s" % start_line)
        else:
            version_tuple = match.groups()
        has_connections_val = version_tuple >= ('3', '4', '4')
        version = "%s.%s.%s" % version_tuple

        # Clients:
        buf.readline()  # skip the Clients: header
        connections = 0
        client_line = buf.readline().strip()
        if client_line:
            connections += 1
        while client_line:
            client_line = buf.readline().strip()
            if client_line:
                connections += 1

        # Latency min/avg/max: -10/0/20007
        _, value = buf.readline().split(':')
        l_min, l_avg, l_max = [int(v) for v in value.strip().split('/')]
        metrics.append(ZKMetric('zookeeper.latency.min', l_min))
        metrics.append(ZKMetric('zookeeper.latency.avg', l_avg))
        metrics.append(ZKMetric('zookeeper.latency.max', l_max))

        # Received: 101032173
        _, value = buf.readline().split(':')
        metrics.append(ZKMetric('zookeeper.bytes_received', long(value.strip())))

        # Sent: 1324
        _, value = buf.readline().split(':')
        metrics.append(ZKMetric('zookeeper.bytes_sent', long(value.strip())))

        if has_connections_val:
            # Connections: 1
            _, value = buf.readline().split(':')
            metrics.append(ZKMetric('zookeeper.connections', int(value.strip())))
        else:
            # If the zk version doesnt explicitly give the Connections val,
            # use the value we computed from the client list.
            metrics.append(ZKMetric('zookeeper.connections', connections))

        # Outstanding: 0
        _, value = buf.readline().split(':')
        # Fixme: This metric name is wrong. It should be removed in a major version of the agent
        # See https://github.com/DataDog/dd-agent/issues/1383
        metrics.append(ZKMetric('zookeeper.bytes_outstanding', long(value.strip())))
        metrics.append(ZKMetric('zookeeper.outstanding_requests', long(value.strip())))

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

        metrics.append(ZKMetric('zookeeper.zxid.epoch', zxid_epoch))
        metrics.append(ZKMetric('zookeeper.zxid.count', zxid_count))

        # Mode: leader
        _, value = buf.readline().split(':')
        mode = value.strip().lower()
        tags = [u'mode:' + mode]

        # Node count: 487
        _, value = buf.readline().split(':')
        metrics.append(ZKMetric('zookeeper.nodes', long(value.strip())))

        return metrics, tags, mode, version

    def parse_mntr(self, buf):
        '''
        Parse `mntr` command's content.
        `buf` is a readable file-like object

        Returns: a tuple (metrics, mode)
        if mode == 'inactive', metrics will be None
        '''
        buf.seek(0)
        first = buf.readline()  # First is version string or error
        if first == 'This ZooKeeper instance is not currently serving requests':
            return (None, 'inactive')

        metrics = []
        mode = 'inactive'

        for line in buf:
            try:
                key, value = line.split()

                if key == "zk_server_state":
                    mode = value.lower()
                    continue

                metric_name = self._normalize_metric_label(key)
                metric_type = "rate" if key in self._MNTR_RATES else "gauge"
                metric_value = int(value)
                metrics.append(ZKMetric(metric_name, metric_value, metric_type))

            except ValueError:
                self.log.warning(
                    u"Cannot format `mntr` value. key={key}, value{value}".format(
                        key=key, value=value
                    )
                )
                continue
            except Exception:
                self.log.exception(
                    u"Unexpected exception occurred while parsing `mntr` command content:\n"
                    u"{buf}".format(
                        buf=buf
                    )
                )

        return (metrics, mode)

    def _normalize_metric_label(self, key):
        if re.match('zk', key):
            key = key.replace('zk', 'zookeeper', 1)
        return key.replace('_', '.', 1)
