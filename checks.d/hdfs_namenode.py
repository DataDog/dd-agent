# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


'''
HDFS NameNode Metrics
---------------------
hdfs.namenode.capacity_total                    Total disk capacity in bytes
hdfs.namenode.capacity_used                     Disk usage in bytes
hdfs.namenode.capacity_remaining                Remaining disk space left in bytes
hdfs.namenode.total_load                        Total load on the file system
hdfs.namenode.fs_lock_queue_length              Lock queue length
hdfs.namenode.blocks_total                      Total number of blocks
hdfs.namenode.max_objects                       Maximum number of files HDFS supports
hdfs.namenode.files_total                       Total number of files
hdfs.namenode.pending_replication_blocks        Number of blocks pending replication
hdfs.namenode.under_replicated_blocks           Number of under replicated blocks
hdfs.namenode.scheduled_replication_blocks      Number of blocks scheduled for replication
hdfs.namenode.pending_deletion_blocks           Number of pending deletion blocks
hdfs.namenode.num_live_data_nodes               Total number of live data nodes
hdfs.namenode.num_dead_data_nodes               Total number of dead data nodes
hdfs.namenode.num_decom_live_data_nodes         Number of decommissioning live data nodes
hdfs.namenode.num_decom_dead_data_nodes         Number of decommissioning dead data nodes
hdfs.namenode.volume_failures_total             Total volume failures
hdfs.namenode.estimated_capacity_lost_total     Estimated capacity lost in bytes
hdfs.namenode.num_decommissioning_data_nodes    Number of decommissioning data nodes
hdfs.namenode.num_stale_data_nodes              Number of stale data nodes
hdfs.namenode.num_stale_storages                Number of stale storages
hdfs.namenode.missing_blocks                    Number of missing blocks
hdfs.namenode.corrupt_blocks                    Number of corrupt blocks
'''

# stdlib
from urlparse import urljoin

# 3rd party
import requests
from requests.exceptions import Timeout, HTTPError, InvalidURL, ConnectionError
from simplejson import JSONDecodeError

# Project
from checks import AgentCheck

# Service check names
JMX_SERVICE_CHECK = 'hdfs.namenode.jmx.can_connect'

# URL Paths
JMX_PATH = 'jmx'

# Namesystem state bean
HDFS_NAME_SYSTEM_STATE_BEAN = 'Hadoop:service=NameNode,name=FSNamesystemState'

# Namesystem bean
HDFS_NAME_SYSTEM_BEAN = 'Hadoop:service=NameNode,name=FSNamesystem'

# Metric types
GAUGE = 'gauge'

# HDFS metrics
HDFS_NAME_SYSTEM_STATE_METRICS = {
    'CapacityTotal' : ('hdfs.namenode.capacity_total',  GAUGE),
    'CapacityUsed' : ('hdfs.namenode.capacity_used',  GAUGE),
    'CapacityRemaining' : ('hdfs.namenode.capacity_remaining',  GAUGE),
    'TotalLoad' : ('hdfs.namenode.total_load',  GAUGE),
    'FsLockQueueLength' : ('hdfs.namenode.fs_lock_queue_length',  GAUGE),
    'BlocksTotal' : ('hdfs.namenode.blocks_total',  GAUGE),
    'MaxObjects' : ('hdfs.namenode.max_objects',  GAUGE),
    'FilesTotal' : ('hdfs.namenode.files_total',  GAUGE),
    'PendingReplicationBlocks' : ('hdfs.namenode.pending_replication_blocks',  GAUGE),
    'UnderReplicatedBlocks' : ('hdfs.namenode.under_replicated_blocks',  GAUGE),
    'ScheduledReplicationBlocks' : ('hdfs.namenode.scheduled_replication_blocks',  GAUGE),
    'PendingDeletionBlocks' : ('hdfs.namenode.pending_deletion_blocks',  GAUGE),
    'NumLiveDataNodes' : ('hdfs.namenode.num_live_data_nodes',  GAUGE),
    'NumDeadDataNodes' : ('hdfs.namenode.num_dead_data_nodes',  GAUGE),
    'NumDecomLiveDataNodes' : ('hdfs.namenode.num_decom_live_data_nodes',  GAUGE),
    'NumDecomDeadDataNodes' : ('hdfs.namenode.num_decom_dead_data_nodes',  GAUGE),
    'VolumeFailuresTotal' : ('hdfs.namenode.volume_failures_total',  GAUGE),
    'EstimatedCapacityLostTotal' : ('hdfs.namenode.estimated_capacity_lost_total',  GAUGE),
    'NumDecommissioningDataNodes' : ('hdfs.namenode.num_decommissioning_data_nodes',  GAUGE),
    'NumStaleDataNodes' : ('hdfs.namenode.num_stale_data_nodes',  GAUGE),
    'NumStaleStorages' : ('hdfs.namenode.num_stale_storages',  GAUGE),
}

