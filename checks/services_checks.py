from checks import AgentCheck
import time
from Queue import Queue, Empty
from checks.libs.thread_pool import Pool
import threading




TIMEOUT = 180
DEFAULT_SIZE_POOL = 6
MAX_LOOP_ITERATIONS = 1000
FAILURE = "FAILURE"

class Status:
    DOWN = "DOWN"
    UP = "UP"

class EventType:
    DOWN = "servicecheck.state_change.down"
    UP = "servicecheck.state_change.up"


class ServicesCheck(AgentCheck):
    SOURCE_TYPE_NAME = 'servicecheck'

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
        name = instance.get('name', None)

        try:
            status, msg = self._check(instance)

            result = (status, msg, name, instance)
            # We put the results in the result queue
            self.resultsq.put(result)

        except Exception, e:
            result = (FAILURE, FAILURE, FAILURE, FAILURE)
            self.resultsq.put(result)

    def _process_results(self):
        for i in range(MAX_LOOP_ITERATIONS):
            try:
                # We want to fetch the result in a non blocking way
                status, msg, name, queue_instance = self.resultsq.get_nowait()
            except Empty:
                break

            if status == FAILURE:
                self.nb_failures += 1
                if self.nb_failures >= self.pool_size - 1:
                    self.nb_failures = 0
                    self.restart_pool()
                continue

            event = None

            if not name in self.statuses:
                self.statuses[name] = []

            self.statuses[name].append(status)

            window = int(queue_instance.get('window', 1))

            if window > 256:
                self.log.warning("Maximum window size (256) exceeded, defaulting it to 256")
                window = 256



            threshold = queue_instance.get('threshold', 1)

            if len(self.statuses[name]) > window:
                self.statuses[name].pop(0)

            nb_failures = self.statuses[name].count(Status.DOWN)

            if nb_failures >= threshold:
                if self.notified.get(name, Status.UP) != Status.DOWN:
                    event = self._create_status_event(status, msg, queue_instance)
                    self.notified[name] = Status.DOWN
            else:
                if self.notified.get(name, Status.UP) != Status.UP:
                    event = self._create_status_event(status, msg, queue_instance)
                    self.notified[name] = Status.UP

            if event is not None:
                self.events.append(event)

            # The job is finished here, this instance can be re processed
            del self.jobs_status[name]

    def _check(self, instance):
        """This function should be implemented by inherited classes"""
        raise NotImplementedError


    def _clean(self):
        now = time.time()
        stuck_process = None
        stuck_time = time.time()
        for name in self.jobs_status.keys():
            start_time = self.jobs_status[name]
            if now - start_time > TIMEOUT:
                self.log.critical("Restarting Pool. One check is stuck.")
                self.restart_pool()
                
   
