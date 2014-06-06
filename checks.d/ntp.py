from checks import AgentCheck
from checks.libs import ntplib

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
        ntp_offset = ntplib.NTPClient().request(**req_args).offset
        if ntp_offset > offset_threshold:
            status = AgentCheck.CRITICAL
        else:
            status = AgentCheck.OK
        self.service_check('ntp.in_sync', status)
