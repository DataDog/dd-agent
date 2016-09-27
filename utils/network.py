"""
Collects extended network metrics.
"""
# stdlib
import re

# project
from checks import AgentCheck

GAUGE = AgentCheck.gauge
MONOTONIC_COUNT = AgentCheck.monotonic_count

SNMP_METRICS = {
    'Tcp': {
        # The algorithm used to determine the timeout value used for
        # retransmitting unacknowledged octets.
        'RtoAlgorithm': ('tcpx.rto_algorithm', GAUGE),
        # The minimum value permitted by a TCP implementation for the
        # retransmission timeout, measured in milliseconds. More
        # refined semantics for objects of this type depend upon the
        # algorithm used to determine the retransmission timeout. In
        # particular, when the timeout algorithm is ``rsre '' (3), an
        # object of this type has the semantics of the LBOUND quantity
        # described in RFC 793.
        'RtoMin': ('tcpx.rto_min', GAUGE),
        # The maximum value permitted by a TCP implementation for the
        # retransmission timeout, measured in milliseconds. More
        # refined semantics for objects of this type depend upon the
        # algorithm used to determine the retransmission timeout. In
        # particular, when the timeout algorithm is ``rsre'' (3), an
        # object of this type has the semantics of the UBOUND quantity
        # described in RFC 793.
        'RtoMax': ('tcpx.rto_max', GAUGE),
        # The limit on the total number of TCP connections the entity
        # can support. In entities where the maximum number of
        # connections is dynamic, this object should contain the value
        # -1.
        'MaxConn': ('tcpx.max_conn', GAUGE),
        # The number of times TCP connections have made a direct
        # transition to the SYN-SENT state from the CLOSED state.
        'ActiveOpens': ('tcpx.active_opens', MONOTONIC_COUNT),
        # The number of times TCP connections have made a direct
        # transition to the SYN-RCVD state from the LISTEN state.
        'PassiveOpens': ('tcpx.passive_opens', MONOTONIC_COUNT),
        # The number of times TCP connections have made a direct
        # transition to the CLOSED state from either the SYN-SENT state
        # or the SYN-RCVD state, plus the number of times TCP
        # connections have made a direct transition to the LISTEN state
        # from the SYN-RCVD state.
        'AttemptFails': ('tcpx.attempt_fails', MONOTONIC_COUNT),
        # The number of times TCP connections have made a direct
        # transition to the CLOSED state from either the ESTABLISHED
        # state or the CLOSE-WAIT state.
        'EstabResets': ('tcpx.estab_resets', MONOTONIC_COUNT)}}

