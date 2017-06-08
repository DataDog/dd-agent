# stdlib
from collections import defaultdict

# 3rd party
from redis import Redis

# project
from checks import AgentCheck


# rq prefixes that are not user configurable
QUEUE_PREFIX = 'rq:queue:'
IN_PROGRESS_PREFIX = 'rq:wip:'
DEFERRED_PREFIX = 'rq:deferred:'
FINISHED_PREFIX = 'rq:finished:'

# default queues names
QUEUES_KEY = 'rq:queues'
WORKERS_KEY = 'rq:workers'
FAILED_QUEUE = 'failed'
WORKERS_STATES = ['idle', 'started', 'suspended', 'busy']

# metrics
GAUGE_KEYS = {
    # queues status
    'jobs_enqueued': 'python_rq.queue.enqueued',
    'jobs_in_progress': 'python_rq.queue.in_progress',
    'jobs_deferred': 'python_rq.queue.deferred',
    'jobs_finished': 'python_rq.queue.finished',
    'jobs_failed': 'python_rq.queue.failed',

    # workers status
    'workers_status': 'python_rq.workers',
}


class RQCheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        # reuse the Redis connections
        self._connections = {}
        # use only meaningful connection parameters
        self._params = [
            'host', 'port', 'db', 'password', 'socket_timeout',
            'connection_pool', 'charset', 'errors', 'unix_socket_path'
        ]
        # set a default timeout (in seconds) if no timeout is specified in the instance config
        for instance in instances:
            instance['socket_timeout'] = instance.get('socket_timeout', 5)

    def _generate_instance_key(self, instance):
        """
        For the given instance, it provides a unique tuple that can be used
        to retrieve the Redis connection
        """
        if 'unix_socket_path' in instance:
            return (instance.get('unix_socket_path'), instance.get('db'))
        else:
            return (instance.get('host'), instance.get('port'), instance.get('db'))

    def _get_connection(self, instance):
        """
        Establish a connection with Redis only if (host, port) or (unix_socket_path) are
        provided. In both cases a new connection is created and the handler is stored
        in the class instance, so that it can be re-used again during the next check
        """
        if ('host' not in instance or 'port' not in instance) and 'unix_socket_path' not in instance:
            raise Exception('You must specify a host/port couple or a unix_socket_path')

        key = self._generate_instance_key(instance)
        if key not in self._connections:
            try:
                # open and store the connection handler
                connection_params = dict((k, instance[k]) for k in self._params if k in instance)
                self._connections[key] = Redis(**connection_params)
            except TypeError:
                raise Exception('You need a redis library that supports authenticated connections. Try sudo easy_install redis.')
        return self._connections[key]

    def _get_workers_status(self, connection):
        """
        Returns a dictionary with the number of workers aggregated by their status. Possible
        status are:
            * started
            * suspended
            * busy
            * idle
        These values depend on the python-rq code and are not developer configurable
        """
        workers_keys = connection.smembers(WORKERS_KEY)
        workers_status = defaultdict(int)

        for key in workers_keys:
            state = connection.hget(key, 'state')
            workers_status[state] += 1

        return workers_status

    def _get_queues_names(self, connection):
        """
        Returns a list of names for the currently active queues. It
        excludes the 'failed' queue because during the metric collection,
        failed jobs are handled differently
        """
        names = []
        queues = connection.smembers(QUEUES_KEY)
        for queue in queues:
            if FAILED_QUEUE not in queue:
                name = queue.split(':')
                if len(name) == 3:
                    names.append(name[2])

        return names

    def _get_cardinality(self, connection, name, prefix):
        """
        Returns the cardinality of the given queue. Depending on
        the type of the key, it uses the LLEN or ZCARD command
        """
        queue = '{}{}'.format(prefix, name)
        if QUEUE_PREFIX in queue:
            return connection.llen(queue)

        return connection.zcard(queue)

    def _check_queues(self, connection, queues=[], custom_tags=[]):
        """
        Agent check that collects metrics for each queue that is listed in the
        'queues' parameter. If 'queues' is an empty list, metrics for all user
        defined queues are collected.

        When a job is scheduled, it is placed in a different Redis list (or set)
        according to the job status. A hypothetical 'high_priority' queue, creates
        the following queue:
            - 'rq:queue:high_priority'
            - 'rq:wip:high_priority'
            - 'rq:deferred:high_priority'
            - 'rq:finished:high_priority'
        To achieve better metrics, all of them should be monitored and tagged according
        to the queue name.
        """
        # collect metrics for each queue except the 'failed' one
        for name in self._get_queues_names(connection):
            if not queues or name in queues:
                enqueued = self._get_cardinality(connection, name, QUEUE_PREFIX)
                in_progress = self._get_cardinality(connection, name, IN_PROGRESS_PREFIX)
                deferred = self._get_cardinality(connection, name, DEFERRED_PREFIX)
                finished = self._get_cardinality(connection, name, FINISHED_PREFIX)
                tags = ['queue:{}'.format(name)]

                self.gauge(GAUGE_KEYS['jobs_enqueued'], enqueued, tags=tags)
                self.gauge(GAUGE_KEYS['jobs_in_progress'], in_progress, tags=tags)
                self.gauge(GAUGE_KEYS['jobs_deferred'], deferred, tags=tags)
                self.gauge(GAUGE_KEYS['jobs_finished'], finished, tags=tags)

        # collect metrics for the 'failed' queue that doesn't behave such as
        # a user-defined queue
        failed_jobs = self._get_cardinality(connection, FAILED_QUEUE, QUEUE_PREFIX)
        self.gauge(GAUGE_KEYS['jobs_failed'], failed_jobs)

    def _check_workers(self, connection, custom_tags=[]):
        """
        Agent check that collects workers metrics related to their current activity
        """
        status = self._get_workers_status(connection)
        for state in WORKERS_STATES:
            value = status.get(state, 0)
            tags = ['status:{}'.format(state)] + custom_tags
            self.gauge(GAUGE_KEYS['workers_status'], value, tags=tags)

    def check(self, instance):
        connection = self._get_connection(instance)
        custom_tags = instance.get('tags', [])
        queues = instance.get('queues', [])
        # checks
        self._check_queues(connection, queues, custom_tags)
        self._check_workers(connection, custom_tags)
