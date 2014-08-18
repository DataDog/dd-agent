""" Collect status information for Windows services
"""
# project
from checks import AgentCheck

# 3rd party
import wmi

class WindowsService(AgentCheck):
    STATE_TO_VALUE = {
        'Stop Pending': 0,
        'Stopped': 0,
        'Start Pending': 1,
        'Running': 1,
        'Continue Pending': 1,
        'Pause Pending': 2,
        'Paused': 2,
        'Unknown': -1
    }

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.wmi_conns = {}

    def _get_wmi_conn(self, host, user, password):
        key = "%s:%s:%s" % (host, user, password)
        if key not in self.wmi_conns:
            self.wmi_conns[key] = wmi.WMI(host, user=user, password=password)
        return self.wmi_conns[key]

    def check(self, instance):
        # Connect to the WMI provider
        host = instance.get('host', None)
        user = instance.get('username', None)
        password = instance.get('password', None)
        tags = instance.get('tags') or []
        services = instance.get('services') or []
        w = self._get_wmi_conn(host, user, password)

        if len(services) == 0:
            raise Exception('No services defined in windows_service.yaml')

        for service in services:
            results = w.Win32_Service(name=service)
            if len(results) == 0:
                self.warning(u"No services found matching %s" % service)
                continue
            elif len(results) > 1:
                self.warning(u"Multiple services found matching %s" % service)
                continue

            wmi_service = results[0]
            self._collect_metrics(wmi_service, tags)

    def _collect_metrics(self, wmi_service, custom_tags):
        """ Given an instance of a wmi_object from Win32_Service, write any
            performance counters to be gathered and flushed by the collector.
        """
        tags = [u'service:%s' % wmi_service.Name]
        tags.extend(custom_tags)
        state_value = self.STATE_TO_VALUE.get(wmi_service.State, -1)
        self.gauge('windows_service.state', state_value, tags=tags)
