# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from checks.prometheus_mixins import PrometheusScraper
from checks import AgentCheck

# Prometheus check is a parent class providing a structure and some helpers
# to collect metrics, events and service checks exposed via Prometheus.
#
# It must be noted that if the check implementing this class is not officially
# supported
# its metrics will count as cutom metrics and WILL impact billing.
#
# Minimal config for checks based on this class include:
#   - implementing the check method
#   - overriding self.NAMESPACE
#   - overriding self.metrics_mapper
#     AND/OR
#   - create method named after the prometheus metric with the signature prometheus_metric_name(self, message, **kwargs)
#     it will be called in `process_metric`
#

class PrometheusCheck(PrometheusScraper, AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(PrometheusCheck, self).__init__(name, init_config, agentConfig, instances)

    def check(self, instance):
        """
        check should take care of getting the url and other params
        from the instance and using the utils to process messages and submit metrics.
        """
        raise NotImplementedError()

    def _submit_gauge(self, metric_name, val, metric, custom_tags=None, hostname=None):
        """
        Submit a metric as a gauge, additional tags provided will be added to
        the ones from the label provided via the metrics object.

        `custom_tags` is an array of 'tag:value' that will be added to the
        metric when sending the gauge to Datadog.
        """
        _tags = []
        if custom_tags is not None:
            _tags += custom_tags
        for label in metric.label:
            if self.exclude_labels is None or label.name not in self.exclude_labels:
                tag_name = label.name
                if self.labels_mapper is not None and label.name in self.labels_mapper:
                    tag_name = self.labels_mapper[label.name]
                _tags.append('{}:{}'.format(tag_name, label.value))
        _tags = self._finalize_tags_to_submit(_tags, metric_name, val, metric, custom_tags=custom_tags, hostname=hostname)
        self.gauge('{}.{}'.format(self.NAMESPACE, metric_name), val, _tags, hostname=hostname)

    def _submit_service_check(self, *args, **kwargs):
        self.service_check(*args, **kwargs)