NETSTAT_METRICS = {
    'TcpExt': {
        # An application wasn't able to accept a connection fast enough, so
        # the kernel couldn't store an entry in the queue for this
        # connection. Instead of dropping it, it sent a cookie to the
        # client.
        'SyncookiesSent': ('tcpx.syncookies_sent', MONOTONIC_COUNT),
        # After sending a cookie, it came back to us and passed the check.
        'SyncookiesRecv': ('tcpx.syncookies_recv', MONOTONIC_COUNT),
        # After sending a cookie, it came back to us but looked invalid.
        'SyncookiesFailed': ('tcpx.syncookies_failed', MONOTONIC_COUNT),
        # ??
        'EmbryonicRsts': ('tcpx.embryonic_rsts', MONOTONIC_COUNT),
        # ??
        'PruneCalled': ('tcpx.prune_called', MONOTONIC_COUNT),
        # If the kernel is really really desperate and cannot give more
        # memory to this socket even after dropping the ofo queue, it will
        # simply discard the packet it received. This is Really Bad.
        'RcvPruned': ('tcpx.rcv_pruned', MONOTONIC_COUNT),
        # When a socket is using too much memory (rmem), the kernel will
        # first discard any out-of-order packet that has been queued (with
        # SACK).
        'OfoPruned': ('tcpx.ofo_pruned', MONOTONIC_COUNT),

        # ??
        # 'OutOfWindowIcmps': 'tcpx.X',
        # 'LockDroppedIcmps': 'tcpx.X',
        # 'ArpFilter': 'tcpx.X',

        'TW': ('tcpx.time_waited', MONOTONIC_COUNT),
        'TWRecycled': ('tcpx.time_wait_recycled', MONOTONIC_COUNT),
        'TWKilled': ('tcpx.time_wait_killed', MONOTONIC_COUNT),

        # ??
        # 'PAWSPassive': 'tcpx.X',
        # 'PAWSActive': 'tcpx.X',
        # 'PAWSEstab': 'tcpx.X',

        # We waited for another packet to send an ACK, but didn't see any,
        # so a timer ended up sending a delayed ACK.
        'DelayedACKs': ('tcpx.delayed_acks', MONOTONIC_COUNT),
        # We wanted to send a delayed ACK but failed because the socket was
        # locked. So the timer was reset.
        'DelayedACKLocked': ('tcpx.delayed_ack_locked', MONOTONIC_COUNT),
        # We sent a delayed and duplicated ACK because the remote peer
        # retransmitted a packet, thinking that it didn't get to us.
        'DelayedACKLost': ('tcpx.delayed_ack_lost', MONOTONIC_COUNT),
        # We completed a 3WHS but couldn't put the socket on the accept
        # queue, so we had to discard the connection.
        'ListenOverflows': ('tcpx.listen_overflows', MONOTONIC_COUNT),
        # We couldn't accept a connection because one of: we had no route
        # to the destination, we failed to allocate a socket, we failed to
        # allocate a new local port bind bucket. Note: this counter also
        # include all the increments made to ListenOverflows
        'ListenDrops': ('tcpx.listen_drops', MONOTONIC_COUNT),

        # ??
        # 'TCPPrequeued': 'tcpx.X',
        # 'TCPDirectCopyFromBacklog': 'tcpx.X',
        # 'TCPDirectCopyFromPrequeue': 'tcpx.X',
        # 'TCPPrequeueDropped': 'tcpx.X',
        # 'TCPHPHits': 'tcpx.X',
        # 'TCPHPHitsToUser': 'tcpx.X',
        # 'TCPPureAcks': 'tcpx.X',
        # 'TCPHPAcks': 'tcpx.X',

        # A packet was lost and we recovered after a fast retransmit.
        'TCPRenoRecovery': ('tcpx.reno_recovery', MONOTONIC_COUNT),
        # A packet was lost and we recovered by using selective acknowledgements.
        'TCPSackRecovery': ('tcpx.sack_recovery', MONOTONIC_COUNT),
        # ??
        'TCPSACKReneging': ('tcpx.sack_reneging', MONOTONIC_COUNT),
        # We detected re-ordering using FACK (Forward ACK -- the highest
        # sequence number known to have been received by the peer when
        # using SACK -- FACK is used during congestion control).
        'TCPFACKReorder': ('tcpx.fack_reorder', MONOTONIC_COUNT),
        # We detected re-ordering using SACK.
        'TCPSACKReorder': ('tcpx.sack_reorder', MONOTONIC_COUNT),
        # We detected re-ordering using fast retransmit.
        'TCPRenoReorder': ('tcpx.reno_reorder', MONOTONIC_COUNT),
        # We detected re-ordering using the timestamp option.
        'TCPTSReorder': ('tcpx.ts_reorder', MONOTONIC_COUNT),
        # We detected some erroneous retransmits and undid our CWND reduction.
        'TCPFullUndo': ('tcpx.full_undo', MONOTONIC_COUNT),
        # We detected some erroneous retransmits, a partial ACK arrived
        # while we were fast retransmitting, so we were able to partially
        # undo some of our CWND reduction.
        'TCPPartialUndo': ('tcpx.partial_undo', MONOTONIC_COUNT),
        # We detected some erroneous retransmits, a D-SACK arrived and
        # ACK'ed all the retransmitted data, so we undid our CWND
        # reduction.
        'TCPDSACKUndo': ('tcpx.sack_undo', MONOTONIC_COUNT),
        # We detected some erroneous retransmits, a partial ACK arrived, so
        # we undid our CWND reduction.
        'TCPLossUndo': ('tcpx.loss_undo', MONOTONIC_COUNT),

        # ??
        # 'TCPLostRetransmit': 'tcpx.X',
        # 'TCPRenoFailures': 'tcpx.X',
        # 'TCPSackFailures': 'tcpx.X',
        # 'TCPLossFailures': 'tcpx.X',
        # 'TCPFastRetrans': 'tcpx.X',
        # 'TCPForwardRetrans': 'tcpx.X',
        # 'TCPSlowStartRetrans': 'tcpx.X',
        # 'TCPTimeouts': 'tcpx.X',
        # 'TCPLossProbes': 'tcpx.X',
        # 'TCPLossProbeRecovery': 'tcpx.X',
        # 'TCPRenoRecoveryFail': 'tcpx.X',
        # 'TCPSackRecoveryFail': 'tcpx.X',
        # 'TCPSchedulerFailed': 'tcpx.X',
        # 'TCPRcvCollapsed': 'tcpx.X',
        # 'TCPDSACKOldSent': 'tcpx.X',
        # 'TCPDSACKOfoSent': 'tcpx.X',
        # 'TCPDSACKRecv': 'tcpx.X',
        # 'TCPDSACKOfoRecv': 'tcpx.X',

        # We were in FIN_WAIT1 yet we received a data packet with a
        # sequence number that's beyond the last one for this connection,
        # so we RST'ed.
        'TCPAbortOnData': ('tcpx.abort_on_data', MONOTONIC_COUNT),
        # We received data but the user has closed the socket, so we have
        # no wait of handing it to them, so we RST'ed.
        'TCPAbortOnClose': ('tcpx.abort_on_close', MONOTONIC_COUNT),
        # This is Really Bad. It happens when there are too many orphaned
        # sockets (not attached a FD) and the kernel has to drop a
        # connection. Sometimes it will send a reset to the peer, sometimes
        # it wont.
        'TCPAbortOnMemory': ('tcpx.abort_on_memory', MONOTONIC_COUNT),
        # The connection timed out really hard.
        'TCPAbortOnTimeout': ('tcpx.abort_on_timeout', MONOTONIC_COUNT),
        # We killed a socket that was closed by the application and
        # lingered around for long enough.
        'TCPAbortOnLinger': ('tcpx.abort_on_linger', MONOTONIC_COUNT),
        # We tried to send a reset, probably during one of teh TCPABort*
        # situations above, but we failed e.g. because we couldn't allocate
        # enough memory (very bad).
        'TCPAbortFailed': ('tcpx.abort_failed', MONOTONIC_COUNT),
        # Number of times a socket was put in "memory pressure" due to a
        # non fatal memory allocation failure (reduces the send buffer size
        # etc).
        'TCPMemoryPressures': ('tcpx.memory_pressures', MONOTONIC_COUNT),
        # We got a completely invalid SACK block and discarded it.
        'TCPSACKDiscard': ('tcpx.sack_discard', MONOTONIC_COUNT),
        # We got a duplicate SACK while retransmitting so we discarded it.
        'TCPDSACKIgnoredOld': ('tcpx.sack_ignored_old', MONOTONIC_COUNT),
        # We got a duplicate SACK and discarded it.
        'TCPDSACKIgnoredNoUndo': ('tcpx.sack_ignored_no_undo', MONOTONIC_COUNT),

        # ??
        # 'TCPSpuriousRTOs': 'tcpx.X',
        # 'TCPMD5NotFound': 'tcpx.X',
        # 'TCPMD5Unexpected': 'tcpx.X',
        # 'TCPSackShifted': 'tcpx.X',
        # 'TCPSackMerged': 'tcpx.X',
        # 'TCPSackShiftFallback': 'tcpx.X',

        # We received something but had to drop it because the socket's
        # receive queue was full.
        'TCPBacklogDrop': ('tcpx.backlog_drop', MONOTONIC_COUNT),

        # ??
        # 'TCPMinTTLDrop': 'tcpx.X',
        # 'TCPDeferAcceptDrop': 'tcpx.X',
        # 'IPReversePathFilter': 'tcpx.X',
        # 'TCPTimeWaitOverflow': 'tcpx.X',
        # 'TCPReqQFullDoCookies': 'tcpx.X',
        # 'TCPReqQFullDrop': 'tcpx.X',
        # 'TCPRetransFail': 'tcpx.X',
        # 'TCPRcvCoalesce': 'tcpx.X',
        # 'TCPOFOQueue': 'tcpx.X',
        # 'TCPOFODrop': 'tcpx.X',
        # 'TCPOFOMerge': 'tcpx.X',
        # 'TCPChallengeACK': 'tcpx.X',
        # 'TCPSYNChallenge': 'tcpx.X',
        # 'TCPFastOpenActive': 'tcpx.X',
        # 'TCPFastOpenPassive': 'tcpx.X',
        # 'TCPFastOpenPassiveFail': 'tcpx.X',
        # 'TCPFastOpenListenOverflow': 'tcpx.X',
        # 'TCPFastOpenCookieReqd': 'tcpx.X',
        # 'TCPSpuriousRtxHostQueues': 'tcpx.X',
        # 'BusyPollRxPackets': 'tcpx.X'
        }}


