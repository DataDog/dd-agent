# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

'''
YARN Cluster Metrics
--------------------
yarn.metrics.appsSubmitted          The number of submitted apps
yarn.metrics.appsCompleted          The number of completed apps
yarn.metrics.appsPending            The number of pending apps
yarn.metrics.appsRunning            The number of running apps
yarn.metrics.appsFailed             The number of failed apps
yarn.metrics.appsKilled             The number of killed apps
yarn.metrics.reservedMB             The size of reserved memory
yarn.metrics.availableMB            The amount of available memory
yarn.metrics.allocatedMB            The amount of allocated memory
yarn.metrics.totalMB                The amount of total memory
yarn.metrics.reservedVirtualCores   The number of reserved virtual cores
yarn.metrics.availableVirtualCores  The number of available virtual cores
yarn.metrics.allocatedVirtualCores  The number of allocated virtual cores
yarn.metrics.totalVirtualCores      The total number of virtual cores
yarn.metrics.containersAllocated    The number of containers allocated
yarn.metrics.containersReserved     The number of containers reserved
yarn.metrics.containersPending      The number of containers pending
yarn.metrics.totalNodes             The total number of nodes
yarn.metrics.activeNodes            The number of active nodes
yarn.metrics.lostNodes              The number of lost nodes
yarn.metrics.unhealthyNodes         The number of unhealthy nodes
yarn.metrics.decommissionedNodes    The number of decommissioned nodes
yarn.metrics.rebootedNodes          The number of rebooted nodes

YARN App Metrics
----------------
yarn.app.progress             The progress of the application as a percent
yarn.app.startedTime          The time in which application started (in ms since epoch)
yarn.app.finishedTime         The time in which the application finished (in ms since epoch)
yarn.app.elapsedTime          The elapsed time since the application started (in ms)
yarn.app.allocatedMB          The sum of memory in MB allocated to the applications running containers
yarn.app.allocatedVCores      The sum of virtual cores allocated to the applications running containers
yarn.app.runningContainers    The number of containers currently running for the application
yarn.app.memorySeconds        The amount of memory the application has allocated (megabyte-seconds)
yarn.app.vcoreSeconds         The amount of CPU resources the application has allocated (virtual core-seconds)

YARN Node Metrics
-----------------
yarn.node.lastHealthUpdate       The last time the node reported its health (in ms since epoch)
yarn.node.usedMemoryMB           The total amount of memory currently used on the node (in MB)
yarn.node.availMemoryMB          The total amount of memory currently available on the node (in MB)
yarn.node.usedVirtualCores       The total number of vCores currently used on the node
yarn.node.availableVirtualCores  The total number of vCores available on the node
yarn.node.numContainers          The total number of containers currently running on the node

'''
# stdlib
from urlparse import urljoin, urlsplit, urlunsplit

# 3rd party
from requests.exceptions import Timeout, HTTPError, InvalidURL, ConnectionError
import requests

# Project
from checks import AgentCheck

# Default settings
DEFAULT_RM_URI = 'http://localhost:8088'
DEFAULT_TIMEOUT = 5
DEFAULT_CUSTER_NAME = 'default_cluster'

# Path to retrieve cluster metrics
YARN_CLUSTER_METRICS_PATH = '/ws/v1/cluster/metrics'

# Path to retrieve YARN APPS
YARN_APPS_PATH = '/ws/v1/cluster/apps'

# Path to retrieve node statistics
YARN_NODES_PATH = '/ws/v1/cluster/nodes'

# Metric types
GAUGE = 'gauge'
INCREMENT = 'increment'

# Name of the service check
SERVICE_CHECK_NAME = 'yarn.can_connect'

# Application states to collect
YARN_APPLICATION_STATES = 'RUNNING'

# Cluster metrics identifier
YARN_CLUSTER_METRICS_ELEMENT = 'clusterMetrics'

