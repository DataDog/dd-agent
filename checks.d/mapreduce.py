# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

'''
MapReduce Job Metrics
---------------------
mapreduce.job.elapsed_ime                The elapsed time since the application started (in ms)
mapreduce.job.maps_total                 The total number of maps
mapreduce.job.maps_completed             The number of completed maps
mapreduce.job.reduces_total              The total number of reduces
mapreduce.job.reduces_completed          The number of completed reduces
mapreduce.job.maps_pending               The number of maps still to be run
mapreduce.job.maps_running               The number of running maps
mapreduce.job.reduces_pending            The number of reduces still to be run
mapreduce.job.reduces_running            The number of running reduces
mapreduce.job.new_reduce_attempts        The number of new reduce attempts
mapreduce.job.running_reduce_attempts    The number of running reduce attempts
mapreduce.job.failed_reduce_attempts     The number of failed reduce attempts
mapreduce.job.killed_reduce_attempts     The number of killed reduce attempts
mapreduce.job.successful_reduce_attempts The number of successful reduce attempts
mapreduce.job.new_map_attempts           The number of new map attempts
mapreduce.job.running_map_attempts       The number of running map attempts
mapreduce.job.failed_map_attempts        The number of failed map attempts
mapreduce.job.killed_map_attempts        The number of killed map attempts
mapreduce.job.successful_map_attempts    The number of successful map attempts

MapReduce Job Counter Metrics
-----------------------------
mapreduce.job.counter.reduce_counter_value   The counter value of reduce tasks
mapreduce.job.counter.map_counter_value      The counter value of map tasks
mapreduce.job.counter.total_counter_value    The counter value of all tasks

MapReduce Map Task Metrics
--------------------------
mapreduce.job.map.task.progress     The distribution of all map task progresses

MapReduce Reduce Task Metrics
--------------------------
mapreduce.job.reduce.task.progress      The distribution of all reduce task progresses
'''

# stdlib
from urlparse import urljoin
from urlparse import urlsplit
from urlparse import urlunsplit

# 3rd party
import requests
from requests.exceptions import Timeout, HTTPError, InvalidURL, ConnectionError
from simplejson import JSONDecodeError

# Project
from checks import AgentCheck
from config import _is_affirmative


# Default Settings
DEFAULT_CUSTER_NAME = 'default_cluster'

# Service Check Names
YARN_SERVICE_CHECK = 'mapreduce.resource_manager.can_connect'
MAPREDUCE_SERVICE_CHECK = 'mapreduce.application_master.can_connect'

# URL Paths
YARN_APPS_PATH = 'ws/v1/cluster/apps'
MAPREDUCE_JOBS_PATH = 'ws/v1/mapreduce/jobs'

# Application type and states to collect
YARN_APPLICATION_TYPES = 'MAPREDUCE'
YARN_APPLICATION_STATES = 'RUNNING'

# Metric types
HISTOGRAM = 'histogram'
INCREMENT = 'increment'

# Metrics to collect
MAPREDUCE_JOB_METRICS = {
    'elapsedTime': ('mapreduce.job.elapsed_time', HISTOGRAM),
    'mapsTotal': ('mapreduce.job.maps_total', INCREMENT),
    'mapsCompleted': ('mapreduce.job.maps_completed', INCREMENT),
    'reducesTotal': ('mapreduce.job.reduces_total', INCREMENT),
    'reducesCompleted': ('mapreduce.job.reduces_completed', INCREMENT),
    'mapsPending': ('mapreduce.job.maps_pending', INCREMENT),
    'mapsRunning': ('mapreduce.job.maps_running', INCREMENT),
    'reducesPending': ('mapreduce.job.reduces_pending', INCREMENT),
    'reducesRunning': ('mapreduce.job.reduces_running', INCREMENT),
    'newReduceAttempts': ('mapreduce.job.new_reduce_attempts', INCREMENT),
    'runningReduceAttempts': ('mapreduce.job.running_reduce_attempts', INCREMENT),
    'failedReduceAttempts': ('mapreduce.job.failed_reduce_attempts', INCREMENT),
    'killedReduceAttempts': ('mapreduce.job.killed_reduce_attempts', INCREMENT),
    'successfulReduceAttempts': ('mapreduce.job.successful_reduce_attempts', INCREMENT),
    'newMapAttempts': ('mapreduce.job.new_map_attempts', INCREMENT),
    'runningMapAttempts': ('mapreduce.job.running_map_attempts', INCREMENT),
    'failedMapAttempts': ('mapreduce.job.failed_map_attempts', INCREMENT),
    'killedMapAttempts': ('mapreduce.job.killed_map_attempts', INCREMENT),
    'successfulMapAttempts': ('mapreduce.job.successful_map_attempts', INCREMENT),
}

