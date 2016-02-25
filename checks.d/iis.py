'''
Check the performance counters from IIS
'''
# project
from checks import AgentCheck
from checks.wmi_check import WinWMICheck, WMIMetric
from utils.containers import hash_mutable
from utils.timeout import TimeoutException


class IIS(WinWMICheck):
    METRICS = [
        ('ServiceUptime', 'iis.uptime', 'gauge'),

        # Network
        ('TotalBytesSent','iis.net.bytes_sent', 'rate'),
        ('TotalBytesReceived', 'iis.net.bytes_rcvd', 'rate'),
        ('TotalBytesTransferred', 'iis.net.bytes_total', 'rate'),
        ('CurrentConnections', 'iis.net.num_connections', 'gauge'),
        ('TotalFilesSent', 'iis.net.files_sent', 'rate'),
        ('TotalFilesReceived', 'iis.net.files_rcvd', 'rate'),
        ('TotalConnectionAttemptsAllInstances', 'iis.net.connection_attempts', 'rate'),

        # HTTP Methods
        ('TotalGetRequests', 'iis.httpd_request_method.get', 'rate'),
        ('TotalPostRequests', 'iis.httpd_request_method.post', 'rate'),
        ('TotalHeadRequests', 'iis.httpd_request_method.head', 'rate'),
        ('TotalPutRequests', 'iis.httpd_request_method.put', 'rate'),
        ('TotalDeleteRequests', 'iis.httpd_request_method.delete', 'rate'),
        ('TotalOptionsRequests', 'iis.httpd_request_method.options', 'rate'),
        ('TotalTraceRequests', 'iis.httpd_request_method.trace', 'rate'),

        # Errors
        ('TotalNotFoundErrors', 'iis.errors.not_found', 'rate'),
        ('TotalLockedErrors', 'iis.errors.locked', 'rate'),

        # Users
        ('TotalAnonymousUsers', 'iis.users.anon', 'rate'),
        ('TotalNonAnonymousUsers', 'iis.users.nonanon', 'rate'),

        # Requests
        ('TotalCGIRequests', 'iis.requests.cgi', 'rate'),
        ('TotalISAPIExtensionRequests', 'iis.requests.isapi', 'rate'),
    ]
    SERVICE_CHECK = "iis.site_up"

    NAMESPACE = "root\\CIMV2"
    CLASS = "Win32_PerfFormattedData_W3SVC_WebService"

    def __init__(self, name, init_config, agentConfig, instances):
        WinWMICheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):
        # Connect to the WMI provider
        host = instance.get('host', "localhost")
        user = instance.get('username', "")
        password = instance.get('password', "")
        instance_tags = instance.get('tags', [])
        sites = instance.get('sites', ['_Total'])


        instance_hash = hash_mutable(instance)
        instance_key = self._get_instance_key(host, self.NAMESPACE, self.CLASS, instance_hash)
        filters = map(lambda x: {"Name": tuple(('=', x))}, sites)

        metrics_by_property, properties = self._get_wmi_properties(instance_key, self.METRICS, [])

        wmi_sampler = self._get_wmi_sampler(
            instance_key,
            self.CLASS, properties,
            filters=filters,
            host=host, namespace=self.NAMESPACE,
            username=user, password=password
        )

        # Sample, extract & submit metrics
        try:
            wmi_sampler.sample()

            metrics = self._extract_metrics(wmi_sampler, sites, instance_tags)
        except TimeoutException:
            self.log.warning(
                u"[IIS] WMI query timed out."
                u" class={wmi_class} - properties={wmi_properties} -"
                u" filters={filters} - tags={instance_tags}".format(
                    wmi_class=self.CLASS, wmi_properties=properties,
                    filters=filters, instance_tags=instance_tags
                )
            )
        else:
            self._submit_events(wmi_sampler, sites)
            self._submit_metrics(metrics, metrics_by_property)

    def _extract_metrics(self, wmi_sampler, sites, tags):
        """
        Extract and tag metrics from the WMISampler.

        Returns: List of WMIMetric
        ```
        [
            WMIMetric("freemegabytes", 19742, ["name:_total"]),
            WMIMetric("avgdiskbytesperwrite", 1536, ["name:c:"]),
        ]
        ```
        """
        metrics = []

        for wmi_obj in wmi_sampler:
            tags = list(tags) if tags else []

            # get site name
            sitename = wmi_obj['Name']

            # Skip any sites we don't specifically want.
            if sitename not in sites:
                continue
            elif sitename != "_Total":
                tags.append("site:{0}".format(self.normalize(sitename)))

            # Tag with `tag_queries` parameter
            for wmi_property, wmi_value in wmi_obj.iteritems():
                # Tag with `tag_by` parameter
                try:
                    metrics.append(WMIMetric(wmi_property, float(wmi_value), tags))
                except ValueError:
                    self.log.warning(u"When extracting metrics with WMI, found a non digit value"
                                     " for property '{0}'.".format(wmi_property))
                    continue
                except TypeError:
                    self.log.warning(u"When extracting metrics with WMI, found a missing property"
                                     " '{0}'".format(wmi_property))
                    continue
        return metrics

    def _submit_events(self, wmi_sampler, sites):
        expected_sites = set(sites)

        for wmi_obj in wmi_sampler:
            sitename = wmi_obj['Name']
            if sitename == "_Total":
                continue

            uptime = wmi_obj["ServiceUptime"]
            status = AgentCheck.CRITICAL if uptime == 0 else AgentCheck.OK

            self.service_check(self.SERVICE_CHECK, status, tags=['site:{0}'.format(self.normalize(sitename))])
            expected_sites.remove(sitename)

        for site in expected_sites:
            self.service_check(self.SERVICE_CHECK, AgentCheck.CRITICAL,
                               tags=['site:{0}'.format(self.normalize(site))])


    def _submit_metrics(self, wmi_metrics, metrics_by_property):
        for m in wmi_metrics:
            if m.name == "TotalBytesTransfered":
                m.name = "TotalBytesTransferred"
            elif m.name == "TotalConnectionAttemptsallinstances":
                m.name = "TotalConnectionAttemptsAllinstances"
            elif m.name not in metrics_by_property:
                continue

            metric, mtype = metrics_by_property[m.name]
            submittor = getattr(self, mtype)
            submittor(metric, m.value, m.tags)
