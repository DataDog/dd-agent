# project
from checks.wmi_check import WinWMICheck
from utils.containers import hash_mutable


class WMICheck(WinWMICheck):
    """
    WMI check.

    Windows only.
    """
    def __init__(self, name, init_config, agentConfig, instances):
        WinWMICheck.__init__(self, name, init_config, agentConfig, instances)
        self.wmi_samplers = {}
        self.wmi_props = {}

    def check(self, instance):
        """
        Fetch WMI metrics.
        """
        # Connection information
        host = instance.get('host', "localhost")
        namespace = instance.get('namespace', "root\\cimv2")
        username = instance.get('username', "")
        password = instance.get('password', "")

        # WMI instance
        wmi_class = instance.get('class')
        metrics = instance.get('metrics')
        filters = instance.get('filters')
        tag_by = instance.get('tag_by', "").lower()
        tag_queries = instance.get('tag_queries', [])
        constant_tags = instance.get('constant_tags')

        # Create or retrieve an existing WMISampler
        instance_hash = hash_mutable(instance)
        instance_key = self._get_instance_key(host, namespace, wmi_class, instance_hash)

        metric_name_and_type_by_property, properties = \
            self._get_wmi_properties(instance_key, metrics, tag_queries)

        wmi_sampler = self._get_wmi_sampler(
            instance_key,
            wmi_class, properties,
            filters=filters,
            host=host, namespace=namespace,
            username=username, password=password,
        )

        # Sample, extract & submit metrics
        wmi_sampler.sample()
        metrics = self._extract_metrics(wmi_sampler, tag_by, tag_queries, constant_tags)
        self._submit_metrics(metrics, metric_name_and_type_by_property)
