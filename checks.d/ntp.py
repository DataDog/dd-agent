from checks import AgentCheck
import ntplib

class NtpCheck(AgentCheck):
    def check(self, instance):
        offset_threshold = instance.get('offset_threshold', 600)
        try:
            offset_threshold = int(offset_threshold)
        except (TypeError, ValueError):
            raise Exception('Must specify an integer value for offset_threshold. Configured value is %s' % repr(offset_threshold))
        req_args = {
            'host':    instance.get('host', 'pool.ntp.org'),
            'port':    instance.get('port', 'ntp'),
            'version': int(instance.get('version', 3)),
            'timeout': float(instance.get('timeout', 5)),
        }
        ntp_stats = ntplib.NTPClient().request(**req_args)
        ntp_offset = ntp_stats.offset

        # Use the ntp server's timestamp for the time of the result in
        # case the agent host's clock is messed up.
        ntp_ts = ntp_stats.recv_time

        if ntp_offset > offset_threshold:
            status = AgentCheck.CRITICAL
        else:
            status = AgentCheck.OK
        self.service_check('ntp.in_sync', status, timestamp=ntp_ts)
