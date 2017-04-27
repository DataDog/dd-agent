# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import requests
from google.protobuf.internal.decoder import _DecodeVarint32  # pylint: disable=E0611,E0401
from checks import AgentCheck
from utils.prometheus import metrics_pb2

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

    def parse_metric_family(self, buf):
        """
        Parse the binary buffer in input, searching for Prometheus messages
        of type MetricFamily [0] delimited by a varint32 [1].

        [0] https://github.com/prometheus/client_model/blob/086fe7ca28bde6cec2acd5223423c1475a362858/metrics.proto#L76-%20%20L81
        [1] https://developers.google.com/protocol-buffers/docs/reference/java/com/google/protobuf/AbstractMessageLite#writeDelimitedTo(java.io.OutputStream)

        Imported from the utils/prometheus/functions.

        TODO: adapt to detect the text format and import it in protobuf classes for easier use.
        """
        n = 0
        while n < len(buf):
            msg_len, new_pos = _DecodeVarint32(buf, n)
            n = new_pos
            msg_buf = buf[n:n+msg_len]
            n += msg_len

            message = metrics_pb2.MetricFamily()
            message.ParseFromString(msg_buf)
            yield message

    def process(self, endpoint, send_histograms_buckets=True, instance=None):
        """
        Polls the data from prometheus and pushes them as gauges
        `endpoint` is the metrics endpoint to use to poll metrics from Prometheus
        """
        data = self.poll(endpoint)
        for metric in self.parse_metric_family(data):
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

    def _submit_metric(self, metric_name, message, send_histograms_buckets=True, labels_mapper={}, custom_tags=None, exclude_labels=None):
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

        `exclude_labels` is an array of labels names to exclude. Those labels
        will just not be added as tags when submitting the metric.
        """
        if message.type < len(self.METRIC_TYPES):
            for metric in message.metric:
                if message.type == 4:
                    self._submit_gauges_from_histogram(metric_name, metric, send_histograms_buckets, labels_mapper, custom_tags, exclude_labels)
                elif message.type == 2:
                    self._submit_gauges_from_summary(metric_name, metric, labels_mapper, custom_tags, exclude_labels)
                else:
                    val = getattr(metric, self.METRIC_TYPES[message.type]).value
                    self._submit_gauge(metric_name, val, metric, labels_mapper, custom_tags, exclude_labels)

        else:
            self.log.error("Metric type {} unsupported for metric {}.".format(message.type, message.name))

    def _submit_gauge(self, metric_name, val, metric, labels_mapper=None, custom_tags=None, exclude_labels=None):
        """
        Submit a metric as a gauge, additional tags provided will be added to
        the ones from the label provided via the metrics object.

        If the `labels_mapper` dictionnary is provided, the metrics labels names
        in the `labels_mapper` will use the corresponding value as tag name.

        `custom_tags` is an array of 'tag:value' that will be added to the
        metric when sending the gauge to Datadog.

        `exclude_labels` is an array of labels names to exclude. Those labels
        will just not be added as tags when submitting the metric.
        """
        _tags = custom_tags
        if _tags is None:
            _tags = []
        for label in metric.label:
            if exclude_labels is None or label.name not in exclude_labels:
                tag_name = label.name
                if labels_mapper is not None and label.name in labels_mapper:
                    tag_name = labels_mapper[label.name]
                _tags.append('{}:{}'.format(tag_name, label.value))
        self.gauge('{}.{}'.format(self.NAMESPACE, metric_name), val, _tags)

    def _submit_gauges_from_summary(self, name, metric, labels_mapper={}, custom_tags=None, exclude_labels=None):
        """
        Extracts metrics from a prometheus summary metric and sends them as gauges
        """
        if custom_tags is None:
            custom_tags = []
        # summaries do not have a value attribute
        val = getattr(metric, self.METRIC_TYPES[2]).sample_count
        self._submit_gauge("{}.count".format(name), val, metric, labels_mapper, custom_tags, exclude_labels)
        val = getattr(metric, self.METRIC_TYPES[2]).sample_sum
        self._submit_gauge("{}.sum".format(name), val, metric, labels_mapper, custom_tags, exclude_labels)
        for quantile in getattr(metric, self.METRIC_TYPES[2]).quantile:
            val = quantile.value
            limit = quantile.quantile
            self._submit_gauge("{}.quantile".format(name), val, metric, labels_mapper, custom_tags=custom_tags+["quantile:{}".format(limit)], exclude_labels=exclude_labels)

    def _submit_gauges_from_histogram(self, name, metric, send_histograms_buckets=True, labels_mapper={}, custom_tags=None, exclude_labels=None):
        """
        Extracts metrics from a prometheus histogram and sends them as gauges
        """
        if custom_tags is None:
            custom_tags = []
        # histograms do not have a value attribute
        val = getattr(metric, self.METRIC_TYPES[4]).sample_count
        self._submit_gauge("{}.count".format(name), val, metric, labels_mapper, custom_tags, exclude_labels)
        val = getattr(metric, self.METRIC_TYPES[4]).sample_sum
        self._submit_gauge("{}.sum".format(name), val, metric, labels_mapper, custom_tags, exclude_labels)
        if send_histograms_buckets:
            for bucket in getattr(metric, self.METRIC_TYPES[4]).bucket:
                val = bucket.cumulative_count
                limit = bucket.upper_bound
                self._submit_gauge("{}.count".format(name), val, metric, labels_mapper=labels_mapper, custom_tags=custom_tags+["upper_bound:{}".format(limit)], exclude_labels=exclude_labels)
