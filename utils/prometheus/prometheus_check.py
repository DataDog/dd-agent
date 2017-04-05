# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# std
import requests

# project
from checks import AgentCheck
from utils.prometheus import parse_metric_family


# Prometheus check is a mother class providing a structure and some helpers
# to collect metrics, events and service checks exposed in the Prometheus format.
#
# It must be noted that if the check implementing this class is not officially supported
# its metrics will count as cutom metrics and WILL impact billing.
#
# Minimal config for checks based on this class include:
#   - implementing the check method
#   - overriding self.NAMESPACE
#   - overriding self.metric_to_gauge
#     AND/OR
#   - create method named after the prometheus metric they will handle (see self.prometheus_metric_name)
#
# Refer to the kube-state-metrics check for a usage example.
class PrometheusCheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        # lists the prometheus metric types we support
        # message.type is the index in this array
        # see: https://github.com/prometheus/client_model/blob/model-0.0.2/metrics.proto#L24-L28
        self.METRIC_TYPES = ['counter', 'gauge']

        # NAMESPACE is the prefix metrics will have
        self.NAMESPACE = ''

        # these metrics will be extracted with all their labels
        # and reported as-is with their corresponding metric name
        self.metric_to_gauge = {
        # message.metric: datadog.metric
        }

    def check(self, instance):
        """
        check should take care of getting the url and other params
        from the instance and using the utils to process messages and submit metrics.
        """
        raise NotImplementedError()

    def process(self, raw_payload, **kwargs):
        """
        Handle a message according to the following flow:
            - search self.metric_to_gauge for a prometheus.metric <--> datadog.metric mapping
            - call check method with the same name as the metric
            - log some info if none of the above worked
        """
        payload = parse_metric_family(raw_payload)
        for message in payload:
            try:
                if message.name in self.metric_to_gauge:
                    self._submit_gauges(self.metric_to_gauge[message.name], message, **kwargs)
                else:
                    getattr(self, message.name)(message, **kwargs)
            except AttributeError:
                self.log.debug("Unable to handle metric: {}".format(message.name))

    def perform_protobuf_query(self, url, headers={}):
        """
        Get content from an endpoint using the protobuf format (accept and use custom headers).
        """
        req_headers = {'accept': 'application/vnd.google.protobuf; proto=io.prometheus.client.MetricFamily; encoding=delimited'}
        for h_n, h_v in headers.iteritems():
            req_headers[h_n] = h_v
        return self.perform_query(url, headers=req_headers)

    def perform_query(self, url, headers={}):
        """
        Get content from an endpoint (accept and use custom headers).
        """
        req_headers = {
            'accept-encoding': 'gzip',
        }
        for h_n, h_v in headers.iteritems():
            req_headers[h_n] = h_v
        req = requests.get(url, headers=req_headers)
        req.raise_for_status()
        return req.content

    def _submit_gauges(self, metric_name, message, labels={}, **kwargs):
        """
        For each metric in the message, report it as a gauge with all labels as tags
        except if a labels dict is passed, in which case keys are label names we'll extract
        and corresponding values are tag names we'll use (eg: {'node': 'node'})
        """
        if message.type < len(self.METRIC_TYPES):
            for metric in message.metric:
                val = getattr(metric, self.METRIC_TYPES[message.type]).value
                tags = kwargs.get('tags', set()) or set()
                if labels == {}:
                    tags = tags.union(set(['{}:{}'.format(label.name, label.value) for label in metric.label]))
                else:
                    for label, tag in labels.iteritems():
                        tags.add('{}:{}'.format(
                            tag, self._extract_label_value(label, metric.label)))

                self.gauge(metric_name, val, list(tags))
        else:
            self.log.error("Metric type %s unsupported for metric %s." % (message.type, message.name))

    # Helpers

    def _eval_metric_state(self, metric, state_marker="condition"):
        """
        Some metrics report state, labels that have a state marker as name and "true", "false", or "unknown"
        as value. The metric value is expected to be a gauge equal to 0 or 1 in this case.

        This function acts as an helper to iterate and evaluate metrics containing such state
        marker and returns a tuple containing the state marker and the boolean value.
        For example:

        metric {
          label {
            name: "condition"
            value: "true"
          }
          # other labels here
          gauge {
            value: 1.0
          }
        }

        would return `("true", True)`.

        Returns `None, None` if metric has no state marker.
        """
        val = bool(metric.gauge.value)
        for label in metric.label:
            if label.name == state_marker:
                return label.value, val

        return None, None

    def _extract_label_value(self, name, labels):
        """
        Search for `name` in labels name and returns
        corresponding value.
        Returns None if name was not found.
        """
        for label in labels:
            if label.name == name:
                return label.value
        return None

    def prometheus_metric_name(self, message, **kwargs):
        """ Example method"""
        pass
