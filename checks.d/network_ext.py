"""
Collects extended network metrics.
"""
# stdlib
import re

# project
from checks import AgentCheck
from utils.platform import Platform
from utils.subprocess_output import (
    get_subprocess_output,
    SubprocessOutputEmptyError,
)

GAUGE = AgentCheck.gauge
MONOTONIC_COUNT = AgentCheck.monotonic_count


class NetworkExt(AgentCheck):

    SOURCE_TYPE_NAME = 'system'

    SNMP_METRICS = {
        'Tcp': {
            # The algorithm used to determine the timeout value used for
            # retransmitting unacknowledged octets.
            'RtoAlgorithm': ('system.net.tcpx.rto_algorithm', GAUGE),
            # The minimum value permitted by a TCP implementation for the
            # retransmission timeout, measured in milliseconds. More
            # refined semantics for objects of this type depend upon the
            # algorithm used to determine the retransmission timeout. In
            # particular, when the timeout algorithm is ``rsre '' (3), an
            # object of this type has the semantics of the LBOUND quantity
            # described in RFC 793.
            'RtoMin': ('system.net.tcpx.rto_min', GAUGE),
            # The maximum value permitted by a TCP implementation for the
            # retransmission timeout, measured in milliseconds. More
            # refined semantics for objects of this type depend upon the
            # algorithm used to determine the retransmission timeout. In
            # particular, when the timeout algorithm is ``rsre'' (3), an
            # object of this type has the semantics of the UBOUND quantity
            # described in RFC 793.
            'RtoMax': ('system.net.tcpx.rto_max', GAUGE),
            # The limit on the total number of TCP connections the entity
            # can support. In entities where the maximum number of
            # connections is dynamic, this object should contain the value
            # -1.
            'MaxConn': ('system.net.tcpx.max_conn', GAUGE),
            # The number of times TCP connections have made a direct
            # transition to the SYN-SENT state from the CLOSED state.
            'ActiveOpens': ('system.net.tcpx.active_opens', MONOTONIC_COUNT),
            # The number of times TCP connections have made a direct
            # transition to the SYN-RCVD state from the LISTEN state.
            'PassiveOpens': ('system.net.tcpx.passive_opens', MONOTONIC_COUNT),
            # The number of times TCP connections have made a direct
            # transition to the CLOSED state from either the SYN-SENT state
            # or the SYN-RCVD state, plus the number of times TCP
            # connections have made a direct transition to the LISTEN state
            # from the SYN-RCVD state.
            'AttemptFails': ('system.net.tcpx.attempt_fails', MONOTONIC_COUNT),
            # The number of times TCP connections have made a direct
            # transition to the CLOSED state from either the ESTABLISHED
            # state or the CLOSE-WAIT state.
            'EstabResets': ('system.net.tcpx.estab_resets', MONOTONIC_COUNT)}}

    NETSTAT_METRICS = {
        'TcpExt': {
            # An application wasn't able to accept a connection fast enough, so
            # the kernel couldn't store an entry in the queue for this
            # connection. Instead of dropping it, it sent a cookie to the
            # client.
            'SyncookiesSent': ('system.net.tcpx.syncookies_sent', MONOTONIC_COUNT),
            # After sending a cookie, it came back to us and passed the check.
            'SyncookiesRecv': ('system.net.tcpx.syncookies_recv', MONOTONIC_COUNT),
            # After sending a cookie, it came back to us but looked invalid.
            'SyncookiesFailed': ('system.net.tcpx.syncookies_failed', MONOTONIC_COUNT),
            # ??
            'EmbryonicRsts': ('system.net.tcpx.embryonic_rsts', MONOTONIC_COUNT),
            # ??
            'PruneCalled': ('system.net.tcpx.prune_called', MONOTONIC_COUNT),
            # If the kernel is really really desperate and cannot give more
            # memory to this socket even after dropping the ofo queue, it will
            # simply discard the packet it received. This is Really Bad.
            'RcvPruned': ('system.net.tcpx.rcv_pruned', MONOTONIC_COUNT),
            # When a socket is using too much memory (rmem), the kernel will
            # first discard any out-of-order packet that has been queued (with
            # SACK).
            'OfoPruned': ('system.net.tcpx.ofo_pruned', MONOTONIC_COUNT),

            # ??
            # 'OutOfWindowIcmps': 'system.net.tcpx.X',
            # 'LockDroppedIcmps': 'system.net.tcpx.X',
            # 'ArpFilter': 'system.net.tcpx.X',

            'TW': ('system.net.tcpx.time_waited', MONOTONIC_COUNT),
            'TWRecycled': ('system.net.tcpx.time_wait_recycled', MONOTONIC_COUNT),
            'TWKilled': ('system.net.tcpx.time_wait_killed', MONOTONIC_COUNT),

            # ??
            # 'PAWSPassive': 'system.net.tcpx.X',
            # 'PAWSActive': 'system.net.tcpx.X',
            # 'PAWSEstab': 'system.net.tcpx.X',

            # We waited for another packet to send an ACK, but didn't see any,
            # so a timer ended up sending a delayed ACK.
            'DelayedACKs': ('system.net.tcpx.delayed_acks', MONOTONIC_COUNT),
            # We wanted to send a delayed ACK but failed because the socket was
            # locked. So the timer was reset.
            'DelayedACKLocked': ('system.net.tcpx.delayed_ack_locked', MONOTONIC_COUNT),
            # We sent a delayed and duplicated ACK because the remote peer
            # retransmitted a packet, thinking that it didn't get to us.
            'DelayedACKLost': ('system.net.tcpx.delayed_ack_lost', MONOTONIC_COUNT),
            # We completed a 3WHS but couldn't put the socket on the accept
            # queue, so we had to discard the connection.
            'ListenOverflows': ('system.net.tcpx.listen_overflows', MONOTONIC_COUNT),
            # We couldn't accept a connection because one of: we had no route
            # to the destination, we failed to allocate a socket, we failed to
            # allocate a new local port bind bucket. Note: this counter also
            # include all the increments made to ListenOverflows
            'ListenDrops': ('system.net.tcpx.listen_drops', MONOTONIC_COUNT),

            # ??
            # 'TCPPrequeued': 'system.net.tcpx.X',
            # 'TCPDirectCopyFromBacklog': 'system.net.tcpx.X',
            # 'TCPDirectCopyFromPrequeue': 'system.net.tcpx.X',
            # 'TCPPrequeueDropped': 'system.net.tcpx.X',
            # 'TCPHPHits': 'system.net.tcpx.X',
            # 'TCPHPHitsToUser': 'system.net.tcpx.X',
            # 'TCPPureAcks': 'system.net.tcpx.X',
            # 'TCPHPAcks': 'system.net.tcpx.X',

            # A packet was lost and we recovered after a fast retransmit.
            'TCPRenoRecovery': ('system.net.tcpx.reno_recovery', MONOTONIC_COUNT),
            # A packet was lost and we recovered by using selective acknowledgements.
            'TCPSackRecovery': ('system.net.tcpx.sack_recovery', MONOTONIC_COUNT),
            # ??
            'TCPSACKReneging': ('system.net.tcpx.sack_reneging', MONOTONIC_COUNT),
            # We detected re-ordering using FACK (Forward ACK -- the highest
            # sequence number known to have been received by the peer when
            # using SACK -- FACK is used during congestion control).
            'TCPFACKReorder': ('system.net.tcpx.fack_reorder', MONOTONIC_COUNT),
            # We detected re-ordering using SACK.
            'TCPSACKReorder': ('system.net.tcpx.sack_reorder', MONOTONIC_COUNT),
            # We detected re-ordering using fast retransmit.
            'TCPRenoReorder': ('system.net.tcpx.reno_reorder', MONOTONIC_COUNT),
            # We detected re-ordering using the timestamp option.
            'TCPTSReorder': ('system.net.tcpx.ts_reorder', MONOTONIC_COUNT),
            # We detected some erroneous retransmits and undid our CWND reduction.
            'TCPFullUndo': ('system.net.tcpx.full_undo', MONOTONIC_COUNT),
            # We detected some erroneous retransmits, a partial ACK arrived
            # while we were fast retransmitting, so we were able to partially
            # undo some of our CWND reduction.
            'TCPPartialUndo': ('system.net.tcpx.partial_undo', MONOTONIC_COUNT),
            # We detected some erroneous retransmits, a D-SACK arrived and
            # ACK'ed all the retransmitted data, so we undid our CWND
            # reduction.
            'TCPDSACKUndo': ('system.net.tcpx.sack_undo', MONOTONIC_COUNT),
            # We detected some erroneous retransmits, a partial ACK arrived, so
            # we undid our CWND reduction.
            'TCPLossUndo': ('system.net.tcpx.loss_undo', MONOTONIC_COUNT),

            # ??
            # 'TCPLostRetransmit': 'system.net.tcpx.X',
            # 'TCPRenoFailures': 'system.net.tcpx.X',
            # 'TCPSackFailures': 'system.net.tcpx.X',
            # 'TCPLossFailures': 'system.net.tcpx.X',
            # 'TCPFastRetrans': 'system.net.tcpx.X',
            # 'TCPForwardRetrans': 'system.net.tcpx.X',
            # 'TCPSlowStartRetrans': 'system.net.tcpx.X',
            # 'TCPTimeouts': 'system.net.tcpx.X',
            # 'TCPLossProbes': 'system.net.tcpx.X',
            # 'TCPLossProbeRecovery': 'system.net.tcpx.X',
            # 'TCPRenoRecoveryFail': 'system.net.tcpx.X',
            # 'TCPSackRecoveryFail': 'system.net.tcpx.X',
            # 'TCPSchedulerFailed': 'system.net.tcpx.X',
            # 'TCPRcvCollapsed': 'system.net.tcpx.X',
            # 'TCPDSACKOldSent': 'system.net.tcpx.X',
            # 'TCPDSACKOfoSent': 'system.net.tcpx.X',
            # 'TCPDSACKRecv': 'system.net.tcpx.X',
            # 'TCPDSACKOfoRecv': 'system.net.tcpx.X',

            # We were in FIN_WAIT1 yet we received a data packet with a
            # sequence number that's beyond the last one for this connection,
            # so we RST'ed.
            'TCPAbortOnData': ('system.net.tcpx.abort_on_data', MONOTONIC_COUNT),
            # We received data but the user has closed the socket, so we have
            # no wait of handing it to them, so we RST'ed.
            'TCPAbortOnClose': ('system.net.tcpx.abort_on_close', MONOTONIC_COUNT),
            # This is Really Bad. It happens when there are too many orphaned
            # sockets (not attached a FD) and the kernel has to drop a
            # connection. Sometimes it will send a reset to the peer, sometimes
            # it wont.
            'TCPAbortOnMemory': ('system.net.tcpx.abort_on_memory', MONOTONIC_COUNT),
            # The connection timed out really hard.
            'TCPAbortOnTimeout': ('system.net.tcpx.abort_on_timeout', MONOTONIC_COUNT),
            # We killed a socket that was closed by the application and
            # lingered around for long enough.
            'TCPAbortOnLinger': ('system.net.tcpx.abort_on_linger', MONOTONIC_COUNT),
            # We tried to send a reset, probably during one of teh TCPABort*
            # situations above, but we failed e.g. because we couldn't allocate
            # enough memory (very bad).
            'TCPAbortFailed': ('system.net.tcpx.abort_failed', MONOTONIC_COUNT),
            # Number of times a socket was put in "memory pressure" due to a
            # non fatal memory allocation failure (reduces the send buffer size
            # etc).
            'TCPMemoryPressures': ('system.net.tcpx.memory_pressures', MONOTONIC_COUNT),
            # We got a completely invalid SACK block and discarded it.
            'TCPSACKDiscard': ('system.net.tcpx.sack_discard', MONOTONIC_COUNT),
            # We got a duplicate SACK while retransmitting so we discarded it.
            'TCPDSACKIgnoredOld': ('system.net.tcpx.sack_ignored_old', MONOTONIC_COUNT),
            # We got a duplicate SACK and discarded it.
            'TCPDSACKIgnoredNoUndo': ('system.net.tcpx.sack_ignored_no_undo', MONOTONIC_COUNT),

            # ??
            # 'TCPSpuriousRTOs': 'system.net.tcpx.X',
            # 'TCPMD5NotFound': 'system.net.tcpx.X',
            # 'TCPMD5Unexpected': 'system.net.tcpx.X',
            # 'TCPSackShifted': 'system.net.tcpx.X',
            # 'TCPSackMerged': 'system.net.tcpx.X',
            # 'TCPSackShiftFallback': 'system.net.tcpx.X',

            # We received something but had to drop it because the socket's
            # receive queue was full.
            'TCPBacklogDrop': ('system.net.tcpx.backlog_drop', MONOTONIC_COUNT),

            # ??
            # 'TCPMinTTLDrop': 'system.net.tcpx.X',
            # 'TCPDeferAcceptDrop': 'system.net.tcpx.X',
            # 'IPReversePathFilter': 'system.net.tcpx.X',
            # 'TCPTimeWaitOverflow': 'system.net.tcpx.X',
            # 'TCPReqQFullDoCookies': 'system.net.tcpx.X',
            # 'TCPReqQFullDrop': 'system.net.tcpx.X',
            # 'TCPRetransFail': 'system.net.tcpx.X',
            # 'TCPRcvCoalesce': 'system.net.tcpx.X',
            # 'TCPOFOQueue': 'system.net.tcpx.X',
            # 'TCPOFODrop': 'system.net.tcpx.X',
            # 'TCPOFOMerge': 'system.net.tcpx.X',
            # 'TCPChallengeACK': 'system.net.tcpx.X',
            # 'TCPSYNChallenge': 'system.net.tcpx.X',
            # 'TCPFastOpenActive': 'system.net.tcpx.X',
            # 'TCPFastOpenPassive': 'system.net.tcpx.X',
            # 'TCPFastOpenPassiveFail': 'system.net.tcpx.X',
            # 'TCPFastOpenListenOverflow': 'system.net.tcpx.X',
            # 'TCPFastOpenCookieReqd': 'system.net.tcpx.X',
            # 'TCPSpuriousRtxHostQueues': 'system.net.tcpx.X',
            # 'BusyPollRxPackets': 'system.net.tcpx.X'
            }}

    def check(self, instance):
        if instance is None:
            instance = {}

        proc_location = self.agentConfig.get('procfs_path', '/proc').rstrip('/')
        self.parse_proc_net_netstat(self.read_lines("{}/net/netstat".format(proc_location)))
        self.parse_proc_net_snmp(self.read_lines("{}/net/snmp".format(proc_location)))
        self.parse_proc_net_udp(self.read_lines("{}/net/udp".format(proc_location)))
        self.parse_proc_net_udp(self.read_lines("{}/net/udp6".format(proc_location)), ipv6=True)

    def parse_proc_net_netstat(self, lines):
        return self.parse_proto_metrics(lines, self.NETSTAT_METRICS)

    def parse_proc_net_snmp(self, lines):
        return self.parse_proto_metrics(lines, self.SNMP_METRICS)

    def parse_proc_net_udp(self, lines, ipv6=False):
        columns = lines[0].strip().split()
        for line in lines[1:len(lines)]:
            parts = line.strip().split()
            values = dict(zip(columns, parts[:4] + parts[4].split(':') + parts[5].split(':') + parts[6:]))
            drops = int(values.get('drops', 0))
            proto = "udpx"
            if ipv6:
                proto = "udpx6"
            self.monotonic_count('system.net.%s.drops' % proto, drops, tags=["inode:%s" % values.get('inode', 'unknown')])
        return None

    def read_lines(self, path):
        with open(path, 'r') as proc:
            lines = proc.readlines()
        return lines

    def parse_proto_metrics(self, lines, proto_map):
        for k, t in proto_map.iteritems():
            proto_lines = [line for line in lines if line.startswith(k + ':')]
            columns = proto_lines[0].strip().split()
            values = proto_lines[1].strip().split()
            metrics = dict(zip(columns, values))
            for k, v in metrics.iteritems():
                tup = t.get(k, None)
                if tup:
                    func = {
                        MONOTONIC_COUNT: self.monotonic_count,
                        GAUGE: self.gauge}[tup[1]]
                    func(tup[0], int(v))
        return None