def check_all(check, netns, proc_location, tags=[]):
    parse_proc_net_netstat(check, netns, read_lines("{}/net/netstat".format(proc_location)), tags)
    parse_proc_net_snmp(check, netns, read_lines("{}/net/snmp".format(proc_location)), tags)
    parse_proc_net_udp(check, netns, read_lines("{}/net/udp".format(proc_location)), tags=tags)
    parse_proc_net_udp(check, netns, read_lines("{}/net/udp6".format(proc_location)), tags=tags, ipv6=True)

def parse_proc_net_netstat(check, netns, lines, tags=[]):
    return parse_proto_metrics(check, netns, lines, NETSTAT_METRICS, tags)

def parse_proc_net_snmp(check, netns, lines, tags=[]):
    return parse_proto_metrics(check, netns, lines, SNMP_METRICS, tags)

def parse_proc_net_udp(check, netns, lines, ipv6=False, tags=[]):
    columns = lines[0].strip().split()
    for line in lines[1:len(lines)]:
        parts = line.strip().split()
        values = dict(zip(columns, parts[:4] + parts[4].split(':') + parts[5].split(':') + parts[6:]))
        drops = int(values.get('drops', 0))
        proto = "udpx"
        if ipv6:
            proto = "udpx6"
        check.monotonic_count('%s.%s.drops' % (netns, proto), drops, tags=tags + ["inode:%s" % values.get('inode', 'unknown')])
    return None

def parse_proto_metrics(check, netns, lines, proto_map, tags=[]):
    for k, t in proto_map.iteritems():
        proto_lines = [line for line in lines if line.startswith(k + ':')]
        columns = proto_lines[0].strip().split()
        values = proto_lines[1].strip().split()
        metrics = dict(zip(columns, values))
        for k, v in metrics.iteritems():
            tup = t.get(k, None)
            if tup:
                func = {
                    MONOTONIC_COUNT: check.monotonic_count,
                    GAUGE: check.gauge}[tup[1]]
                func("%s.%s" % (netns, tup[0]), int(v), tags=tags)
    return None

def read_lines(path):
    with open(path, 'r') as proc:
        lines = proc.readlines()
    return lines
