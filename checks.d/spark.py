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
import time
from urlparse import urljoin, urlsplit, urlunsplit

# 3rd party
import requests
from requests.exceptions import Timeout, HTTPError, InvalidURL, ConnectionError
from simplejson import JSONDecodeError
from bs4 import BeautifulSoup

# Project
from checks import AgentCheck
from config import _is_affirmative

# Identifier for cluster master address in `spark.yaml`
MASTER_ADDRESS = 'spark_url'
DEPRECATED_MASTER_ADDRESS = 'resourcemanager_uri'

# Switch that determines the mode Spark is running in. Can be either
# 'yarn' or 'standalone'
SPARK_CLUSTER_MODE = 'spark_cluster_mode'
SPARK_YARN_MODE = 'spark_yarn_mode'
SPARK_STANDALONE_MODE = 'spark_standalone_mode'
SPARK_MESOS_MODE = 'spark_mesos_mode'

# option enabling compatibility mode for Spark ver < 2
SPARK_PRE_20_MODE = 'spark_pre_20_mode'

# Service Checks
SPARK_STANDALONE_SERVICE_CHECK = 'spark.standalone_master.can_connect'
YARN_SERVICE_CHECK = 'spark.resource_manager.can_connect'
SPARK_SERVICE_CHECK = 'spark.application_master.can_connect'
MESOS_SERVICE_CHECK = 'spark.mesos_master.can_connect'

# URL Paths
YARN_APPS_PATH = 'ws/v1/cluster/apps'
SPARK_APPS_PATH = 'api/v1/applications'
SPARK_MASTER_STATE_PATH = '/json/'
SPARK_MASTER_APP_PATH = '/app/'
MESOS_MASTER_APP_PATH = '/frameworks'

# Application type and states to collect
YARN_APPLICATION_TYPES = 'SPARK'
APPLICATION_STATES = 'RUNNING'

# Event types
JOB_EVENT = 'job'
STAGE_EVENT = 'stage'

# Alert types
ERROR_STATUS = 'FAILED'
SUCCESS_STATUS = ['SUCCEEDED', 'COMPLETE']

