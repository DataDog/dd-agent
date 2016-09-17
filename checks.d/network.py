# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""
Collects network metrics.
"""
# stdlib
import re
import socket
from collections import defaultdict

# project
from checks import AgentCheck
from utils.platform import Platform
from utils.subprocess_output import (
    get_subprocess_output,
    SubprocessOutputEmptyError,
)
import psutil

BSD_TCP_METRICS = [
    (re.compile("^\s*(\d+) data packets \(\d+ bytes\) retransmitted\s*$"), 'system.net.tcp.retrans_packs'),
    (re.compile("^\s*(\d+) packets sent\s*$"), 'system.net.tcp.sent_packs'),
    (re.compile("^\s*(\d+) packets received\s*$"), 'system.net.tcp.rcv_packs')
]

SOLARIS_TCP_METRICS = [
    (re.compile("\s*tcpRetransSegs\s*=\s*(\d+)\s*"), 'system.net.tcp.retrans_segs'),
    (re.compile("\s*tcpOutDataSegs\s*=\s*(\d+)\s*"), 'system.net.tcp.in_segs'),
    (re.compile("\s*tcpInSegs\s*=\s*(\d+)\s*"), 'system.net.tcp.out_segs')
]


class Network(AgentCheck):

    SOURCE_TYPE_NAME = 'system'

    TCP_STATES = {
        "ss": {
            "ESTAB": "estab",
            "SYN-SENT": "syn_sent",
            "SYN-RECV": "syn_recv",
            "FIN-WAIT-1": "fin_wait_1",
            "FIN-WAIT-2": "fin_wait_2",
            "TIME-WAIT": "time_wait",
            "UNCONN": "unconn",
            "CLOSE-WAIT": "close_wait",
            "LAST-ACK": "last_ack",
            "LISTEN": "listen",
            "CLOSING": "closing",
        },
        "netstat": {
            "ESTABLISHED": "estab",
            "SYN_SENT": "syn_sent",
            "SYN_RECV": "syn_recv",
            "FIN_WAIT1": "fin_wait_1",
            "FIN_WAIT2": "fin_wait_2",
            "TIME_WAIT": "time_wait",
            "CLOSE": "close",
            "CLOSE_WAIT": "close_wait",
            "LAST_ACK": "last_ack",
            "LISTEN": "listen",
            "CLOSING": "closing",
        },
        "psutil": {
            psutil.CONN_ESTABLISHED: "established",
            psutil.CONN_SYN_SENT: "opening",
            psutil.CONN_SYN_RECV: "opening",
            psutil.CONN_FIN_WAIT1: "closing",
            psutil.CONN_FIN_WAIT2: "closing",
            psutil.CONN_TIME_WAIT: "time_wait",
            psutil.CONN_CLOSE: "closing",
            psutil.CONN_CLOSE_WAIT: "closing",
            psutil.CONN_LAST_ACK: "closing",
            psutil.CONN_LISTEN: "listening",
            psutil.CONN_CLOSING: "closing",
            psutil.CONN_NONE: "connections",  # CONN_NONE is always returned for udp connections
        }
    }

    PSUTIL_TYPE_MAPPING = {
        socket.SOCK_STREAM: 'tcp',
        socket.SOCK_DGRAM: 'udp',
    }

    PSUTIL_FAMILY_MAPPING = {
        socket.AF_INET: '4',
        socket.AF_INET6: '6',
    }

    CX_STATE_GAUGE = {
        ('udp4', 'connections') : 'system.net.udp4.connections',
        ('udp6', 'connections') : 'system.net.udp6.connections',

        ('tcp4', 'estab') : 'system.net.tcp4.estab',
        ('tcp4', 'syn_sent') : 'system.net.tcp4.syn_sent',
        ('tcp4', 'syn_recv') : 'system.net.tcp4.syn_recv',
        ('tcp4', 'fin_wait_1') : 'system.net.tcp4.fin_wait_1',
        ('tcp4', 'fin_wait_2') : 'system.net.tcp4.fin_wait_2',
        ('tcp4', 'time_wait') : 'system.net.tcp4.time_wait',
        ('tcp4', 'unconn') : 'system.net.tcp4.unconn',
        ('tcp4', 'close') : 'system.net.tcp4.close',
        ('tcp4', 'close_wait') : 'system.net.tcp4.close_wait',
        ('tcp4', 'closing') : 'system.net.tcp4.closing',
        ('tcp4', 'listen') : 'system.net.tcp4.listen',
        ('tcp4', 'last_ack') : 'system.net.tcp4.time_wait',

        ('tcp6', 'estab') : 'system.net.tcp4.estab',
        ('tcp6', 'syn_sent') : 'system.net.tcp4.syn_sent',
        ('tcp6', 'syn_recv') : 'system.net.tcp4.syn_recv',
        ('tcp6', 'fin_wait_1') : 'system.net.tcp4.fin_wait_1',
        ('tcp6', 'fin_wait_2') : 'system.net.tcp4.fin_wait_2',
        ('tcp6', 'time_wait') : 'system.net.tcp4.time_wait',
        ('tcp6', 'unconn') : 'system.net.tcp4.unconn',
        ('tcp6', 'close') : 'system.net.tcp4.close',
        ('tcp6', 'close_wait') : 'system.net.tcp4.close_wait',
        ('tcp6', 'closing') : 'system.net.tcp4.closing',
        ('tcp6', 'listen') : 'system.net.tcp4.listen',
        ('tcp6', 'last_ack') : 'system.net.tcp4.time_wait',
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        if instances is not None and len(instances) > 1:
            raise Exception("Network check only supports one configured instance.")

    def check(self, instance):
        if instance is None:
            instance = {}

        self._excluded_ifaces = instance.get('excluded_interfaces', [])
        self._collect_cx_state = instance.get('collect_connection_state', False)

        self._exclude_iface_re = None
        exclude_re = instance.get('excluded_interface_re', None)
        if exclude_re:
            self.log.debug("Excluding network devices matching: %s" % exclude_re)
            self._exclude_iface_re = re.compile(exclude_re)

        if Platform.is_linux():
            self._check_linux(instance)
        elif Platform.is_bsd():
            self._check_bsd(instance)
        elif Platform.is_solaris():
            self._check_solaris(instance)
        elif Platform.is_windows():
            self._check_psutil()

    def _submit_devicemetrics(self, iface, vals_by_metric):
        if iface in self._excluded_ifaces or (self._exclude_iface_re and self._exclude_iface_re.match(iface)):
            # Skip this network interface.
            return False

        expected_metrics = [
            'bytes_rcvd',
            'bytes_sent',
            'packets_in.count',
            'packets_in.error',
            'packets_out.count',
            'packets_out.error',
        ]
        for m in expected_metrics:
            assert m in vals_by_metric
        assert len(vals_by_metric) == len(expected_metrics)

        count = 0
        for metric, val in vals_by_metric.iteritems():
            self.rate('system.net.%s' % metric, val, device_name=iface)
            count += 1
        self.log.debug("tracked %s network metrics for interface %s" % (count, iface))

    def _parse_value(self, v):
        if v == "-":
            return 0
        else:
            try:
                return long(v)
            except ValueError:
                return 0

    def _submit_regexed_values(self, output, regex_list):
        lines = output.splitlines()
        for line in lines:
            for regex, metric in regex_list:
                value = re.match(regex, line)
                if value:
                    self.rate(metric, self._parse_value(value.group(1)))

    def _check_linux(self, instance):
        proc_location = self.agentConfig.get('procfs_path', '/proc').rstrip('/')
        if self._collect_cx_state:
            try:
                self.log.debug("Using `ss` to collect connection state")
                # Try using `ss` for increased performance over `netstat`
                for ip_version in ['4', '6']:
                    # Call `ss` for each IP version because there's no built-in way of distinguishing
                    # between the IP versions in the output
                    output, _, _ = get_subprocess_output(["ss", "-n", "-u", "-t", "-a", "-{0}".format(ip_version)], self.log)
                    lines = output.splitlines()
                    # Netid  State      Recv-Q Send-Q     Local Address:Port       Peer Address:Port
                    # udp    UNCONN     0      0              127.0.0.1:8125                  *:*
                    # udp    ESTAB      0      0              127.0.0.1:37036         127.0.0.1:8125
                    # udp    UNCONN     0      0        fe80::a00:27ff:fe1c:3c4:123          :::*
                    # tcp    TIME-WAIT  0      0          90.56.111.177:56867        46.105.75.4:143
                    # tcp    LISTEN     0      0       ::ffff:127.0.0.1:33217  ::ffff:127.0.0.1:7199
                    # tcp    ESTAB      0      0       ::ffff:127.0.0.1:58975  ::ffff:127.0.0.1:2181

                    metrics = self._parse_linux_cx_state(lines[1:], self.TCP_STATES['ss'], 1, ip_version=ip_version)
                    # Only send the metrics which match the loop iteration's ip version
                    for stat, metric in self.CX_STATE_GAUGE.iteritems():
                        if stat[0].endswith(ip_version):
                            self.gauge(metric, metrics.get(metric))

            except OSError:
                self.log.info("`ss` not found: using `netstat` as a fallback")
                output, _, _ = get_subprocess_output(["netstat", "-n", "-u", "-t", "-a"], self.log)
                lines = output.splitlines()
                # Active Internet connections (w/o servers)
                # Proto Recv-Q Send-Q Local Address           Foreign Address         State
                # tcp        0      0 46.105.75.4:80          79.220.227.193:2032     SYN_RECV
                # tcp        0      0 46.105.75.4:143         90.56.111.177:56867     ESTABLISHED
                # tcp        0      0 46.105.75.4:50468       107.20.207.175:443      TIME_WAIT
                # tcp6       0      0 46.105.75.4:80          93.15.237.188:58038     FIN_WAIT2
                # tcp6       0      0 46.105.75.4:80          79.220.227.193:2029     ESTABLISHED
                # udp        0      0 0.0.0.0:123             0.0.0.0:*
                # udp6       0      0 :::41458                :::*

                metrics = self._parse_linux_cx_state(lines[2:], self.TCP_STATES['netstat'], 5)
                for metric, value in metrics.iteritems():
                    self.gauge(metric, value)
            except SubprocessOutputEmptyError:
                self.log.exception("Error collecting connection stats.")

        proc_dev_path = "{}/net/dev".format(proc_location)
        proc = open(proc_dev_path, 'r')
        try:
            lines = proc.readlines()
        finally:
            proc.close()
        # Inter-|   Receive                                                 |  Transmit
        #  face |bytes     packets errs drop fifo frame compressed multicast|bytes       packets errs drop fifo colls carrier compressed
        #     lo:45890956   112797   0    0    0     0          0         0    45890956   112797    0    0    0     0       0          0
        #   eth0:631947052 1042233   0   19    0   184          0      1206  1208625538  1320529    0    0    0     0       0          0
        #   eth1:       0        0   0    0    0     0          0         0           0        0    0    0    0     0       0          0
        for l in lines[2:]:
            cols = l.split(':', 1)
            x = cols[1].split()
            # Filter inactive interfaces
            if self._parse_value(x[0]) or self._parse_value(x[8]):
                iface = cols[0].strip()
                metrics = {
                    'bytes_rcvd': self._parse_value(x[0]),
                    'bytes_sent': self._parse_value(x[8]),
                    'packets_in.count': self._parse_value(x[1]),
                    'packets_in.error': self._parse_value(x[2]) + self._parse_value(x[3]),
                    'packets_out.count': self._parse_value(x[9]),
                    'packets_out.error':self._parse_value(x[10]) + self._parse_value(x[11]),
                }
                self._submit_devicemetrics(iface, metrics)

        try:
            proc_snmp_path = "{}/net/snmp".format(proc_location)
            proc = open(proc_snmp_path, 'r')

            # IP:      Forwarding   DefaultTTL InReceives     InHdrErrors  ...
            # IP:      2            64         377145470      0            ...
            # Icmp:    InMsgs       InErrors   InDestUnreachs InTimeExcds  ...
            # Icmp:    1644495      1238       1643257        0            ...
            # IcmpMsg: InType3      OutType3
            # IcmpMsg: 1643257      1643257
            # Tcp:     RtoAlgorithm RtoMin     RtoMax         MaxConn      ...
            # Tcp:     1            200        120000         -1           ...
            # Udp:     InDatagrams  NoPorts    InErrors       OutDatagrams ...
            # Udp:     24249494     1643257    0              25892947     ...
            # UdpLite: InDatagrams  Noports    InErrors       OutDatagrams ...
            # UdpLite: 0            0          0              0            ...
            try:
                lines = proc.readlines()
            finally:
                proc.close()

            tcp_lines = [line for line in lines if line.startswith('Tcp:')]
            udp_lines = [line for line in lines if line.startswith('Udp:')]
            ip_lines = [line for line in lines if line.startswith('Ip:')]
            icmp_lines = [line for line in lines if line.startswith('Icmp:')]
            icmp_msg_lines = [line for line in lines if line.startswith('IcmpMsg:')]

            tcp_column_names = tcp_lines[0].strip().split()
            tcp_values = tcp_lines[1].strip().split()
            tcp_metrics = dict(zip(tcp_column_names, tcp_values))

            udp_column_names = udp_lines[0].strip().split()
            udp_values = udp_lines[1].strip().split()
            udp_metrics = dict(zip(udp_column_names, udp_values))

            ip_column_names = ip_lines[0].strip().split()
            ip_values = ip_lines[1].strip().split()
            ip_metrics = dict(zip(ip_column_names, ip_values))

            icmp_column_names = icmp_lines[0].strip().split()
            icmp_values = icmp_lines[1].strip().split()
            icmp_metrics = dict(zip(icmp_column_names, icmp_values))

            icmp_msg_column_names = icmp_msg_lines[0].strip().split()
            icmp_msg_values = icmp_msg_lines[1].strip().split()
            icmp_msg_metrics = dict(zip(icmp_msg_column_names, icmp_msg_values))

            # line start indicating what kind of metrics we're looking at
            assert(tcp_metrics['Tcp:'] == 'Tcp:')

            tcp_metrics_name = {
                'RtoAlgorithm'	: 'system.net.tcp.rto_algorithm',
                'RtoMin'	    : 'system.net.tcp.rto_min',
                'RtoMax'	    : 'system.net.tcp.rto_max',
                'MaxConn'	    : 'system.net.tcp.max_conn',
                'ActiveOpens'	: 'system.net.tcp.active_opens',
                'PassiveOpens'	: 'system.net.tcp.passive_opens',
                'AttemptFails'	: 'system.net.tcp.attempt_fails',
                'EstabResets'	: 'system.net.tcp.estab_resets',
                'CurrEstab'	    : 'system.net.tcp.curr_estab',
                'InSegs'	    : 'system.net.tcp.in_segs',
                'OutSegs'	    : 'system.net.tcp.out_segs',
                'RetransSegs'	: 'system.net.tcp.retrans_segs',
                'InErrs'	    : 'system.net.tcp.in_errs',
                'OutRsts'	    : 'system.net.tcp.out_rsts',
                'InCsumErrors'	: 'system.net.tcp.in_csum_errors'
            }

            for key, metric in tcp_metrics_name.iteritems():
                if key in tcp_metrics:
                    self.rate(metric, self._parse_value(tcp_metrics[key]))

            assert(udp_metrics['Udp:'] == 'Udp:')

            udp_metrics_name = {
                'InDatagrams'   : 'system.net.udp.in_datagrams',
                'NoPorts'       : 'system.net.udp.no_ports',
                'InErrors'      : 'system.net.udp.in_errors',
                'OutDatagrams'  : 'system.net.udp.out_datagrams',
                'RcvbufErrors'  : 'system.net.udp.rcv_buf_errors',
                'SndbufErrors'  : 'system.net.udp.snd_buf_errors',
                'InCsumErrors'	: 'system.net.udp.in_csum_errors'
            }
            for key, metric in udp_metrics_name.iteritems():
                if key in udp_metrics:
                    self.rate(metric, self._parse_value(udp_metrics[key]))

            assert(ip_metrics['Ip:'] == 'Ip:')

            ip_metrics_name = {
                'Forwarding'	   : 'system.net.ip.forwarding',
                'DefaultTTL'	   : 'system.net.ip.default_ttl',
                'InReceives'	   : 'system.net.ip.in_receives',
                'InHdrErrors'	   : 'system.net.ip.in_hdr_errors',
                'InAddrErrors'	   : 'system.net.ip.in_addr_errors',
                'ForwDatagrams'	   : 'system.net.ip.forw_datagrams',
                'InUnknownProtos'  : 'system.net.ip.in_unknown_protos',
                'InDiscards'	   : 'system.net.ip.in_discards',
                'InDelivers'	   : 'system.net.ip.in_delivers',
                'OutRequests'	   : 'system.net.ip.out_requests',
                'OutDiscards'	   : 'system.net.ip.out_discards',
                'OutNoRoutes'	   : 'system.net.ip.out_no_routes',
                'ReasmTimeout'	   : 'system.net.ip.reasm_timeout',
                'ReasmReqds'	   : 'system.net.ip.reasm_reqds',
                'ReasmOKs'	       : 'system.net.ip.reasm_oks',
                'ReasmFails'	   : 'system.net.ip.reasm_fails',
                'FragOKs'	       : 'system.net.ip.frag_oks',
                'FragFails'	       : 'system.net.ip.frag_fails',
                'FragCreates'	   : 'system.net.ip.frag_creates'
            }
            for key, metric in ip_metrics_name.iteritems():
                if key in ip_metrics:
                    self.rate(metric, self._parse_value(ip_metrics[key]))

            assert(icmp_metrics['Icmp:'] == 'Icmp:')

            icmp_metrics_name = {
                'InMsgs'	        : 'system.net.icmp.in_msgs',
                'InErrors'	        : 'system.net.icmp.in_errors',
                'InCsumErrors'	    : 'system.net.icmp.in_csum_errors',
                'InDestUnreachs'    : 'system.net.icmp.in_dest_unreachs',
                'InTimeExcds'	    : 'system.net.icmp.in_time_excds',
                'InParmProbs'	    : 'system.net.icmp.in_param_probs',
                'InSrcQuenchs'	    : 'system.net.icmp.in_src_quenchs',
                'InRedirects'	    : 'system.net.icmp.in_redirects',
                'InEchos'	        : 'system.net.icmp.in_echos',
                'InEchoReps'	    : 'system.net.icmp.in_echos_reps',
                'InTimestamps'	    : 'system.net.icmp.in_timestamps',
                'InTimestampReps'   : 'system.net.icmp.in_timestams_reps',
                'InAddrMasks'	    : 'system.net.icmp.in_addr_masks',
                'InAddrMaskReps'    : 'system.net.icmp.in_addr_mask_reps',
                'OutMsgs'	        : 'system.net.icmp.out_msgs',
                'OutErrors'	        : 'system.net.icmp.out_errors',
                'OutDestUnreachs'   : 'system.net.icmp.out_dest_unreachs',
                'OutTimeExcds'	    : 'system.net.icmp.out_time_excds',
                'OutParmProbs'	    : 'system.net.icmp.out_parm_probs',
                'OutSrcQuenchs'	    : 'system.net.icmp.out_src_quenchs',
                'OutRedirects'	    : 'system.net.icmp.out_redirects',
                'OutEchos'	        : 'system.net.icmp.out_echos',
                'OutEchoReps'	    : 'system.net.icmp.out_echo_reps',
                'OutTimestamps'	    : 'system.net.icmp.out_timestamps',
                'OutTimestampReps'  : 'system.net.icmp.out_timestamp_reps',
                'OutAddrMasks'	    : 'system.net.icmp.out_addr_masks',
                'OutAddrMaskReps'	: 'system.net.icmp.out_addr_mask_reps'
            }
            for key, metric in icmp_metrics_name.iteritems():
                if key in icmp_metrics:
                    self.rate(metric, self._parse_value(icmp_metrics[key]))

            assert(icmp_msg_metrics['IcmpMsg:'] == 'IcmpMsg:')

            icmp_msg_metrics_name = {
                'InType3'	: 'system.net.icmp_msg.in_type_3',
                'InType8'	: 'system.net.icmp_msg.in_type_8',
                'OutType0'	: 'system.net.icmp_msg.out_type_0',
                'OutType3'	: 'system.net.icmp_msg.out_type_3',
                'OutType11'	: 'system.net.icmp_msg.out_type_11',
            }
            for key, metric in icmp_msg_metrics_name.iteritems():
                if key in icmp_msg_metrics:
                    self.rate(metric, self._parse_value(icmp_msg_metrics[key]))

        except IOError:
            # On Openshift, /proc/net/snmp is only readable by root
            self.log.debug("Unable to read %s.", proc_snmp_path)

        try:
            proc_netstat_path = "{}/net/netstat".format(proc_location)
            proc = open(proc_netstat_path, 'r')

            # TcpExt: SyncookiesSent SyncookiesRecv SyncookiesFailed  ...
            # TcpExt: 141632012 134142477 442066090 14721903          ...
            # IpExt: InNoRoutes InTruncatedPkts InMcastPkts           ...
            # IpExt: 0 0 0 0                                          ...

            try:
                lines = proc.readlines()
            finally:
                proc.close()

            tcpext_lines = [line for line in lines if line.startswith('TcpExt:')]
            ipext_lines = [line for line in lines if line.startswith('IpExt:')]

            tcpext_column_names = tcpext_lines[0].strip().split()
            tcpext_values = tcpext_lines[1].strip().split()
            tcpext_metrics = dict(zip(tcpext_column_names, tcpext_values))

            ipext_column_names = ipext_lines[0].strip().split()
            ipext_values = ipext_lines[1].strip().split()
            ipext_metrics = dict(zip(ipext_column_names, ipext_values))

            # line start indicating what kind of metrics we're looking at
            assert(tcp_metrics['TcpExt:'] == 'TcpExt:')

            tcpext_metrics_name = {
                'SyncookiesSent'	        : 'system.net.tcpext.syncookies_sent',
                'SyncookiesRecv'	        : 'system.net.tcpext.syncookies_recv',
                'SyncookiesFailed'	        : 'system.net.tcpext.syncookies_failed',
                'EmbryonicRsts'	            : 'system.net.tcpext.embryonic_rsts',
                'PruneCalled'	            : 'system.net.tcpext.prune_called',
                'RcvPruned'	                : 'system.net.tcpext.rcv_pruned',
                'OfoPruned'	                : 'system.net.tcpext.ofo_pruned',
                'OutOfWindowIcmps'	        : 'system.net.tcpext.out_of_window_icmps',
                'LockDroppedIcmps'	        : 'system.net.tcpext.locl_dropped_icmps',
                'ArpFilter'	                : 'system.net.tcpext.arp_filter',
                'TW'	                    : 'system.net.tcpext.tw',
                'TWRecycled'	            : 'system.net.tcpext.tw_recycled',
                'TWKilled'	                : 'system.net.tcpext.tw_killed',
                'PAWSPassive'	            : 'system.net.tcpext.paws_passive',
                'PAWSActive'	            : 'system.net.tcpext.paws_active',
                'PAWSEstab'	                : 'system.net.tcpext.paws_estab',
                'DelayedACKs'	            : 'system.net.tcpext.delayed_acks',
                'DelayedACKLocked'	        : 'system.net.tcpext.delayed_ack_locked',
                'DelayedACKLost'	        : 'system.net.tcpext.delayed_ack_lost',
                'ListenOverflows'	        : 'system.net.tcpext.listen_overflows',
                'ListenDrops'	            : 'system.net.tcpext.listen_drops',
                'TCPPrequeued'	            : 'system.net.tcpext.prequeued',
                'TCPDirectCopyFromBacklog'	: 'system.net.tcpext.direct_copy_from_backlog',
                'TCPDirectCopyFromPrequeue'	: 'system.net.tcpext.direct_copy_from_prequeue',
                'TCPPrequeueDropped'	    : 'system.net.tcpext.prequeued_dropped',
                'TCPHPHits'	                : 'system.net.tcpext.hp_hits',
                'TCPHPHitsToUser'	        : 'system.net.tcpext.hp_hits_to_user',
                'TCPPureAcks'	            : 'system.net.tcpext.pure_acks',
                'TCPHPAcks'	                : 'system.net.tcpext.hp_acks',
                'TCPRenoRecovery'	        : 'system.net.tcpext.reno_recovery',
                'TCPSackRecovery'	        : 'system.net.tcpext.sack_recovery',
                'TCPSACKReneging'	        : 'system.net.tcpext.sack_reneging',
                'TCPFACKReorder'	        : 'system.net.tcpext.fack_reorder',
                'TCPSACKReorder'	        : 'system.net.tcpext.sack_reorder',
                'TCPRenoReorder'	        : 'system.net.tcpext.reno_reorder',
                'TCPTSReorder'	            : 'system.net.tcpext.ts_reorder',
                'TCPFullUndo'	            : 'system.net.tcpext.full_undo',
                'TCPPartialUndo'	        : 'system.net.tcpext.partial_undo',
                'TCPDSACKUndo'	            : 'system.net.tcpext.dsack_undo',
                'TCPLossUndo'	            : 'system.net.tcpext.loss_undo',
                'TCPLostRetransmit'	        : 'system.net.tcpext.lost_retransmit',
                'TCPRenoFailures'	        : 'system.net.tcpext.reno_failures',
                'TCPSackFailures'	        : 'system.net.tcpext.sack_failures',
                'TCPLossFailures'	        : 'system.net.tcpext.loss_failures',
                'TCPFastRetrans'	        : 'system.net.tcpext.fast_retrans',
                'TCPForwardRetrans'	        : 'system.net.tcpext.forward_retrans',
                'TCPSlowStartRetrans'	    : 'system.net.tcpext.slow_start_retrans',
                'TCPTimeouts'	            : 'system.net.tcpext.timeouts',
                'TCPLossProbes'	            : 'system.net.tcpext.loss_probes',
                'TCPLossProbeRecovery'	    : 'system.net.tcpext.loss_probe_recovery',
                'TCPRenoRecoveryFail'	    : 'system.net.tcpext.reno_recovery_fail',
                'TCPSackRecoveryFail'	    : 'system.net.tcpext.sack_recovery_fail',
                'TCPSchedulerFailed'	    : 'system.net.tcpext.scheduler_failed',
                'TCPRcvCollapsed'	        : 'system.net.tcpext.rcv_collapsed',
                'TCPDSACKOldSent'	        : 'system.net.tcpext.sack_old_sent',
                'TCPDSACKOfoSent'	        : 'system.net.tcpext.sack_ofo_sent',
                'TCPDSACKRecv'	            : 'system.net.tcpext.dsack_recv',
                'TCPDSACKOfoRecv'	        : 'system.net.tcpext.sack_ofo_recv',
                'TCPAbortOnData'	        : 'system.net.tcpext.abort_on_data',
                'TCPAbortOnClose'	        : 'system.net.tcpext.abort_on_close',
                'TCPAbortOnMemory'	        : 'system.net.tcpext.abort_on_memory',
                'TCPAbortOnTimeout'	        : 'system.net.tcpext.abort_on_timeout',
                'TCPAbortOnLinger'	        : 'system.net.tcpext.abort_on_linger',
                'TCPAbortFailed'	        : 'system.net.tcpext.abort_failed',
                'TCPMemoryPressures'	    : 'system.net.tcpext.memory_pressures',
                'TCPSACKDiscard'	        : 'system.net.tcpext.sack_discard',
                'TCPDSACKIgnoredOld'	    : 'system.net.tcpext.dsack_ignore_old',
                'TCPDSACKIgnoredNoUndo'	    : 'system.net.tcpext.dsack_ignore_no_undo',
                'TCPSpuriousRTOs'	        : 'system.net.tcpext.spurious_rtos',
                'TCPMD5NotFound'	        : 'system.net.tcpext.md5_not_found',
                'TCPMD5Unexpected'	        : 'system.net.tcpext.md5_unexpected',
                'TCPSackShifted'	        : 'system.net.tcpext.sack_shifted',
                'TCPSackMerged'	            : 'system.net.tcpext.sack_merged',
                'TCPSackShiftFallback'	    : 'system.net.tcpext.sack_shift_fallback',
                'TCPBacklogDrop'	        : 'system.net.tcpext.backlog_drop',
                'TCPMinTTLDrop'	            : 'system.net.tcpext.min_ttl_drop',
                'TCPDeferAcceptDrop'	    : 'system.net.tcpext.defer_accept_drop',
                'IPReversePathFilter'	    : 'system.net.tcpext.reverse_path_filter',
                'TCPTimeWaitOverflow'	    : 'system.net.tcpext.time_wait_overflow',
                'TCPReqQFullDoCookies'	    : 'system.net.tcpext.req_q_full_do_cookies',
                'TCPReqQFullDrop'	        : 'system.net.tcpext.req_q_full_drop',
                'TCPRetransFail'	        : 'system.net.tcpext.retrans_fail',
                'TCPRcvCoalesce'	        : 'system.net.tcpext.rcv_coalesce',
                'TCPOFOQueue'	            : 'system.net.tcpext.ofo_queue',
                'TCPOFODrop'	            : 'system.net.tcpext.ofo_drop',
                'TCPOFOMerge'	            : 'system.net.tcpext.ofo_merge',
                'TCPChallengeACK'	        : 'system.net.tcpext.challenge_ack',
                'TCPSYNChallenge'	        : 'system.net.tcpext.syn_challenge',
                'TCPFastOpenActive'	        : 'system.net.tcpext.fast_open_active',
                'TCPFastOpenPassive'	    : 'system.net.tcpext.fast_open_passive',
                'TCPFastOpenPassiveFail'	: 'system.net.tcpext.fast_open_passive_fail',
                'TCPFastOpenListenOverflow'	: 'system.net.tcpext.fast_open_listen_overflow',
                'TCPFastOpenCookieReqd'	    : 'system.net.tcpext.fast_open_cookie_reqd',
                'TCPSpuriousRtxHostQueues'	: 'system.net.tcpext.spurious_rtx_host_queues',
                'BusyPollRxPackets'	        : 'system.net.tcpext.busy_poll_rx_packets'
            }

            for key, metric in tcpext_metrics_name.iteritems():
                if key in tcpext_metrics:
                    self.rate(metric, self._parse_value(tcpext_metrics[key]))

            assert(udp_metrics['IpExt:'] == 'IpExt:')

            ipext_metrics_name = {
                'InNoRoutes'	    : 'system.net.ipext.in_no_routes',
                'InTruncatedPkts'	: 'system.net.ipext.in_truncated_pkts',
                'InMcastPkts'	    : 'system.net.ipext.in_mcast_pkts',
                'OutMcastPkts'	    : 'system.net.ipext.out_mcast_pkts',
                'InBcastPkts'	    : 'system.net.ipext.in_bcast_pkts',
                'OutBcastPkts'	    : 'system.net.ipext.out_bcast_pkts',
                'InOctets'	        : 'system.net.ipext.in_octets',
                'OutOctets'	        : 'system.net.ipext.out_octets',
                'InMcastOctets'	    : 'system.net.ipext.in_mcast_octets',
                'OutMcastOctets'	: 'system.net.ipext.out_mcast_octets',
                'InBcastOctets'	    : 'system.net.ipext.in_bcast_octets',
                'OutBcastOctets'	: 'system.net.ipext.out_bast_octets',
                'InCsumErrors'	    : 'system.net.ipext.in_csum_errors',
                'InNoECTPkts'	    : 'system.net.ipext.in_no_ect_pkts',
                'InECT1Pkts'	    : 'system.net.ipext.in_ect_1_pkts',
                'InECT0Pkts'	    : 'system.net.ipext.in_ect0_pkts',
                'InCEPkts'	        : 'system.net.ipext.in_ce_pkts'
            }
            for key, metric in ipext_metrics_name.iteritems():
                if key in ipext_metrics:
                    self.rate(metric, self._parse_value(ipext_metrics[key]))

        except IOError:
            # On Openshift, /proc/net/netstat is only readable by root
            self.log.debug("Unable to read %s.", proc_netstat_path)

    # Parse the output of the command that retrieves the connection state (either `ss` or `netstat`)
    # Returns a dict metric_name -> value
    def _parse_linux_cx_state(self, lines, tcp_states, state_col, ip_version=None):
        metrics = dict.fromkeys(self.CX_STATE_GAUGE.values(), 0)
        for l in lines:
            cols = l.split()
            if cols[0].startswith('tcp'):
                protocol = "tcp{0}".format(ip_version) if ip_version else ("tcp4", "tcp6")[cols[0] == "tcp6"]
                if cols[state_col] in tcp_states:
                    metric = self.CX_STATE_GAUGE[protocol, tcp_states[cols[state_col]]]
                    metrics[metric] += 1
            elif cols[0].startswith('udp'):
                protocol = "udp{0}".format(ip_version) if ip_version else ("udp4", "udp6")[cols[0] == "udp6"]
                metric = self.CX_STATE_GAUGE[protocol, 'connections']
                metrics[metric] += 1

        return metrics

    def _check_bsd(self, instance):
        netstat_flags = ['-i', '-b']

        # FreeBSD's netstat truncates device names unless you pass '-W'
        if Platform.is_freebsd():
            netstat_flags.append('-W')

        try:
            output, _, _ = get_subprocess_output(["netstat"] + netstat_flags, self.log)
            lines = output.splitlines()
            # Name  Mtu   Network       Address            Ipkts Ierrs     Ibytes    Opkts Oerrs     Obytes  Coll
            # lo0   16384 <Link#1>                        318258     0  428252203   318258     0  428252203     0
            # lo0   16384 localhost   fe80:1::1           318258     -  428252203   318258     -  428252203     -
            # lo0   16384 127           localhost         318258     -  428252203   318258     -  428252203     -
            # lo0   16384 localhost   ::1                 318258     -  428252203   318258     -  428252203     -
            # gif0* 1280  <Link#2>                             0     0          0        0     0          0     0
            # stf0* 1280  <Link#3>                             0     0          0        0     0          0     0
            # en0   1500  <Link#4>    04:0c:ce:db:4e:fa 20801309     0 13835457425 15149389     0 11508790198     0
            # en0   1500  seneca.loca fe80:4::60c:ceff: 20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  192.168.1     192.168.1.63    20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
            # p2p0  2304  <Link#5>    06:0c:ce:db:4e:fa        0     0          0        0     0          0     0
            # ham0  1404  <Link#6>    7a:79:05:4d:bf:f5    30100     0    6815204    18742     0    8494811     0
            # ham0  1404  5             5.77.191.245       30100     -    6815204    18742     -    8494811     -
            # ham0  1404  seneca.loca fe80:6::7879:5ff:    30100     -    6815204    18742     -    8494811     -
            # ham0  1404  2620:9b::54 2620:9b::54d:bff5    30100     -    6815204    18742     -    8494811     -

            headers = lines[0].split()

            # Given the irregular structure of the table above, better to parse from the end of each line
            # Verify headers first
            #          -7       -6       -5        -4       -3       -2        -1
            for h in ("Ipkts", "Ierrs", "Ibytes", "Opkts", "Oerrs", "Obytes", "Coll"):
                if h not in headers:
                    self.logger.error("%s not found in %s; cannot parse" % (h, headers))
                    return False

            current = None
            for l in lines[1:]:
                # Another header row, abort now, this is IPv6 land
                if "Name" in l:
                    break

                x = l.split()
                if len(x) == 0:
                    break

                iface = x[0]
                if iface.endswith("*"):
                    iface = iface[:-1]
                if iface == current:
                    # skip multiple lines of same interface
                    continue
                else:
                    current = iface

                # Filter inactive interfaces
                if self._parse_value(x[-5]) or self._parse_value(x[-2]):
                    iface = current
                    metrics = {
                        'bytes_rcvd': self._parse_value(x[-5]),
                        'bytes_sent': self._parse_value(x[-2]),
                        'packets_in.count': self._parse_value(x[-7]),
                        'packets_in.error': self._parse_value(x[-6]),
                        'packets_out.count': self._parse_value(x[-4]),
                        'packets_out.error':self._parse_value(x[-3]),
                    }
                    self._submit_devicemetrics(iface, metrics)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting connection stats.")


        try:
            netstat, _, _ = get_subprocess_output(["netstat", "-s", "-p" "tcp"], self.log)
            #3651535 packets sent
            #        972097 data packets (615753248 bytes)
            #        5009 data packets (2832232 bytes) retransmitted
            #        0 resends initiated by MTU discovery
            #        2086952 ack-only packets (471 delayed)
            #        0 URG only packets
            #        0 window probe packets
            #        310851 window update packets
            #        336829 control packets
            #        0 data packets sent after flow control
            #        3058232 checksummed in software
            #        3058232 segments (571218834 bytes) over IPv4
            #        0 segments (0 bytes) over IPv6
            #4807551 packets received
            #        1143534 acks (for 616095538 bytes)
            #        165400 duplicate acks
            #        ...

            self._submit_regexed_values(netstat, BSD_TCP_METRICS)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting TCP stats.")


    def _check_solaris(self, instance):
        # Can't get bytes sent and received via netstat
        # Default to kstat -p link:0:
        try:
            netstat, _, _ = get_subprocess_output(["kstat", "-p", "link:0:"], self.log)
            metrics_by_interface = self._parse_solaris_netstat(netstat)
            for interface, metrics in metrics_by_interface.iteritems():
                self._submit_devicemetrics(interface, metrics)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting kstat stats.")

        try:
            netstat, _, _ = get_subprocess_output(["netstat", "-s", "-P" "tcp"], self.log)
            # TCP: tcpRtoAlgorithm=     4 tcpRtoMin           =   200
            # tcpRtoMax           = 60000 tcpMaxConn          =    -1
            # tcpActiveOpens      =    57 tcpPassiveOpens     =    50
            # tcpAttemptFails     =     1 tcpEstabResets      =     0
            # tcpCurrEstab        =     0 tcpOutSegs          =   254
            # tcpOutDataSegs      =   995 tcpOutDataBytes     =1216733
            # tcpRetransSegs      =     0 tcpRetransBytes     =     0
            # tcpOutAck           =   185 tcpOutAckDelayed    =     4
            # ...
            self._submit_regexed_values(netstat, SOLARIS_TCP_METRICS)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting TCP stats.")


    def _parse_solaris_netstat(self, netstat_output):
        """
        Return a mapping of network metrics by interface. For example:
            { interface:
                {'bytes_sent': 0,
                  'bytes_rcvd': 0,
                  'bytes_rcvd': 0,
                  ...
                }
            }
        """
        # Here's an example of the netstat output:
        #
        # link:0:net0:brdcstrcv   527336
        # link:0:net0:brdcstxmt   1595
        # link:0:net0:class       net
        # link:0:net0:collisions  0
        # link:0:net0:crtime      16359935.2637943
        # link:0:net0:ierrors     0
        # link:0:net0:ifspeed     10000000000
        # link:0:net0:ipackets    682834
        # link:0:net0:ipackets64  682834
        # link:0:net0:link_duplex 0
        # link:0:net0:link_state  1
        # link:0:net0:multircv    0
        # link:0:net0:multixmt    1595
        # link:0:net0:norcvbuf    0
        # link:0:net0:noxmtbuf    0
        # link:0:net0:obytes      12820668
        # link:0:net0:obytes64    12820668
        # link:0:net0:oerrors     0
        # link:0:net0:opackets    105445
        # link:0:net0:opackets64  105445
        # link:0:net0:rbytes      113983614
        # link:0:net0:rbytes64    113983614
        # link:0:net0:snaptime    16834735.1607669
        # link:0:net0:unknowns    0
        # link:0:net0:zonename    53aa9b7e-48ba-4152-a52b-a6368c3d9e7c
        # link:0:net1:brdcstrcv   4947620
        # link:0:net1:brdcstxmt   1594
        # link:0:net1:class       net
        # link:0:net1:collisions  0
        # link:0:net1:crtime      16359935.2839167
        # link:0:net1:ierrors     0
        # link:0:net1:ifspeed     10000000000
        # link:0:net1:ipackets    4947620
        # link:0:net1:ipackets64  4947620
        # link:0:net1:link_duplex 0
        # link:0:net1:link_state  1
        # link:0:net1:multircv    0
        # link:0:net1:multixmt    1594
        # link:0:net1:norcvbuf    0
        # link:0:net1:noxmtbuf    0
        # link:0:net1:obytes      73324
        # link:0:net1:obytes64    73324
        # link:0:net1:oerrors     0
        # link:0:net1:opackets    1594
        # link:0:net1:opackets64  1594
        # link:0:net1:rbytes      304384894
        # link:0:net1:rbytes64    304384894
        # link:0:net1:snaptime    16834735.1613302
        # link:0:net1:unknowns    0
        # link:0:net1:zonename    53aa9b7e-48ba-4152-a52b-a6368c3d9e7c

        # A mapping of solaris names -> datadog names
        metric_by_solaris_name = {
            'rbytes64':'bytes_rcvd',
            'obytes64':'bytes_sent',
            'ipackets64':'packets_in.count',
            'ierrors':'packets_in.error',
            'opackets64':'packets_out.count',
            'oerrors':'packets_out.error',
        }

        lines = [l for l in netstat_output.splitlines() if len(l) > 0]

        metrics_by_interface = {}

        for l in lines:
            # Parse the metric & interface.
            cols = l.split()
            link, n, iface, name = cols[0].split(":")
            assert link == "link"

            # Get the datadog metric name.
            ddname = metric_by_solaris_name.get(name, None)
            if ddname is None:
                continue

            # Add it to this interface's list of metrics.
            metrics = metrics_by_interface.get(iface, {})
            metrics[ddname] = self._parse_value(cols[1])
            metrics_by_interface[iface] = metrics

        return metrics_by_interface

    def _check_psutil(self):
        """
        Gather metrics about connections states and interfaces counters
        using psutil facilities
        """
        if self._collect_cx_state:
            self._cx_state_psutil()

        self._cx_counters_psutil()

    def _cx_state_psutil(self):
        """
        Collect metrics about connections state using psutil
        """
        metrics = defaultdict(int)
        for conn in psutil.net_connections():
            protocol = self._parse_protocol_psutil(conn)
            status = self.TCP_STATES['psutil'].get(conn.status)
            metric = self.CX_STATE_GAUGE.get((protocol, status))
            if metric is None:
                self.log.warning('Metric not found for: %s,%s', protocol, status)
            else:
                metrics[metric] += 1

        for metric, value in metrics.iteritems():
            self.gauge(metric, value)

    def _cx_counters_psutil(self):
        """
        Collect metrics about interfaces counters using psutil
        """
        for iface, counters in psutil.net_io_counters(pernic=True).iteritems():
            metrics = {
                'bytes_rcvd': counters.bytes_recv,
                'bytes_sent': counters.bytes_sent,
                'packets_in.count': counters.packets_recv,
                'packets_in.error': counters.errin,
                'packets_out.count': counters.packets_sent,
                'packets_out.error': counters.errout,
            }
            self._submit_devicemetrics(iface, metrics)

    def _parse_protocol_psutil(self, conn):
        """
        Returns a string describing the protocol for the given connection
        in the form `tcp4`, 'udp4` as in `self.CX_STATE_GAUGE`
        """
        protocol = self.PSUTIL_TYPE_MAPPING.get(conn.type, '')
        family = self.PSUTIL_FAMILY_MAPPING.get(conn.family, '')
        return '{}{}'.format(protocol, family)
