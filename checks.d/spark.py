'''
Spark Job Metrics
-----------------
spark.job.count
spark.job.num_tasks
spark.job.num_active_tasks
spark.job.num_completed_tasks
spark.job.num_skipped_tasks
spark.job.num_failed_tasks
spark.job.num_active_stages
spark.job.num_completed_stages
spark.job.num_skipped_stages
spark.job.num_failed_stages

Spark Stage Metrics
-------------------
spark.stage.count
spark.stage.num_active_tasks
spark.stage.num_complete_tasks
spark.stage.num_failed_tasks
spark.stage.executor_run_time
spark.stage.input_bytes
spark.stage.input_records
spark.stage.output_bytes
spark.stage.output_records
spark.stage.shuffle_read_bytes
spark.stage.shuffle_read_records
spark.stage.shuffle_write_bytes
spark.stage.shuffle_write_records
spark.stage.memory_bytes_spilled
spark.stage.disk_bytes_spilled

Spark Driver Metrics
----------------------
spark.driver.rdd_blocks
spark.driver.memory_used
spark.driver.disk_used
spark.driver.active_tasks
spark.driver.failed_tasks
spark.driver.completed_tasks
spark.driver.total_tasks
spark.driver.total_duration
spark.driver.total_input_bytes
spark.driver.total_shuffle_read
spark.driver.total_shuffle_write
spark.driver.max_memory

Spark Executor Metrics
----------------------
spark.executor.count
spark.executor.rdd_blocks
spark.executor.memory_used
spark.executor.disk_used
spark.executor.active_tasks
spark.executor.failed_tasks
spark.executor.completed_tasks
spark.executor.total_tasks
spark.executor.total_duration
spark.executor.total_input_bytes
spark.executor.total_shuffle_read
spark.executor.total_shuffle_write
spark.executor.max_memory

Spark RDD Metrics
-----------------
spark.rdd.count
spark.rdd.num_partitions
spark.rdd.num_cached_partitions
spark.rdd.memory_used
spark.rdd.disk_used
'''

# stdlib
from urlparse import urljoin, urlsplit, urlunsplit

# 3rd party
import requests
from requests.exceptions import Timeout, HTTPError, InvalidURL, ConnectionError
from simplejson import JSONDecodeError

# Project
from checks import AgentCheck

# Service Check Names
YARN_SERVICE_CHECK = 'spark.resource_manager.can_connect'
SPARK_SERVICE_CHECK = 'spark.application_master.can_connect'

# URL Paths
YARN_APPS_PATH = 'ws/v1/cluster/apps'
SPARK_APPS_PATH = 'api/v1/applications'

# Application type and states to collect
YARN_APPLICATION_TYPES = 'SPARK'
YARN_APPLICATION_STATES = 'RUNNING'

# Metric types
INCREMENT = 'increment'

# Metrics to collect
SPARK_JOB_METRICS = {
    'numTasks': ('spark.job.num_tasks', INCREMENT),
    'numActiveTasks': ('spark.job.num_active_tasks', INCREMENT),
    'numCompletedTasks': ('spark.job.num_completed_tasks', INCREMENT),
    'numSkippedTasks': ('spark.job.num_skipped_tasks', INCREMENT),
    'numFailedTasks': ('spark.job.num_failed_tasks', INCREMENT),
    'numActiveStages': ('spark.job.num_active_stages', INCREMENT),
    'numCompletedStages': ('spark.job.num_completed_stages', INCREMENT),
    'numSkippedStages': ('spark.job.num_skipped_stages', INCREMENT),
    'numFailedStages': ('spark.job.num_failed_stages', INCREMENT)
}

SPARK_STAGE_METRICS = {
    'numActiveTasks': ('spark.stage.num_active_tasks', INCREMENT),
    'numCompleteTasks': ('spark.stage.num_complete_tasks', INCREMENT),
    'numFailedTasks': ('spark.stage.num_failed_tasks', INCREMENT),
    'executorRunTime': ('spark.stage.executor_run_time', INCREMENT),
    'inputBytes': ('spark.stage.input_bytes', INCREMENT),
    'inputRecords': ('spark.stage.input_records', INCREMENT),
    'outputBytes': ('spark.stage.output_bytes', INCREMENT),
    'outputRecords': ('spark.stage.output_records', INCREMENT),
    'shuffleReadBytes': ('spark.stage.shuffle_read_bytes', INCREMENT),
    'shuffleReadRecords': ('spark.stage.shuffle_read_records', INCREMENT),
    'shuffleWriteBytes': ('spark.stage.shuffle_write_bytes', INCREMENT),
    'shuffleWriteRecords': ('spark.stage.shuffle_write_records', INCREMENT),
    'memoryBytesSpilled': ('spark.stage.memory_bytes_spilled', INCREMENT),
    'diskBytesSpilled': ('spark.stage.disk_bytes_spilled', INCREMENT)
}