# Event source type
SOURCE_TYPE_NAME = 'spark.application.server'

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
    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.previous_jobs = {}
        self.previous_stages = {}

    def check(self, instance):
        # Get additional tags from the conf file
        tags = instance.get('tags', [])
        if tags is None:
            tags = []
        else:
            tags = list(set(tags))

        spark_apps = self._get_running_apps(instance, tags)

        # Get the job metrics
        self._spark_job_metrics(spark_apps, tags)

        # Get the stage metrics
        self._spark_stage_metrics(spark_apps, tags)

        # Get the executor metrics
        self._spark_executor_metrics(spark_apps, tags)

        # Get the rdd metrics
        self._spark_rdd_metrics(spark_apps, tags)

        # Report success after gathering all metrics from the ApplicationMaster
        if spark_apps:
            app_id, (app_name, tracking_url) = spark_apps.items()[0]
            am_address = self._get_url_base(tracking_url)

            self.service_check(SPARK_SERVICE_CHECK,
                AgentCheck.OK,
                tags=['url:%s' % am_address],
                message='Connection to ApplicationMaster "%s" was successful' % am_address)

    def _get_running_apps(self, instance, tags):
        '''
        Determine what mode was specified
        '''

        # Get the master address from the instance configuration
        master_address = instance.get(MASTER_ADDRESS)
        if master_address is None:
            master_address = instance.get(DEPRECATED_MASTER_ADDRESS)

            if master_address:
                self.log.warning('The use of `%s` is deprecated. Please use `%s` instead.' %
                    (DEPRECATED_MASTER_ADDRESS, MASTER_ADDRESS))
            else:
                raise Exception('A URL for `%s` must be specified in the instance '
                    'configuration' % MASTER_ADDRESS)

        # Get the cluster name from the instance configuration
        cluster_name = instance.get('cluster_name')
        if cluster_name is None:
            raise Exception('The cluster_name must be specified in the instance configuration')

        tags.append('cluster_name:%s' % cluster_name)

        # Determine the cluster mode
        cluster_mode = instance.get(SPARK_CLUSTER_MODE)
        if cluster_mode is None:
            self.log.warning('The value for `spark_cluster_mode` was not set in the configuration. '
                'Defaulting to "%s"' % SPARK_YARN_MODE)
            cluster_mode = SPARK_YARN_MODE

        if cluster_mode == SPARK_STANDALONE_MODE:
            # check for PRE-20
            pre20 = _is_affirmative(instance.get(SPARK_PRE_20_MODE, False))
            return self._standalone_init(master_address, pre20)

        elif cluster_mode == SPARK_MESOS_MODE:
            running_apps = self._mesos_init(master_address)
            return self._get_spark_app_ids(running_apps)


        elif cluster_mode == SPARK_YARN_MODE:
            running_apps = self._yarn_init(master_address)
            return self._get_spark_app_ids(running_apps)

        else:
            raise Exception('Invalid setting for %s. Received %s.' % (SPARK_CLUSTER_MODE,
                cluster_mode))

    def _standalone_init(self, spark_master_address, pre_20_mode):
        '''
        Return a dictionary of {app_id: (app_name, tracking_url)} for the running Spark applications
        '''
        metrics_json = self._rest_request_to_json(spark_master_address,
            SPARK_MASTER_STATE_PATH,
            SPARK_STANDALONE_SERVICE_CHECK)

        running_apps = {}

        if metrics_json.get('activeapps'):
            for app in metrics_json['activeapps']:
                app_id = app.get('id')
                app_name = app.get('name')

                # Parse through the HTML to grab the application driver's link
                try:
                    app_url = self._get_standalone_app_url(app_id, spark_master_address)

                    if app_id and app_name and app_url:
                        if pre_20_mode:
                            self.log.debug('Getting application list in pre-20 mode')
                            applist = self._rest_request_to_json(app_url,
                                SPARK_APPS_PATH,
                                SPARK_STANDALONE_SERVICE_CHECK)
                            for appl in applist:
                                aid = appl.get('id')
                                aname = appl.get('name')
                                running_apps[aid] = (aname, app_url)
                        else:
                            running_apps[app_id] = (app_name, app_url)
                except:
                    # it's possible for the requests to fail if the job
                    # completed since we got the list of apps.  Just continue
                    pass

        # Report success after gathering metrics from Spark master
        self.service_check(SPARK_STANDALONE_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['url:%s' % spark_master_address],
            message='Connection to Spark master "%s" was successful' % spark_master_address)
        self.log.info("Returning running apps %s" % running_apps)
        return running_apps

    def _mesos_init(self, master_address):
        '''
        Return a dictionary of {app_id: (app_name, tracking_url)} for running Spark applications.
        '''
        running_apps = {}

        metrics_json = self._rest_request_to_json(master_address,
            MESOS_MASTER_APP_PATH,
            MESOS_SERVICE_CHECK)

        if metrics_json.get('frameworks'):
            for app_json in metrics_json.get('frameworks'):
                app_id = app_json.get('id')
                tracking_url = app_json.get('webui_url')
                app_name = app_json.get('name')

                if app_id and tracking_url and app_name:
                    running_apps[app_id] = (app_name, tracking_url)

        # Report success after gathering all metrics from ResourceManaager
        self.service_check(MESOS_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['url:%s' % master_address],
            message='Connection to ResourceManager "%s" was successful' % master_address)

        return running_apps

    def _yarn_init(self, rm_address):
        '''
        Return a dictionary of {app_id: (app_name, tracking_url)} for running Spark applications.
        '''
        running_apps = {}
        running_apps = self._yarn_get_running_spark_apps(rm_address)

        # Report success after gathering all metrics from ResourceManaager
        self.service_check(YARN_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['url:%s' % rm_address],
            message='Connection to ResourceManager "%s" was successful' % rm_address)

        return running_apps

    def _get_standalone_app_url(self, app_id, spark_master_address):
        '''
        Return the application URL from the app info page on the Spark master.
        Due to a bug, we need to parse the HTML manually because we cannot
        fetch JSON data from HTTP interface.
        '''
        app_page = self._rest_request(spark_master_address,
            SPARK_MASTER_APP_PATH,
            SPARK_STANDALONE_SERVICE_CHECK,
            appId=app_id)

        dom = BeautifulSoup(app_page.text, 'html.parser')
        app_detail_ui_links = dom.find_all('a', string='Application Detail UI')

        if app_detail_ui_links and len(app_detail_ui_links) == 1:
            return app_detail_ui_links[0].attrs['href']

    def _yarn_get_running_spark_apps(self, rm_address):
        '''
        Return a dictionary of {app_id: (app_name, tracking_url)} for running Spark applications.

        The `app_id` returned is that of the YARN application. This will eventually be mapped into
        a Spark application ID.
        '''
        metrics_json = self._rest_request_to_json(rm_address,
            YARN_APPS_PATH,
            YARN_SERVICE_CHECK,
            states=APPLICATION_STATES,
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
        Traverses the Spark application master in YARN to get a Spark application ID.

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
        '''
        new_jobs = {}

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

                job_id = job.get('jobId')
                previous_status = None
                if app_id in self.previous_jobs and job_id in self.previous_jobs[app_id]:
                    previous_status = self.previous_jobs[app_id][job_id].get('status')

                self._event_for_job_status_change(job, tags, previous_status)

            # Map application IDs to {job ID: job}
            new_jobs[app_id] = dict((job['jobId'], job) for job in response)

        self.previous_jobs = new_jobs

    def _spark_stage_metrics(self, running_apps, addl_tags):
        '''
        Get metrics for each Spark stage.
        '''
        new_stages = {}
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

                stage_id = stage.get('stageId')
                previous_status = None
                if app_id in self.previous_stages and stage_id in self.previous_stages[app_id]:
                    previous_status = self.previous_stages[app_id][stage_id].get('status')

                self._event_for_stage_status_change(stage, tags, previous_status)

            # Map application IDs to {stage ID: stage}
            new_stages[app_id] = dict((stage['stageId'], stage) for stage in response)

        self.previous_stages = new_stages

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

    def _event_for_job_status_change(self, current_job, tags, previous_status):
        '''
        Create an event for a job changing status
        '''
        job_name = current_job.get('name')
        job_id = current_job.get('jobId')
        current_status = current_job.get('status')

        self._set_event(current_status, previous_status, tags, JOB_EVENT, job_name, job_id)

    def _event_for_stage_status_change(self, current_stage, tags, previous_status):
        '''
        Create an event for a stage changing status
        '''
        stage_name = current_stage.get('name')
        stage_id = current_stage.get('stageId')
        current_status = current_stage.get('status')

        self._set_event(current_status, previous_status, tags, STAGE_EVENT, stage_name, stage_id)

    def _set_event(self, current_status, previous_status, tags, event_type, state_name, state_id):
        '''
        Create an event
        '''
        if previous_status is None:
            msg = 'New Spark {type} `{name}` (ID {id}) has status {curr}.'.format(type=event_type,
                name=state_name, id=state_id, curr=current_status)

        elif previous_status != current_status:
            msg = 'Spark {type} `{name}` (ID {id}) status changed from {prev} to {curr}.'.format(
                type=event_type, name=state_name, id=state_id, prev=previous_status,
                curr=current_status)

        else:
            return

        msg_title = 'Spark {type} `{stage}` has status {status}'.format(type=event_type,
            stage=state_name, status=current_status)

        alert_type = None
        if current_status == ERROR_STATUS:
            alert_type = 'error'
        elif current_status in SUCCESS_STATUS:
            alert_type = 'success'

        self.event({
            'timestamp': int(time.time()),
            'source_type_name': SOURCE_TYPE_NAME,
            'msg_title': msg_title,
            'msg_text': msg,
            'tags': tags,
            'alert_type': alert_type
        })

    def _rest_request(self, address, object_path, service_name, *args, **kwargs):
        '''
        Query the given URL and return the response
        '''
        response = None
        service_check_tags = ['url:%s' % self._get_url_base(address)]

        url = address

        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add args to the url
        if args:
            for directory in args:
                url = self._join_url_dir(url, directory)

        # Add kwargs as arguments
        if kwargs:
            query = '&'.join(['{0}={1}'.format(key, value) for key, value in kwargs.iteritems()])
            url = urljoin(url, '?' + query)

        try:
            self.log.debug('Spark check URL: %s' % url)
            response = requests.get(url)
            response.raise_for_status()

        except Timeout as e:
            self.service_check(service_name,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message='Request timeout: {0}, {1}'.format(url, e))
            raise

        except (HTTPError,
                InvalidURL,
                ConnectionError) as e:
            self.service_check(service_name,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message='Request failed: {0}, {1}'.format(url, e))
            raise

        except ValueError as e:
            self.service_check(service_name,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message=str(e))
            raise

        return response

    def _rest_request_to_json(self, address, object_path, service_name, *args, **kwargs):
        '''
        Query the given URL and return the JSON response
        '''
        response = self._rest_request(address, object_path, service_name, *args, **kwargs)

        try:
            response_json = response.json()

        except JSONDecodeError as e:
            self.service_check(service_name,
                AgentCheck.CRITICAL,
                tags=['url:%s' % self._get_url_base(address)],
                message='JSON Parse failed: {0}'.format(e))
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