# Cluster metrics for YARN
YARN_CLUSTER_METRICS = {
    'appsSubmitted': ('yarn.metrics.apps_submitted', GAUGE),
    'appsCompleted': ('yarn.metrics.apps_completed', GAUGE),
    'appsPending': ('yarn.metrics.apps_pending', GAUGE),
    'appsRunning': ('yarn.metrics.apps_running', GAUGE),
    'appsFailed': ('yarn.metrics.apps_failed', GAUGE),
    'appsKilled': ('yarn.metrics.apps_killed', GAUGE),
    'reservedMB': ('yarn.metrics.reserved_mb', GAUGE),
    'availableMB': ('yarn.metrics.available_mb', GAUGE),
    'allocatedMB': ('yarn.metrics.allocated_mb', GAUGE),
    'totalMB': ('yarn.metrics.total_mb', GAUGE),
    'reservedVirtualCores': ('yarn.metrics.reserved_virtual_cores', GAUGE),
    'availableVirtualCores': ('yarn.metrics.available_virtual_cores', GAUGE),
    'allocatedVirtualCores': ('yarn.metrics.allocated_virtual_cores', GAUGE),
    'totalVirtualCores': ('yarn.metrics.total_virtual_cores', GAUGE),
    'containersAllocated': ('yarn.metrics.containers_allocated', GAUGE),
    'containersReserved': ('yarn.metrics.containers_reserved', GAUGE),
    'containersPending': ('yarn.metrics.containers_pending', GAUGE),
    'totalNodes': ('yarn.metrics.total_nodes', GAUGE),
    'activeNodes': ('yarn.metrics.active_nodes', GAUGE),
    'lostNodes': ('yarn.metrics.lost_nodes', GAUGE),
    'unhealthyNodes': ('yarn.metrics.unhealthy_nodes', GAUGE),
    'decommissionedNodes': ('yarn.metrics.decommissioned_nodes', GAUGE),
    'rebootedNodes': ('yarn.metrics.rebooted_nodes', GAUGE),
}

# Application metrics for YARN
YARN_APP_METRICS = {
    'progress': ('yarn.apps.progress', INCREMENT),
    'startedTime': ('yarn.apps.started_time', INCREMENT),
    'finishedTime': ('yarn.apps.finished_time', INCREMENT),
    'elapsedTime': ('yarn.apps.elapsed_time', INCREMENT),
    'allocatedMB': ('yarn.apps.allocated_mb', INCREMENT),
    'allocatedVCores': ('yarn.apps.allocated_vcores', INCREMENT),
    'runningContainers': ('yarn.apps.running_containers', INCREMENT),
    'memorySeconds': ('yarn.apps.memory_seconds', INCREMENT),
    'vcoreSeconds': ('yarn.apps.vcore_seconds', INCREMENT),
}

# Node metrics for YARN
YARN_NODE_METRICS = {
    'lastHealthUpdate': ('yarn.node.last_health_update', GAUGE),
    'usedMemoryMB': ('yarn.node.used_memory_mb', GAUGE),
    'availMemoryMB': ('yarn.node.avail_memory_mb', GAUGE),
    'usedVirtualCores': ('yarn.node.used_virtual_cores', GAUGE),
    'availableVirtualCores': ('yarn.node.available_virtual_cores', GAUGE),
    'numContainers': ('yarn.node.num_containers', GAUGE),
}


