# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import requests
from checks import AgentCheck
from utils.prometheus import parse_metric_family

# Prometheus check is a mother class providing a structure and some helpers
# to collect metrics, events and service checks exposed via Prometheus.
#
# It must be noted that if the check implementing this class is not officially
# supported
# its metrics will count as cutom metrics and WILL impact billing.
#
# Minimal config for checks based on this class include:
#   - implementing the check method
#   - overriding self.NAMESPACE
#   - overriding self.metric_to_gauge
#     AND/OR
#   - create method named after the prometheus metric they will handle (see self.prometheus_metric_name)
#
# Check class example:
# from checks import CheckException
# from checks.prometheus_check import PrometheusCheck
#
# EVENT_TYPE = SOURCE_TYPE_NAME = 'kubedns'
#
# class KubeDNSCheck(PrometheusCheck):
#     """
#     Collect kube dns metrics from Prometheus
#     """
#     def __init__(self, name, init_config, agentConfig, instances=None):
#         super(PrometheusDNSCheck, self).__init__(name, init_config, agentConfig, instances)
#         self.client = PrometheusCheck(self)
#         self.client.NAMESPACE='kubedns'
#
#         self.client.metrics_mapper = {
#             'skydns_skydns_dns_response_size_bytes': 'dns.response_size.bytes',
#             'skydns_skydns_dns_request_duration_seconds': 'dns.request_duration.seconds',
#             'skydns_skydns_dns_request_count_total': 'dns.request_count.total',
#             'skydns_skydns_dns_error_count_total': 'dns.error_count.total',
#             'skydns_skydns_dns_cachemiss_count_total': 'dns.cachemiss_count.total',
#         }
#
#
#     def check(self, instance):
#         endpoint = 'http://localhost:10055/metrics'
#         if endpoint is None:
#             raise CheckException("Unable to find prometheus_endpoint in config file.")
#
#         send_buckets = instance.get('send_histograms_buckets')
#         if send_buckets is None:
#             raise CheckException("Unable to find send_histograms_buckets in config file.")
#
#         self.client.process(endpoint, send_histograms_buckets=send_buckets, instance=instance)
#

# Used to specify if you want to use the protobuf format or the text format when
# querying prometheus metrics
class PrometheusFormat:
    PROTOBUF = "PROTOBUF"
    TEXT = "TEXT"

class PrometheusCheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        # message.type is the index in this array
        # see: https://github.com/prometheus/client_model/blob/master/ruby/lib/prometheus/client/model/metrics.pb.rb
        self.METRIC_TYPES = ['counter', 'gauge', 'summary', 'untyped', 'histogram']

        # NAMESPACE is the prefix metrics will have. Need to be hardcoded in the
        # child check class.
        self.NAMESPACE = ''

        # metrics_mapper is a dictionnary where the keys are the metrics to capture
        # and the values are the corresponding metrics names to have in datadog.
        # Note: it is empty in the mother class but will need to be
        # overloaded/hardcoded in the final check not to be counted as custom metric.
        self.metrics_mapper = {}

    def check(self, instance):
        """
        check should take care of getting the url and other params
        from the instance and using the utils to process messages and submit metrics.
        """
        raise NotImplementedError()

    def process(self, endpoint, send_histograms_buckets=True, instance=None):
        """
        Polls the data from prometheus and pushes them as gauges
        `endpoint` is the metrics endpoint to use to poll metrics from Prometheus
        """
        data = self.poll(endpoint)
        for metric in parse_metric_family(data):
            self.process_metric(metric, instance=instance)

    def process_metric(self, message, send_histograms_buckets=True, **kwargs):
        """
        Handle a prometheus metric message according to the following flow:
            - search self.metrics_mapper for a prometheus.metric <--> datadog.metric mapping
            - call check method with the same name as the metric
            - log some info if none of the above worked

        `send_histograms_buckets` is used to specify if yes or no you want to send the buckets as tagged values when dealing with histograms.
        """
        try:
            if message.name in self.metrics_mapper:
                self._submit_metric(self.metrics_mapper[message.name], message, send_histograms_buckets)
            else:
                getattr(self, message.name)(message, **kwargs)
        except AttributeError as err:
            self.log.debug("Unable to handle metric: {} - error: {}".format(message.name, err))

    def poll(self, endpoint, pFormat=PrometheusFormat.PROTOBUF, headers={}):
        """
        Polls the metrics from the prometheus metrics endpoint provided.
        Defaults to the protobuf format, but can use the formats specified by
        the PrometheusFormat class.
        Custom headers can be added to the default headers.
        """
        if 'accept-encoding' not in headers:
            headers['accept-encoding'] = 'gzip'
        if pFormat == PrometheusFormat.PROTOBUF:
            headers['accept'] = 'application/vnd.google.protobuf; proto=io.prometheus.client.MetricFamily; encoding=delimited'

        req = requests.get(endpoint, headers=headers)
        req.raise_for_status()
        return req.content

    def _submit_metric(self, metric_name, message, send_histograms_buckets=True, labels_mapper={}, custom_tags=None):
        """
        For each metric in the message, report it as a gauge with all labels as tags
        except if a labels dict is passed, in which case keys are label names we'll extract
        and corresponding values are tag names we'll use (eg: {'node': 'node'}).

        Histograms generate a set of values instead of a unique metric.
        send_histograms_buckets is used to specify if yes or no you want to
            send the buckets as tagged values when dealing with histograms.

        If the `labels_mapper` dictionnary is provided, the metrics labels names
        in the `labels_mapper` will use the corresponding value as tag name.

        `custom_tags` is an array of 'tag:value' that will be added to the
        metric when sending the gauge to Datadog.
        """
        if message.type < len(self.METRIC_TYPES):
            for metric in message.metric:
                if message.type == 4:
                    self._submit_gauges_from_histogram(metric_name, metric, send_histograms_buckets, labels_mapper, custom_tags)
                elif message.type == 2:
                    self._submit_gauges_from_summary(metric_name, metric, labels_mapper, custom_tags)
                else:
                    val = getattr(metric, self.METRIC_TYPES[message.type]).value
                    self._submit_gauge(metric_name, val, metric, labels_mapper, custom_tags)

        else:
            self.log.error("Metric type {} unsupported for metric {}.".format(message.type, message.name))

    def _submit_gauge(self, metric_name, val, metric, labels_mapper=None, custom_tags=None):
        """
        Submit a metric as a gauge, additional tags provided will be added to
        the ones from the label provided via the metrics object.

        If the `labels_mapper` dictionnary is provided, the metrics labels names
        in the `labels_mapper` will use the corresponding value as tag name.
        """
        _tags = custom_tags
        if _tags is None:
            _tags = []
        for label in metric.label:
            tag_name = label.name
            if labels_mapper is not None and label.name in labels_mapper:
                tag_name = labels_mapper[label.name]
            _tags.append('{}:{}'.format(tag_name, label.value))
        self.gauge('{}.{}'.format(self.NAMESPACE, metric_name), val, _tags)

    def _submit_gauges_from_summary(self, name, metric, labels_mapper={}, custom_tags=None):
        """
        Extracts metrics from a prometheus summary metric and sends them as gauges
        """
        if custom_tags is None:
            custom_tags = []
        # summaries do not have a value attribute
        val = getattr(metric, self.METRIC_TYPES[2]).sample_count
        self._submit_gauge("{}.count".format(name), val, metric, labels_mapper, custom_tags)
        val = getattr(metric, self.METRIC_TYPES[2]).sample_sum
        self._submit_gauge("{}.sum".format(name), val, metric, labels_mapper, custom_tags)
        for quantile in getattr(metric, self.METRIC_TYPES[2]).quantile:
            val = quantile.value
            limit = quantile.quantile
            self._submit_gauge("{}.quantile".format(name), val, metric, labels_mapper, custom_tags=custom_tags+["quantile:{}".format(limit)])

    def _submit_gauges_from_histogram(self, name, metric, send_histograms_buckets=True, labels_mapper={}, custom_tags=None):
        """
        Extracts metrics from a prometheus histogram and sends them as gauges
        """
        if custom_tags is None:
            custom_tags = []
        # histograms do not have a value attribute
        val = getattr(metric, self.METRIC_TYPES[4]).sample_count
        self._submit_gauge("{}.count".format(name), val, metric, labels_mapper, custom_tags)
        val = getattr(metric, self.METRIC_TYPES[4]).sample_sum
        self._submit_gauge("{}.sum".format(name), val, metric, labels_mapper, custom_tags)
        if send_histograms_buckets:
            for bucket in getattr(metric, self.METRIC_TYPES[4]).bucket:
                val = bucket.cumulative_count
                limit = bucket.upper_bound
                self._submit_gauge("{}.count".format(name), val, metric, labels_mapper=labels_mapper, custom_tags=custom_tags+["upper_bound:{}".format(limit)])
