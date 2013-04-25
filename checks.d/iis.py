'''
Check the performance counters from IIS
'''
from checks import AgentCheck

class IIS(AgentCheck):
    METRICS = [
        ('iis.uptime', 'gauge', 'ServiceUptime'),

        # Network
        ('iis.net.bytes_sent', 'rate', 'TotalBytesSent'),
        ('iis.net.bytes_rcvd', 'rate', 'TotalBytesReceived'),
        ('iis.net.bytes_total', 'rate', 'TotalBytesTransferred'),
        ('iis.net.num_connections', 'gauge', 'CurrentConnections'),
        ('iis.net.files_sent', 'rate', 'TotalFilesSent'),
        ('iis.net.files_rcvd', 'rate', 'TotalFilesReceived'),
        ('iis.net.connection_attempts', 'rate', 'TotalConnectionAttemptsAllInstances'),

        # HTTP Methods
        ('iis.httpd_request_method.get', 'rate', 'TotalGetRequests'),
        ('iis.httpd_request_method.post', 'rate', 'TotalPostRequests'),
        ('iis.httpd_request_method.head', 'rate', 'TotalHeadRequests'),
        ('iis.httpd_request_method.put', 'rate', 'TotalPutRequests'),
        ('iis.httpd_request_method.delete', 'rate', 'TotalDeleteRequests'),
        ('iis.httpd_request_method.options', 'rate', 'TotalOptionsRequests'),
        ('iis.httpd_request_method.trace', 'rate', 'TotalTraceRequests'),

        # Errors
        ('iis.errors.not_found', 'rate', 'TotalNotFoundErrors'),
        ('iis.errors.locked', 'rate', 'TotalLockedErrors'),

        # Users
        ('iis.users.anon', 'rate', 'TotalAnonymousUsers'),
        ('iis.users.nonanon', 'rate', 'TotalNonAnonymousUsers'),

        # Requests
        ('iis.requests.cgi', 'rate', 'TotalCGIRequests'),
        ('iis.requests.isapi', 'rate', 'TotalISAPIExtensionRequests'),
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

            # Submit the metric value with the correct type
            value = getattr(wmi_cls, wmi_val)
            metric_func = getattr(self, mtype)
            metric_func(metric, value, tags=tags)