MAPREDUCE_JOB_COUNTER_METRICS = {
    'reduceCounterValue': ('mapreduce.job.counter.reduce_counter_value', INCREMENT),
    'mapCounterValue': ('mapreduce.job.counter.map_counter_value', INCREMENT),
    'totalCounterValue': ('mapreduce.job.counter.total_counter_value', INCREMENT),
}

MAPREDUCE_MAP_TASK_METRICS = {
    'elapsedTime': ('mapreduce.job.map.task.elapsed_time', HISTOGRAM)
}

MAPREDUCE_REDUCE_TASK_METRICS = {
    'elapsedTime': ('mapreduce.job.reduce.task.elapsed_time', HISTOGRAM)
}


class MapReduceCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Parse job specific counters
        self.general_counters = self._parse_general_counters(init_config)

        # Parse job specific counters
        self.job_specific_counters = self._parse_job_specific_counters(init_config)

    def check(self, instance):
        # Get properties from conf file
        rm_address = instance.get('resourcemanager_uri')
        if rm_address is None:
            raise Exception('The ResourceManager URL must be specified in the instance configuration')

        collect_task_metrics = _is_affirmative(instance.get('collect_task_metrics', False))

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

        # Get the running MR applications from YARN
        running_apps = self._get_running_app_ids(rm_address)

        # Report success after gathering all metrics from ResourceManaager
        self.service_check(YARN_SERVICE_CHECK,
            AgentCheck.OK,
            tags=['url:%s' % rm_address],
            message='Connection to ResourceManager "%s" was successful' % rm_address)

        # Get the applications from the application master
        running_jobs = self._mapreduce_job_metrics(running_apps, tags)

        # # Get job counter metrics
        self._mapreduce_job_counters_metrics(running_jobs, tags)

        # Get task metrics
        if collect_task_metrics:
            self._mapreduce_task_metrics(running_jobs, tags)

        # Report success after gathering all metrics from Application Master
        if running_jobs:
            job_id, metrics = running_jobs.items()[0]
            am_address = self._get_url_base(metrics['tracking_url'])

            self.service_check(MAPREDUCE_SERVICE_CHECK,
                AgentCheck.OK,
                tags=['url:%s' % am_address],
                message='Connection to ApplicationManager "%s" was successful' % am_address)

    def _parse_general_counters(self, init_config):
        '''
        Return a dictionary for each job counter
        {
          counter_group_name: [
              counter_name
            ]
          }
        }
        '''
        job_counter = {}

        if init_config.get('general_counters'):

            # Parse the custom metrics
            for counter_group in init_config['general_counters']:
                counter_group_name = counter_group.get('counter_group_name')
                counters = counter_group.get('counters')

                if not counter_group_name:
                    raise Exception('"general_counters" must contain a valid "counter_group_name"')

                if not counters:
                    raise Exception('"general_counters" must contain a list of "counters"')

                # Add the counter_group to the job_counters if it doesn't already exist
                if counter_group_name not in job_counter:
                    job_counter[counter_group_name] = []

                for counter in counters:
                    counter_name = counter.get('counter_name')

                    if not counter_name:
                        raise Exception('At least one "counter_name" should be specified in the list of "counters"')

                    job_counter[counter_group_name].append(counter_name)

        return job_counter

    def _parse_job_specific_counters(self, init_config):
        '''
        Return a dictionary for each job counter
        {
          job_name: {
            counter_group_name: [
                counter_name
              ]
            }
          }
        }
        '''
        job_counter = {}

        if init_config.get('job_specific_counters'):

            # Parse the custom metrics
            for job in init_config['job_specific_counters']:
                job_name = job.get('job_name')
                metrics = job.get('metrics')

                if not job_name:
                    raise Exception('Counter metrics must have a "job_name"')

                if not metrics:
                    raise Exception('Jobs specified in counter metrics must contain at least one metric')

                # Add the job to the custom metrics if it doesn't already exist
                if job_name not in job_counter:
                    job_counter[job_name] = {}

                for metric in metrics:
                    counter_group_name = metric.get('counter_group_name')
                    counters = metric.get('counters')

                    if not counter_group_name:
                        raise Exception('Each counter metric must contain a valid "counter_group_name"')

                    if not counters:
                        raise Exception('Each counter metric must contain a list of "counters"')

                    # Add the counter group name if it doesn't exist for the current job
                    if counter_group_name not in job_counter[job_name]:
                        job_counter[job_name][counter_group_name] = []

                    for counter in counters:
                        counter_name = counter.get('counter_name')

                        if not counter_name:
                            raise Exception('At least one "counter_name" should be specified in the list of "counters"')

                        job_counter[job_name][counter_group_name].append(counter_name)

        return job_counter

    def _get_running_app_ids(self, rm_address, **kwargs):
        '''
        Return a dictionary of {app_id: (app_name, tracking_url)} for the running MapReduce applications
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

    def _mapreduce_job_metrics(self, running_apps, addl_tags):
        '''
        Get metrics for each MapReduce job.
        Return a dictionary for each MapReduce job
        {
          job_id: {
            'job_name': job_name,
            'app_name': app_name,
            'user_name': user_name,
            'tracking_url': tracking_url
        }
        '''
        running_jobs = {}

        for app_id, (app_name, tracking_url) in running_apps.iteritems():

            metrics_json = self._rest_request_to_json(tracking_url,
                MAPREDUCE_JOBS_PATH,
                MAPREDUCE_SERVICE_CHECK)

            if metrics_json.get('jobs'):
                if metrics_json['jobs'].get('job'):

                    for job_json in metrics_json['jobs']['job']:
                        job_id = job_json.get('id')
                        job_name = job_json.get('name')
                        user_name = job_json.get('user')

                        if job_id and job_name and user_name:

                            # Build the structure to hold the information for each job ID
                            running_jobs[str(job_id)] = {'job_name': str(job_name),
                                                    'app_name': str(app_name),
                                                    'user_name': str(user_name),
                                                    'tracking_url': self._join_url_dir(tracking_url, MAPREDUCE_JOBS_PATH, job_id)}

                            tags = ['app_name:' + str(app_name),
                                    'user_name:' + str(user_name),
                                    'job_name:' + str(job_name)]

                            tags.extend(addl_tags)

                            self._set_metrics_from_json(tags, job_json, MAPREDUCE_JOB_METRICS)

        return running_jobs

    def _mapreduce_job_counters_metrics(self, running_jobs, addl_tags):
        '''
        Get custom metrics specified for each counter
        '''
        for job_id, job_metrics in running_jobs.iteritems():
            job_name = job_metrics['job_name']

            # Check if the job_name exist in the custom metrics
            if self.general_counters or (job_name in self.job_specific_counters):
                job_specific_metrics = self.job_specific_counters.get(job_name)

                metrics_json = self._rest_request_to_json(job_metrics['tracking_url'],
                    'counters',
                    MAPREDUCE_SERVICE_CHECK)

                if metrics_json.get('jobCounters'):
                    if metrics_json['jobCounters'].get('counterGroup'):

                        # Cycle through all the counter groups for this job
                        for counter_group in metrics_json['jobCounters']['counterGroup']:
                            group_name = counter_group.get('counterGroupName')

                            if group_name:
                                counter_metrics = set([])

                                # Add any counters in the job specific metrics
                                if job_specific_metrics and group_name in job_specific_metrics:
                                    counter_metrics = counter_metrics.union(job_specific_metrics[group_name])

                                # Add any counters in the general metrics
                                if group_name in self.general_counters:
                                    counter_metrics = counter_metrics.union(self.general_counters[group_name])

                                if counter_metrics:
                                    # Cycle through all the counters in this counter group
                                    if counter_group.get('counter'):
                                        for counter in counter_group['counter']:
                                            counter_name = counter.get('name')

                                            # Check if the counter name is in the custom metrics for this group name
                                            if counter_name and counter_name in counter_metrics:
                                                tags = ['app_name:' + job_metrics.get('app_name'),
                                                        'user_name:' + job_metrics.get('user_name'),
                                                        'job_name:' + job_name,
                                                        'counter_name:' + str(counter_name).lower()]

                                                tags.extend(addl_tags)

                                                self._set_metrics_from_json(tags,
                                                    counter,
                                                    MAPREDUCE_JOB_COUNTER_METRICS)

    def _mapreduce_task_metrics(self, running_jobs, addl_tags):
        '''
        Get metrics for each MapReduce task
        Return a dictionary of {task_id: 'tracking_url'} for each MapReduce task
        '''
        for job_id, job_stats in running_jobs.iteritems():

            metrics_json = self._rest_request_to_json(job_stats['tracking_url'],
                    'tasks',
                    MAPREDUCE_SERVICE_CHECK)

            if metrics_json.get('tasks'):
                if metrics_json['tasks'].get('task'):

                    for task in metrics_json['tasks']['task']:
                        task_type = task.get('type')

                        if task_type:
                            tags = ['app_name:' + job_stats['app_name'],
                                    'user_name:' + job_stats['user_name'],
                                    'job_name:' + job_stats['job_name'],
                                    'task_type:' + str(task_type).lower()]

                            tags.extend(addl_tags)

                            if task_type == 'MAP':
                                self._set_metrics_from_json(tags, task, MAPREDUCE_MAP_TASK_METRICS)

                            elif task_type == 'REDUCE':
                                self._set_metrics_from_json(tags, task, MAPREDUCE_REDUCE_TASK_METRICS)

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

    def _set_metric(self, metric_name, metric_type, value, tags=None, device_name=None):
        '''
        Set a metric
        '''
        if metric_type == HISTOGRAM:
            self.histogram(metric_name, value, tags=tags, device_name=device_name)
        elif metric_type == INCREMENT:
            self.increment(metric_name, value, tags=tags, device_name=device_name)
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
