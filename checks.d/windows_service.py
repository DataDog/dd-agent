""" Collect status information for Windows services
"""
# project
from checks import AgentCheck
from checks.wmi_check import WinWMICheck
from utils.containers import hash_mutable
from utils.timeout import TimeoutException


class WindowsService(WinWMICheck):
    STATE_TO_VALUE = {
        'Stopped': AgentCheck.CRITICAL,
        'Start Pending': AgentCheck.WARNING,
        'Stop Pending': AgentCheck.WARNING,
        'Running': AgentCheck.OK,
        'Continue Pending': AgentCheck.WARNING,
        'Pause Pending': AgentCheck.WARNING,
        'Paused': AgentCheck.WARNING,
        'Unknown': AgentCheck.UNKNOWN
    }
    NAMESPACE = "root\\CIMV2"
    CLASS = "Win32_Service"

    def __init__(self, name, init_config, agentConfig, instances):
        WinWMICheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):
        # Connect to the WMI provider
        host = instance.get('host', "localhost")
        user = instance.get('username', "")
        password = instance.get('password', "")
        services = instance.get('services', [])

        instance_hash = hash_mutable(instance)
        instance_key = self._get_instance_key(host, self.NAMESPACE, self.CLASS, instance_hash)
        tags = [] if (host == "localhost" or host == ".") else [u'host:{0}'.format(host)]

        if len(services) == 0:
            raise Exception('No services defined in windows_service.yaml')

        properties = ["Name", "State"]
        filters = map(lambda x: {"Name": tuple(('=', x))}, services)
        wmi_sampler = self._get_wmi_sampler(
            instance_key,
            self.CLASS, properties,
            filters=filters,
            host=host, namespace=self.NAMESPACE,
            username=user, password=password
        )

        try:
            # Sample, extract & submit metrics
            wmi_sampler.sample()
        except TimeoutException:
            self.log.warning(
                u"[WinService] WMI query timed out."
                u" class={wmi_class} - properties={wmi_properties} -"
                u" filters={filters} - tags={tags}".format(
                    wmi_class=self.CLASS, wmi_properties=properties,
                    filters=filters, tags=tags
                )
            )
        else:
            self._process_services(wmi_sampler, services, tags)

    def _process_services(self, wmi_sampler, services, tags):
        expected_services = set(services)

        for wmi_obj in wmi_sampler:
            service = wmi_obj['Name']
            if service not in services:
                continue

            status = self.STATE_TO_VALUE.get(wmi_obj["state"], AgentCheck.UNKNOWN)
            self.service_check("windows_service.state", status,
                               tags=tags + ['service:{0}'.format(service)])
            expected_services.remove(service)

        for service in expected_services:
            self.service_check("windows_service.state", AgentCheck.CRITICAL,
                               tags=tags + ['service:{0}'.format(service)])