SPARK_DRIVER_METRICS = {
    'rddBlocks': ('spark.driver.rdd_blocks', INCREMENT),
    'memoryUsed': ('spark.driver.memory_used', INCREMENT),
    'diskUsed': ('spark.driver.disk_used', INCREMENT),
    'activeTasks': ('spark.driver.active_tasks', INCREMENT),
    'failedTasks': ('spark.driver.failed_tasks', INCREMENT),
    'completedTasks': ('spark.driver.completed_tasks', INCREMENT),
    'totalTasks': ('spark.driver.total_tasks', INCREMENT),
    'totalDuration': ('spark.driver.total_duration', INCREMENT),
    'totalInputBytes': ('spark.driver.total_input_bytes', INCREMENT),
    'totalShuffleRead': ('spark.driver.total_shuffle_read', INCREMENT),
    'totalShuffleWrite': ('spark.driver.total_shuffle_write', INCREMENT),
    'maxMemory': ('spark.driver.max_memory', INCREMENT)
}

SPARK_EXECUTOR_METRICS = {
    'rddBlocks': ('spark.executor.rdd_blocks', INCREMENT),
    'memoryUsed': ('spark.executor.memory_used', INCREMENT),
    'diskUsed': ('spark.executor.disk_used', INCREMENT),
    'activeTasks': ('spark.executor.active_tasks', INCREMENT),
    'failedTasks': ('spark.executor.failed_tasks', INCREMENT),
    'completedTasks': ('spark.executor.completed_tasks', INCREMENT),
    'totalTasks': ('spark.executor.total_tasks', INCREMENT),
    'totalDuration': ('spark.executor.total_duration', INCREMENT),
    'totalInputBytes': ('spark.executor.total_input_bytes', INCREMENT),
    'totalShuffleRead': ('spark.executor.total_shuffle_read', INCREMENT),
    'totalShuffleWrite': ('spark.executor.total_shuffle_write', INCREMENT),
    'maxMemory': ('spark.executor.max_memory', INCREMENT)
}

SPARK_RDD_METRICS = {
    'numPartitions': ('spark.rdd.num_partitions', INCREMENT),
    'numCachedPartitions': ('spark.rdd.num_cached_partitions', INCREMENT),
    'memoryUsed': ('spark.rdd.memory_used', INCREMENT),
    'diskUsed': ('spark.rdd.disk_used', INCREMENT)
}


