# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from checks import CheckException
from checks.prometheus_check import PrometheusCheck
from checks import AgentCheck

# GenericPrometheusCheck is a class that helps instanciating PrometheusCheck only
# with YAML configurations. As each check has it own states it maintains a map
# of all checks so that the one corresponding to the instance is executed
#
# Minimal example configuration:
# instances:
#   - prometheus_url: http://foobar/endpoint
#     namespace: "foobar"
#     metrics:
#       - bar
#       - foo
class GenericPrometheusCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.check_map = {}
        for instance in instances:
            # Check mandatory settings
            endpoint = instance.get("prometheus_url", None)
            if endpoint is None:
                raise CheckException("Unable to find prometheus URL in config file.")
            namespace = instance.get("namespace", None)
            if namespace is None:
                raise CheckException("You have to define a namespace for each prometheus check")
            # Instanciate check
            check = PrometheusCheck(name, init_config, agentConfig, instance)
            check.NAMESPACE = namespace
            # metrics are preprocessed if no mapping
            metrics_mapper = {}
            for metric in instance.get("metrics", []):
                if isinstance(metric, basestring):
                    metrics_mapper[metric] = metric
                else:
                    metrics_mapper.update(metric)
            check.metrics_mapper = metrics_mapper
            check.labels_mapper = instance.get("labels_mapper", {})
            check.label_joins = instance.get("label_joins", {})
            check.exclude_labels = instance.get("exclude_labels", [])
            check.label_to_hostname = instance.get("label_to_hostname", None)
            check.health_service_check = instance.get("health_service_check", True)
            # use the parent aggregator
            check.aggregator = self.aggregator
            self.check_map[instance["prometheus_url"]] = check

    def check(self, instance):
        endpoint = instance["prometheus_url"]
        check = self.check_map[endpoint]
        if not check.metrics_mapper:
            raise CheckException("You have to collect at least one metric from the endpoint: " + endpoint)
        check.process(
            endpoint,
            send_histograms_buckets=instance.get('send_histograms_buckets', True),
            instance=instance,
            ignore_unmapped=True
        )
