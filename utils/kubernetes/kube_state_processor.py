# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

NAMESPACE = 'kubernetes_state'

class KubeStateProcessor:
    def __init__(self, kubernetes_check):
        self.kube_check = kubernetes_check
        self.log = self.kube_check.log
        self.gauge = self.kube_check.gauge
        self.service_check = kubernetes_check.service_check
        # Original camelcase keys have already been converted to lowercase.
        self.pod_phase_to_status = {
            'pending':   kubernetes_check.WARNING,
            'running':   kubernetes_check.OK,
            'succeeded': kubernetes_check.OK,
            'failed':    kubernetes_check.CRITICAL,
            # Rely on lookup default value
            # 'unknown':   AgentCheck.UNKNOWN
        }

    def process(self, message, **kwargs):
        """
        Search this class for a method with the same name of the message and
        invoke it. Log some info if method was not found.
        """
        try:
            getattr(self, message.name)(message, **kwargs)
        except AttributeError:
            self.log.debug("Unable to handle metric: {}".format(message.name))

    def _eval_metric_condition(self, metric):
        """
        Some metrics contains conditions, labels that have "condition" as name and "true", "false", or "unknown"
        as value. The metric value is expected to be a gauge equal to 0 or 1 in this case.

        This function acts as an helper to iterate and evaluate metrics containing conditions
        and returns a tuple containing the name of the condition and the boolean value.
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

        Returns `None, None` if metric has no conditions.
        """
        val = bool(metric.gauge.value)
        for label in metric.label:
            if label.name == 'condition':
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

    def kube_node_status_capacity_cpu_cores(self, message, **kwargs):
        """ The total CPU resources of the node. """
        metric_name = NAMESPACE + '.node.cpu_capacity'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['node:{}'.format(self._extract_label_value("node", metric.label))]
            self.gauge(metric_name, val, tags)

    def kube_node_status_capacity_memory_bytes(self, message, **kwargs):
        """ The total memory resources of the node. """
        metric_name = NAMESPACE + '.node.memory_capacity'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['node:{}'.format(self._extract_label_value("node", metric.label))]
            self.gauge(metric_name, val, tags)

    def kube_node_status_capacity_pods(self, message, **kwargs):
        """ The total pod resources of the node. """
        metric_name = NAMESPACE + '.node.pods_capacity'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['node:{}'.format(self._extract_label_value("node", metric.label))]
            self.gauge(metric_name, val, tags)

    def kube_node_status_allocatable_cpu_cores(self, message, **kwargs):
        """ The CPU resources of a node that are available for scheduling. """
        metric_name = NAMESPACE + '.node.cpu_allocatable'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['node:{}'.format(self._extract_label_value("node", metric.label))]
            self.gauge(metric_name, val, tags)

    def kube_node_status_allocatable_memory_bytes(self, message, **kwargs):
        """ The memory resources of a node that are available for scheduling. """
        metric_name = NAMESPACE + '.node.memory_allocatable'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['node:{}'.format(self._extract_label_value("node", metric.label))]
            self.gauge(metric_name, val, tags)

    def kube_node_status_allocatable_pods(self, message, **kwargs):
        """ The pod resources of a node that are available for scheduling. """
        metric_name = NAMESPACE + '.node.pods_allocatable'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['node:{}'.format(self._extract_label_value("node", metric.label))]
            self.gauge(metric_name, val, tags)

    def kube_deployment_status_replicas_available(self, message, **kwargs):
        """ The number of available replicas per deployment. """
        metric_name = NAMESPACE + '.deployment.replicas_available'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['{}:{}'.format(label.name, label.value) for label in metric.label]
            self.gauge(metric_name, val, tags)

    def kube_deployment_status_replicas_unavailable(self, message, **kwargs):
        """ The number of unavailable replicas per deployment. """
        metric_name = NAMESPACE + '.deployment.replicas_unavailable'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['{}:{}'.format(label.name, label.value) for label in metric.label]
            self.gauge(metric_name, val, tags)

    def kube_deployment_status_replicas_updated(self, message, **kwargs):
        """ The number of updated replicas per deployment. """
        metric_name = NAMESPACE + '.deployment.replicas_updated'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['{}:{}'.format(label.name, label.value) for label in metric.label]
            self.gauge(metric_name, val, tags)

    def kube_deployment_spec_replicas(self, message, **kwargs):
        """ Number of desired pods for a deployment. """
        metric_name = NAMESPACE + '.deployment.replicas_desired'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['{}:{}'.format(label.name, label.value) for label in metric.label]
            self.gauge(metric_name, val, tags)

    # Labels attached: namespace, pod, container, node
    def kube_pod_container_requested_cpu_cores(self, message, **kwargs):
        """ CPU cores requested for a container in a pod. """
        metric_name = NAMESPACE + '.container.cpu_requested'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['{}:{}'.format(label.name, label.value) for label in metric.label]
            #TODO: add deployment/replicaset?
            self.gauge(metric_name, val, tags)

    # Labels attached: namespace, pod, container, node
    def kube_pod_container_requested_memory_bytes(self, message, **kwargs):
        """ Memory bytes requested for a container in a pod. """
        metric_name = NAMESPACE + '.container.memory_requested'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['{}:{}'.format(label.name, label.value) for label in metric.label]
            self.gauge(metric_name, val, tags)

    # TODO: Uncomment after kube-state-metrics 0.4 is released
    # Labels attached: namespace, pod, container, node
    # def kube_pod_container_limits_cpu_cores(self, message, **kwargs):
    #     """ CPU cores limit for a container in a pod. """
    #     metric_name = NAMESPACE + '.container.cpu_limit'
    #     for metric in message.metric:
    #         val = metric.gauge.value
    #         tags = ['{}:{}'.format(label.name, label.value) for label in metric.label]
    #         #TODO: add deployment/replicaset?
    #         self.gauge(metric_name, val, tags)

    # TODO: Uncomment after kube-state-metrics 0.4 is released
    # Labels attached: namespace, pod, container, node
    # def kube_pod_container_limits_memory_bytes(self, message, **kwargs):
    #     """ Memory byte limit for a container in a pod. """
    #     metric_name = NAMESPACE + '.container.memory_limit'
    #     for metric in message.metric:
    #         val = metric.gauge.value
    #         tags = ['{}:{}'.format(label.name, label.value) for label in metric.label]
    #         self.gauge(metric_name, val, tags)

    # TODO: implement kube_pod_container_status_ready
    # TODO: implement kube_pod_container_status_running
    # TODO: implement kube_pod_container_status_terminated
    # TODO: implement kube_pod_container_status_waiting

    # Labels attached: namespace, pod, container
    def kube_pod_container_status_restarts(self, message, **kwargs):
        """ Number of desired pods for a deployment. """
        metric_name = NAMESPACE + '.container.restarts'
        for metric in message.metric:
            val = metric.gauge.value
            tags = ['{}:{}'.format(label.name, label.value) for label in metric.label]
            self.gauge(metric_name, val, tags)

    # TODO: implement kube_pod_info
    # TODO: implement kube_pod_status_ready
    # TODO: implement kube_pod_status_scheduled

    # Labels attached: namespace, pod, phase=Pending|Running|Succeeded|Failed|Unknown
    # The phase gets not passed through; rather, it becomes the service check suffix.
    def kube_pod_status_phase(self, message, **kwargs):
        """ Phase a pod is in. """
        check_basename = NAMESPACE + '.pod.phase.'
        for metric in message.metric:
            # The gauge value is always 1, no point in fetching it.
            phase = ''
            tags = []
            for label in metric.label:
                if label.name == 'phase':
                    phase = label.value.lower()
                else:
                    tags.append('{}:{}'.format(label.name, label.value))
            #TODO: add deployment/replicaset?
            status = self.pod_phase_to_status.get(phase, self.kube_check.UNKNOWN)
            self.service_check(check_basename + phase, status, tags=tags)

    def kube_node_status_ready(self, message, **kwargs):
        """ The ready status of a cluster node. """
        service_check_name = NAMESPACE + '.node.ready'
        for metric in message.metric:
            name, val = self._eval_metric_condition(metric)
            tags = ['node:{}'.format(self._extract_label_value("node", metric.label))]
            if name == 'true' and val:
                self.service_check(service_check_name, self.kube_check.OK, tags=tags)
            elif name == 'false' and val:
                self.service_check(service_check_name, self.kube_check.CRITICAL, tags=tags)
            elif name == 'unknown' and val:
                self.service_check(service_check_name, self.kube_check.UNKNOWN, tags=tags)

    def kube_node_status_out_of_disk(self, message, **kwargs):
        """ Whether the node is out of disk space. """
        service_check_name = NAMESPACE + '.node.out_of_disk'
        for metric in message.metric:
            name, val = self._eval_metric_condition(metric)
            tags = ['node:{}'.format(self._extract_label_value("node", metric.label))]
            if name == 'true' and val:
                self.service_check(service_check_name, self.kube_check.CRITICAL, tags=tags)
            elif name == 'false' and val:
                self.service_check(service_check_name, self.kube_check.OK, tags=tags)
            elif name == 'unknown' and val:
                self.service_check(service_check_name, self.kube_check.UNKNOWN, tags=tags)

    def kube_node_spec_unschedulable(self, message, **kwargs):
        """ Whether a node can schedule new pods. """
        metric_name = NAMESPACE + '.node.status'
        statuses = ('schedulable', 'unschedulable')
        for metric in message.metric:
            tags = ['{}:{}'.format(label.name, label.value) for label in metric.label]
            status = statuses[int(metric.gauge.value)]  # value can be 0 or 1
            tags.append('status:{}'.format(status))
            self.gauge(metric_name, 1, tags)  # metric value is always one, value is on the tags