class SparkCheck(AgentCheck):

    def check(self, instance):
        # Get properties from conf file
        rm_address = instance.get('resourcemanager_uri')
        if rm_address is None:
            raise Exception('The ResourceManager URL must be specified in the instance configuration')

        # Get additional tags from the conf file
        tags = instance.get('tags', [])
        if tags is None:
            tags = []
        else:
            tags = list(set(tags))

        # Get the cluster name from the conf file
        cluster_name = instance.get('cluster_name')
        if cluster_name is None:
            raise Exception('The cluster_name must be specified in the instance configuration')

        tags.append('cluster_name:%s' % cluster_name)

        # Get the running MR applications from YARN
        running_apps = self._get_running_spark_apps(rm_address)

        # Report success after gathering all metrics from ResourceManaager
        self.service_check(YARN_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['url:%s' % rm_address],
            message='Connection to ResourceManager "%s" was successful' % rm_address)

        # Get the ids of the running spark applications
        spark_apps = self._get_spark_app_ids(running_apps)

        # Get the job metrics
        self._spark_job_metrics(spark_apps, tags)

        # Get the stage metrics
        self._spark_stage_metrics(spark_apps, tags)

        # Get the executor metrics
        self._spark_executor_metrics(spark_apps, tags)

        # Get the rdd metrics
        self._spark_rdd_metrics(spark_apps, tags)

        # Report success after gathering all metrics from the ApplicationMaster
        if running_apps:
            app_id, (app_name, tracking_url) = running_apps.items()[0]
            am_address = self._get_url_base(tracking_url)

            self.service_check(SPARK_SERVICE_CHECK,
                AgentCheck.OK,
                tags=['url:%s' % am_address],
                message='Connection to ApplicationMaster "%s" was successful' % am_address)

    def _get_running_spark_apps(self, rm_address):
        '''
        Return a dictionary of {app_id: (app_name, tracking_url)} for the running Spark applications
        '''
        metrics_json = self._rest_request_to_json(rm_address,
            YARN_APPS_PATH,
            YARN_SERVICE_CHECK,
            states=YARN_APPLICATION_STATES,
            applicationTypes=YARN_APPLICATION_TYPES)

        running_apps = {}

        if metrics_json.get('apps'):
            if metrics_json['apps'].get('app') is not None:

                for app_json in metrics_json['apps']['app']:
                    app_id = app_json.get('id')
                    tracking_url = app_json.get('trackingUrl')
                    app_name = app_json.get('name')

                    if app_id and tracking_url and app_name:
                        running_apps[app_id] = (app_name, tracking_url)

        return running_apps

    def _get_spark_app_ids(self, running_apps):
        '''
        Return a dictionary of {app_id: (app_name, tracking_url)} for Spark applications
        '''
        spark_apps = {}
        for app_id, (app_name, tracking_url) in running_apps.iteritems():
            response = self._rest_request_to_json(tracking_url,
                SPARK_APPS_PATH,
                SPARK_SERVICE_CHECK)
            for app in response:
                app_id = app.get('id')
                app_name = app.get('name')

                if app_id and app_name:
                    spark_apps[app_id] = (app_name, tracking_url)

        return spark_apps

    def _spark_job_metrics(self, running_apps, addl_tags):
        '''
        Get metrics for each Spark job.
        Return a map from Stage IDs to Job IDs
        '''
        for app_id, (app_name, tracking_url) in running_apps.iteritems():

            response = self._rest_request_to_json(tracking_url,
                SPARK_APPS_PATH,
                SPARK_SERVICE_CHECK, app_id, 'jobs')

            for job in response:

                status = job.get('status')

                tags = ['app_name:%s' % str(app_name)]
                tags.extend(addl_tags)
                tags.append('status:%s' % str(status).lower())

                self._set_metrics_from_json(tags, job, SPARK_JOB_METRICS)
                self._set_metric('spark.job.count', INCREMENT, 1, tags)

    def _spark_stage_metrics(self, running_apps, addl_tags):
        '''
        Get metrics for each Spark stage.
        '''
        for app_id, (app_name, tracking_url) in running_apps.iteritems():

            response = self._rest_request_to_json(tracking_url,
                SPARK_APPS_PATH,
                SPARK_SERVICE_CHECK, app_id, 'stages')

            for stage in response:

                status = stage.get('status')

                tags = ['app_name:%s' % str(app_name)]
                tags.extend(addl_tags)
                tags.append('status:%s' % str(status).lower())

                self._set_metrics_from_json(tags, stage, SPARK_STAGE_METRICS)
                self._set_metric('spark.stage.count', INCREMENT, 1, tags)

    def _spark_executor_metrics(self, running_apps, addl_tags):
        '''
        Get metrics for each Spark executor.
        '''
        for app_id, (app_name, tracking_url) in running_apps.iteritems():

            response = self._rest_request_to_json(tracking_url,
                SPARK_APPS_PATH,
                SPARK_SERVICE_CHECK, app_id, 'executors')

            tags = ['app_name:%s' % str(app_name)]
            tags.extend(addl_tags)

            for executor in response:
                if executor.get('id') == 'driver':
                    self._set_metrics_from_json(tags, executor, SPARK_DRIVER_METRICS)
                else:
                    self._set_metrics_from_json(tags, executor, SPARK_EXECUTOR_METRICS)

            if len(response):
                self._set_metric('spark.executor.count', INCREMENT, len(response), tags)

    def _spark_rdd_metrics(self, running_apps, addl_tags):
        '''
        Get metrics for each Spark RDD.
        '''
        for app_id, (app_name, tracking_url) in running_apps.iteritems():

            response = self._rest_request_to_json(tracking_url,
                SPARK_APPS_PATH,
                SPARK_SERVICE_CHECK, app_id, 'storage/rdd')

            tags = ['app_name:%s' % str(app_name)]
            tags.extend(addl_tags)

            for rdd in response:
                self._set_metrics_from_json(tags, rdd, SPARK_RDD_METRICS)

            if len(response):
                self._set_metric('spark.rdd.count', INCREMENT, len(response), tags)

    def _set_metrics_from_json(self, tags, metrics_json, metrics):
        '''
        Parse the JSON response and set the metrics
        '''
        for status, (metric_name, metric_type) in metrics.iteritems():
            metric_status = metrics_json.get(status)

            if metric_status is not None:
                self._set_metric(metric_name,
                    metric_type,
                    metric_status,
                    tags)

    def _set_metric(self, metric_name, metric_type, value, tags=None):
        '''
        Set a metric
        '''
        if metric_type == INCREMENT:
            self.increment(metric_name, value, tags=tags)
        else:
            self.log.error('Metric type "%s" unknown' % (metric_type))

    def _rest_request_to_json(self, address, object_path, service_name, *args, **kwargs):
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
            self.service_check(service_name,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Request timeout: {0}, {1}".format(url, e))
            raise

        except (HTTPError,
                InvalidURL,
                ConnectionError) as e:
            self.service_check(service_name,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Request failed: {0}, {1}".format(url, e))
            raise

        except JSONDecodeError as e:
            self.service_check(service_name,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message='JSON Parse failed: {0}, {1}'.format(url, e))
            raise

        except ValueError as e:
            self.service_check(service_name,
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

    def _get_url_base(self, url):
        '''
        Return the base of a URL
        '''
        s = urlsplit(url)
        return urlunsplit([s.scheme, s.netloc, '', '', ''])
