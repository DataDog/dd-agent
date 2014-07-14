# std
import time

# project
from checks import AgentCheck

# 3rd party
import ntplib

DEFAULT_MIN_COLLECTION_INTERVAL = 20 # in seconds
DEFAULT_OFFSET_THRESHOLD = 600 # in seconds
DEFAULT_NTP_VERSION = 3
DEFAULT_TIMEOUT = 1 # in seconds
DEFAULT_HOST = "pool.ntp.org"
DEFAULT_PORT = "ntp"

class NtpCheck(AgentCheck):
    def check(self, instance):
        min_collection_interval = instance.get('min_collection_interval', DEFAULT_MIN_COLLECTION_INTERVAL)
        if not hasattr(self, "last_collection_time"):
            self.last_collection_time = 0
        else:
            if time.time() - self.last_collection_time < min_collection_interval:
                self.log.debug("Not running NTP Check as it ran less than {0}s ago".format(min_collection_interval))
                return

        offset_threshold = instance.get('offset_threshold', DEFAULT_OFFSET_THRESHOLD)
        try:
            offset_threshold = int(offset_threshold)
        except (TypeError, ValueError):
            raise Exception('Must specify an integer value for offset_threshold. Configured value is %s' % repr(offset_threshold))
        req_args = {
            'host':    instance.get('host', DEFAULT_HOST),
            'port':    instance.get('port', DEFAULT_PORT),
            'version': int(instance.get('version', DEFAULT_NTP_VERSION)),
            'timeout': float(instance.get('timeout', DEFAULT_TIMEOUT)),
        }
        try:
            ntp_stats = ntplib.NTPClient().request(**req_args)
        except ntplib.NTPException:
            self.log.warning("Could not connect to NTP Server")
            status  = AgentCheck.UNKNOWN
            ntp_ts = None
        else:
            self.last_collection_time = time.time()
            ntp_offset = ntp_stats.offset
            # Use the ntp server's timestamp for the time of the result in
            # case the agent host's clock is messed up.
            ntp_ts = ntp_stats.recv_time

            if ntp_offset > offset_threshold:
                status = AgentCheck.CRITICAL
            else:
                status = AgentCheck.OK

        self.service_check('ntp.in_sync', status, timestamp=ntp_ts)
        self.gauge('ntp.offset', ntp_offset, timestamp=ntp_ts)
