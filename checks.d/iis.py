'''
Check the performance counters from IIS
'''
from checks import AgentCheck

class IIS(AgentCheck):
    METRICS = [
        ('iis.uptime', 'gauge', 'ServiceUptime'),

        # Network
        ('iis.net.bytes_sent', 'gauge', 'BytesSentPerSec'),
        ('iis.net.bytes_rcvd', 'gauge', 'BytesReceivedPerSec'),
        ('iis.net.bytes_total', 'gauge', 'BytesTotalPerSec'),
        ('iis.net.num_connections', 'gauge', 'CurrentConnections'),
        ('iis.net.files_sent', 'gauge', 'FilesSentPerSec'),
        ('iis.net.files_received', 'gauge', 'FilesReceivedPerSec'),
        ('iis.net.connection_attempts', 'gauge', 'ConnectionAttemptsPerSec'),

        # HTTP Methods
        ('iis.httpd_request_method.get', 'gauge', 'GetRequestsPerSec'),
        ('iis.httpd_request_method.post', 'gauge', 'PostRequestsPerSec'),
        ('iis.httpd_request_method.head', 'gauge', 'HeadRequestsPerSec'),
        ('iis.httpd_request_method.put', 'gauge', 'PutRequestsPerSec'),
        ('iis.httpd_request_method.delete', 'gauge', 'DeleteRequestsPerSec'),
        ('iis.httpd_request_method.options', 'gauge', 'OptionsRequestsPerSec'),
        ('iis.httpd_request_method.trace', 'gauge', 'TraceRequestsPerSec'),

        # Errors
        ('iis.errors.net_found', 'gauge', 'NotFoundErrorsPerSec'),
        ('iis.errors.locked', 'gauge', 'LockedErrorsPerSec'),

        # Users
        ('iis.users.anon', 'gauge', 'AnonymousUsersPerSec'),
        ('iis.users.nonanon', 'gauge', 'NonAnonymousUsersPerSec'),

        # Requests
        ('iis.requests.cgi', 'gauge', 'CGIRequestsPerSec'),
        ('iis.requests.isapi', 'gauge', 'ISAPIExtensionRequestsPerSec'),
    ]

    def check(self, instance):
        try:
            import wmi
        except ImportError:
            self.log.error("Unable to import 'wmi' module")
            return

        # Connect to the WMI provider
        host = instance.get('host', None)
        user = instance.get('username', None)
        password = instance.get('password', None)
        tags = instance.get('tags', None)
        w = wmi.WMI(host, user=user, password=password)

        try:
            wmi_cls = w.Win32_PerfFormattedData_W3SVC_WebService(name="_Total")
            if not wmi_cls:
                raise Exception('Missing _Total from Win32_PerfFormattedData_W3SVC_WebService')
        except Exception:
            self.log.exception('Unable to fetch Win32_PerfFormattedData_W3SVC_WebService class')
            return

        wmi_cls = wmi_cls[0]
        for metric, mtype, wmi_val in self.METRICS:
            if not hasattr(wmi_cls, wmi_val):
                self.log.error('Unable to fetch metric %s. Missing %s in Win32_PerfFormattedData_W3SVC_WebService' \
                    % (metric, wmi_val))
                continue
            value = getattr(wmi_cls, wmi_val)
            self.gauge(metric, value, tags=tags)


if __name__ == "__main__":
    check, instances = IIS.from_yaml('conf.d/iis.yaml')
    for instance in instances:
        check.check(instance)
        print check.get_metrics()