class YarnCheck(AgentCheck):
    '''
    Extract statistics from YARN's ResourceManger REST API
    '''

    def check(self, instance):

        # Get properties from conf file
        rm_address = instance.get('resourcemanager_uri', DEFAULT_RM_URI)

        # Get additional tags from the conf file
        tags = instance.get('tags', [])
        if tags is None:
            tags = []
        else:
            tags = list(set(tags))

        # Get the cluster name from the conf file
        cluster_name = instance.get('cluster_name')
        if cluster_name is None:
            self.warning("The cluster_name must be specified in the instance configuration, defaulting to '%s'" % (DEFAULT_CUSTER_NAME))
            cluster_name = DEFAULT_CUSTER_NAME

        tags.append('cluster_name:%s' % cluster_name)

        # Get metrics from the Resource Manager
        self._yarn_cluster_metrics(rm_address, tags)
        self._yarn_app_metrics(rm_address, tags)
        self._yarn_node_metrics(rm_address, tags)

    def _yarn_cluster_metrics(self, rm_address, addl_tags):
        '''
        Get metrics related to YARN cluster
        '''
        metrics_json = self._rest_request_to_json(rm_address, YARN_CLUSTER_METRICS_PATH)

        if metrics_json:

            yarn_metrics = metrics_json[YARN_CLUSTER_METRICS_ELEMENT]

            if yarn_metrics is not None:
                self._set_yarn_metrics_from_json(addl_tags, yarn_metrics, YARN_CLUSTER_METRICS)

    def _yarn_app_metrics(self, rm_address, addl_tags):
        '''
        Get metrics for running applications
        '''
        metrics_json = self._rest_request_to_json(rm_address,
            YARN_APPS_PATH,
            states=YARN_APPLICATION_STATES)

        if metrics_json:
            if metrics_json['apps'] is not None:
                if metrics_json['apps']['app'] is not None:

                    for app_json in metrics_json['apps']['app']:

                        app_name = app_json['name']

                        tags = ['app_name:%s' % str(app_name)]
                        tags.extend(addl_tags)

                        self._set_yarn_metrics_from_json(tags, app_json, YARN_APP_METRICS)

    def _yarn_node_metrics(self, rm_address, addl_tags):
        '''
        Get metrics related to YARN nodes
        '''
        metrics_json = self._rest_request_to_json(rm_address, YARN_NODES_PATH)

        if metrics_json:
            if metrics_json['nodes'] is not None:
                if metrics_json['nodes']['node'] is not None:

                    for node_json in metrics_json['nodes']['node']:
                        node_id = node_json['id']

                        tags = ['node_id:%s' % str(node_id)]
                        tags.extend(addl_tags)

                        self._set_yarn_metrics_from_json(tags, node_json, YARN_NODE_METRICS)

    def _set_yarn_metrics_from_json(self, tags, metrics_json, yarn_metrics):
        '''
        Parse the JSON response and set the metrics
        '''
        for status, metric in yarn_metrics.iteritems():
            metric_name, metric_type = metric

            if metrics_json.get(status) is not None:
                self._set_metric(metric_name,
                    metric_type,
                    metrics_json[status],
                    tags)

    def _set_metric(self, metric_name, metric_type, value, tags=None, device_name=None):
        '''
        Set a metric
        '''
        if metric_type == GAUGE:
            self.gauge(metric_name, value, tags=tags, device_name=device_name)
        elif metric_type == INCREMENT:
            self.increment(metric_name, value, tags=tags, device_name=device_name)
        else:
            self.log.error('Metric type "%s" unknown' % (metric_type))

    def _rest_request_to_json(self, address, object_path, *args, **kwargs):
        '''
        Query the given URL and return the JSON response
        '''
        response_json = None

        service_check_tags = ['url:%s' % self._get_url_base(address)]

        url = address

        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add args to the url
        if args:
            for directory in args:
                url = self._join_url_dir(url, directory)

        self.log.debug('Attempting to connect to "%s"' % url)

        # Add kwargs as arguments
        if kwargs:
            query = '&'.join(['{0}={1}'.format(key, value) for key, value in kwargs.iteritems()])
            url = urljoin(url, '?' + query)

        try:
            response = requests.get(url)
            response.raise_for_status()
            response_json = response.json()

        except Timeout as e:
            self.service_check(SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Request timeout: {0}, {1}".format(url, e))
            raise

        except (HTTPError,
                InvalidURL,
                ConnectionError) as e:
            self.service_check(SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Request failed: {0}, {1}".format(url, e))
            raise

        except ValueError as e:
            self.service_check(SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message=str(e))
            raise

        else:
            self.service_check(SERVICE_CHECK_NAME,
                AgentCheck.OK,
                tags=service_check_tags,
                message='Connection to %s was successful' % url)

        return response_json

    def _join_url_dir(self, url, *args):
        '''
        Join a URL with multiple directories
        '''
        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url

    def _get_url_base(self, url):
        '''
        Return the base of a URL
        '''
        s = urlsplit(url)
        return urlunsplit([s.scheme, s.netloc, '', '', ''])
