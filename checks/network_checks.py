# stdlib
from collections import defaultdict
import threading
import time
from Queue import Queue, Empty

# project
from config import _is_affirmative
from checks import AgentCheck

# 3rd party
from checks.libs.thread_pool import Pool

TIMEOUT = 180
DEFAULT_SIZE_POOL = 6
MAX_LOOP_ITERATIONS = 1000
FAILURE = "FAILURE"

class Status:
    DOWN = "DOWN"
    WARNING = "WARNING"
    UP = "UP"

class EventType:
    DOWN = "servicecheck.state_change.down"
    UP = "servicecheck.state_change.up"


class NetworkCheck(AgentCheck):
    SOURCE_TYPE_NAME = 'servicecheck'
    SERVICE_CHECK_PREFIX = 'network_check'

    STATUS_TO_SERVICE_CHECK = {
            Status.UP  : AgentCheck.OK,
            Status.WARNING : AgentCheck.WARNING,
            Status.DOWN : AgentCheck.CRITICAL
        }

    """
    Services checks inherits from this class.
    This class should never be directly instanciated.

    Work flow:
        The main agent loop will call the check function for each instance for
        each iteration of the loop.
        The check method will make an asynchronous call to the _process method in
        one of the thread initiated in the thread pool created in this class constructor.
        The _process method will call the _check method of the inherited class
        which will perform the actual check.

        The _check method must return a tuple which first element is either
            Status.UP or Status.DOWN.
            The second element is a short error message that will be displayed
            when the service turns down.

    """

    def __init__(self, name, init_config, agentConfig, instances):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # A dictionary to keep track of service statuses
        self.statuses = {}
        self.notified = {}
        self.nb_failures = 0
        self.pool_started = False

        # Make sure every instance has a name that we use as a unique key
        # to keep track of statuses
        names = []
        for inst in instances:
            if 'name' not in inst:
                raise Exception("All instances should have a 'name' parameter,"
                                " error on instance: {0}".format(inst))
            if inst['name'] in names:
                raise Exception("Duplicate names for instances with name {0}"
                                .format(inst['name']))

    def stop(self):
        self.stop_pool()
        self.pool_started = False

    def start_pool(self):
        # The pool size should be the minimum between the number of instances
        # and the DEFAULT_SIZE_POOL. It can also be overridden by the 'threads_count'
        # parameter in the init_config of the check
        self.log.info("Starting Thread Pool")
        default_size = min(self.instance_count(), DEFAULT_SIZE_POOL)
        self.pool_size = int(self.init_config.get('threads_count', default_size))

        self.pool = Pool(self.pool_size)

        self.resultsq = Queue()
        self.jobs_status = {}
        self.pool_started = True

    def stop_pool(self):
        self.log.info("Stopping Thread Pool")
        if self.pool_started:
            self.pool.terminate()
            self.pool.join()
            self.jobs_status.clear()
            assert self.pool.get_nworkers() == 0

    def restart_pool(self):
        self.stop_pool()
        self.start_pool()

    def check(self, instance):
        if not self.pool_started:
            self.start_pool()
        if threading.activeCount() > 5 * self.pool_size + 5: # On Windows the agent runs on multiple threads so we need to have an offset of 5 in case the pool_size is 1
            raise Exception("Thread number (%s) is exploding. Skipping this check" % threading.activeCount())
        self._process_results()
        self._clean()
        name = instance.get('name', None)
        if name is None:
            self.log.error('Each service check must have a name')
            return

        if name not in self.jobs_status:
            # A given instance should be processed one at a time
            self.jobs_status[name] = time.time()
            self.pool.apply_async(self._process, args=(instance,))
        else:
            self.log.error("Instance: %s skipped because it's already running." % name)

    def _process(self, instance):
        try:
            statuses = self._check(instance)

            if isinstance(statuses, tuple):
                # Assume the check only returns one service check
                status, msg = statuses
                self.resultsq.put((status, msg, None, instance))

            elif isinstance(statuses, list):
                for status in statuses:
                    sc_name, status, msg = status
                    self.resultsq.put((status, msg, sc_name, instance))

        except Exception:
            result = (FAILURE, FAILURE, FAILURE, FAILURE)
            self.resultsq.put(result)

    def _process_results(self):
        for i in range(MAX_LOOP_ITERATIONS):
            try:
                # We want to fetch the result in a non blocking way
                status, msg, sc_name, instance = self.resultsq.get_nowait()
            except Empty:
                break

            if status == FAILURE:
                self.nb_failures += 1
                if self.nb_failures >= self.pool_size - 1:
                    self.nb_failures = 0
                    self.restart_pool()
                continue
            self.report_as_service_check(sc_name, status, instance, msg)

            # FIXME: 5.3, this has been deprecated before, get rid of events
            # Don't create any event to avoid duplicates with server side
            # service_checks
            skip_event = _is_affirmative(instance.get('skip_event', False))
            instance_name = instance['name']
            if not skip_event:
                self.warning("Using events for service checks is deprecated in favor of monitors and will be removed in future versions of the Datadog Agent.")
                event = None

                if instance_name not in self.statuses:
                    self.statuses[instance_name] = defaultdict(list)

                self.statuses[instance_name][sc_name].append(status)

                window = int(instance.get('window', 1))

                if window > 256:
                    self.log.warning("Maximum window size (256) exceeded, defaulting it to 256")
                    window = 256

                threshold = instance.get('threshold', 1)

                if len(self.statuses[instance_name][sc_name]) > window:
                    self.statuses[instance_name][sc_name].pop(0)

                nb_failures = self.statuses[instance_name][sc_name].count(Status.DOWN)

                if nb_failures >= threshold:
                    if self.notified.get((instance_name, sc_name), Status.UP) != Status.DOWN:
                        event = self._create_status_event(sc_name, status, msg, instance)
                        self.notified[(instance_name, sc_name)] = Status.DOWN
                else:
                    if self.notified.get((instance_name, sc_name), Status.UP) != Status.UP:
                        event = self._create_status_event(sc_name, status, msg, instance)
                        self.notified[(instance_name, sc_name)] = Status.UP

                if event is not None:
                    self.events.append(event)

            # The job is finished here, this instance can be re processed
            if instance_name in self.jobs_status:
                del self.jobs_status[instance_name]

    def _check(self, instance):
        """This function should be implemented by inherited classes"""
        raise NotImplementedError


    def _clean(self):
        now = time.time()
        for name in self.jobs_status.keys():
            start_time = self.jobs_status[name]
            if now - start_time > TIMEOUT:
                self.log.critical("Restarting Pool. One check is stuck: %s" % name)
                self.restart_pool()
                break