HDFS_NAME_SYSTEM_METRICS = {
    'MissingBlocks' : ('hdfs.namenode.missing_blocks', GAUGE),
    'CorruptBlocks' : ('hdfs.namenode.corrupt_blocks', GAUGE)
}

class HDFSNameNode(AgentCheck):

    def check(self, instance):
        jmx_address = instance.get('hdfs_namenode_jmx_uri')
        if jmx_address is None:
            raise Exception('The JMX URL must be specified in the instance configuration')

        # Get metrics from JMX
        self._hdfs_namenode_metrics(jmx_address,
            HDFS_NAME_SYSTEM_STATE_BEAN,
            HDFS_NAME_SYSTEM_STATE_METRICS)

        self._hdfs_namenode_metrics(jmx_address,
            HDFS_NAME_SYSTEM_BEAN,
            HDFS_NAME_SYSTEM_METRICS)

        self.service_check(JMX_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['namenode_url:' + jmx_address],
            message='Connection to %s was successful' % jmx_address)

    def _hdfs_namenode_metrics(self, jmx_uri, bean_name, metrics):
        '''
        Get HDFS namenode metrics from JMX
        '''
        response = self._rest_request_to_json(jmx_uri,
            JMX_PATH,
            query_params={'qry':bean_name})

        beans = response.get('beans', [])

        tags = ['namenode_url:' + jmx_uri]

        if beans:

            bean = next(iter(beans))
            bean_name = bean.get('name')

            if bean_name != bean_name:
                raise Exception("Unexpected bean name {0}".format(bean_name))

            for metric, (metric_name, metric_type) in metrics.iteritems():
                metric_value = bean.get(metric)

                if metric_value is not None:
                    self._set_metric(metric_name, metric_type, metric_value, tags)

            if 'CapacityUsed' in bean and 'CapacityTotal' in bean:
                self._set_metric('hdfs.namenode.capacity_in_use', GAUGE,
                                 float(bean['CapacityUsed']) / float(bean['CapacityTotal']), tags)

    def _set_metric(self, metric_name, metric_type, value, tags=None):
        '''
        Set a metric
        '''
        if metric_type == GAUGE:
            self.gauge(metric_name, value, tags=tags)
        else:
            self.log.error('Metric type "%s" unknown' % (metric_type))

    def _rest_request_to_json(self, address, object_path, query_params):
        '''
        Query the given URL and return the JSON response
        '''
        response_json = None

        service_check_tags = ['namenode_url:' + address]

        url = address

        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add query_params as arguments
        if query_params:
            query = '&'.join(['{0}={1}'.format(key, value) for key, value in query_params.iteritems()])
            url = urljoin(url, '?' + query)

        self.log.debug('Attempting to connect to "%s"' % url)

        try:
            response = requests.get(url)
            response.raise_for_status()
            response_json = response.json()

        except Timeout as e:
            self.service_check(JMX_SERVICE_CHECK,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Request timeout: {0}, {1}".format(url, e))
            raise

        except (HTTPError,
                InvalidURL,
                ConnectionError) as e:
            self.service_check(JMX_SERVICE_CHECK,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Request failed: {0}, {1}".format(url, e))
            raise

        except JSONDecodeError as e:
            self.service_check(JMX_SERVICE_CHECK,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message='JSON Parse failed: {0}, {1}'.format(url, e))
            raise

        except ValueError as e:
            self.service_check(JMX_SERVICE_CHECK,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message=str(e))
            raise

        return response_json

    def _join_url_dir(self, url, *args):
        '''
        Join a URL with multiple directories
        '''

        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url
