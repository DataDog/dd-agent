from checks import AgentCheck
import time
from Queue import Queue
from thread_pool import Pool

SOURCE_TYPE_NAME = 'servicecheck'

TIMEOUT = 120
DEFAULT_SIZE_POOL = 6

class Status:
    DOWN = "DOWN"
    UP = "UP"

class EventType:
    DOWN = "servicecheck.state_change.down"
    UP = "servicecheck.state_change.up"


class ServicesCheck(AgentCheck):
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
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        # A dictionnary to keep track of service statuses
        self.statuses = {}
        self._init_pool()

    def _init_pool(self):
        # The pool size should be the minimum between the number of instances
        # and the DEFAULT_SIZE_POOL. It can also be overriden by the 'nb_threads'
        # parameter in the init_config of the check
        pool_size = int(self.init_config.get('threads_count', 
            min([self.init_config.get('instances_number', DEFAULT_SIZE_POOL), 
                DEFAULT_SIZE_POOL])))
        self.pool = Pool(pool_size)

        self.resultsq = Queue()
        self.jobs_status = {}

    def stop_pool(self):
        self.pool.terminate()

    def restart_pool(self):
        self.stop_pool()
        self._init_pool()

    def check(self, instance):
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
            self.log.exception(e)
            self.restart_pool()

    def _process_results(self):
        for i in range(1000):
            try:
                # We want to fetch the result in a non blocking way
                status, msg, name, queue_instance = self.resultsq.get_nowait()
            except Exception:
                break

            event = None

            if self.statuses.get(name, None) is None and status == Status.DOWN:
                # First time the check is run since agent startup and the service is down
                # We trigger an event
                self.statuses[name] = status
                event = self._create_status_event(status, msg, queue_instance)

            elif self.statuses.get(name, Status.UP) != status:
                # There is a change in the state versus previous state
                # We trigger an event
                self.statuses[name] = status
                event = self._create_status_event(status, msg, queue_instance)

            else:
                # Either it's the first time the check is run and the service is up
                # or there is no change in the status
                self.statuses[name] = status

            if event is not None:
                self.events.append(event)

            # The job is finish here, this instance can be re processed
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
                
    def _create_status_event(self, status, msg, instance):
        msg = msg.replace("<", "")
        msg = msg.replace(">", "")


        custom_message = instance.get('message', None)
        if custom_message is not None:
            custom_message = "\n * Message: %s " % custom_message
        else:
            custom_message = ""

        self.log.info(msg)

        url = instance.get('url', None)
        name = instance.get('name', None)
        notify = instance.get('notify', self.init_config.get('notify', []))
        notify_message = ""
        notify_list = []
        for handle in notify:
            notify_list.append("@%s" % handle.strip())
        notify_message = " ".join(notify_list)

        if status == Status.DOWN:
            title = "Alert: %s is Down" % name
            alert_type = "error"
            msg = "%s \n %%%%%%\n * %s has just been reported %s \n * URL: %s \n * Reporting agent: %s \n * Error: %s %s \n %%%%%%" \
                    % (notify_message, name, status, url, self.hostname, msg, custom_message)
            event_type = EventType.DOWN

        else: # Status is UP
            title = "Alert: %s recovered" % name
            alert_type = "info"
            msg = "%s \n %%%%%%\n * %s has just been reported %s \n * URL: %s \n * Reporting agent: %s %s \n %%%%%%" \
                    % (notify_message, name, status, url, self.hostname, custom_message)
            event_type = EventType.UP

        return {
             'timestamp': int(time.time()),
             'event_type': event_type,
             'host': self.hostname,
             'api_key': self.agentConfig['api_key'],
             'msg_text': msg,
             'msg_title': title,
             'alert_type': alert_type,
             "source_type_name": SOURCE_TYPE_NAME,
             "event_object": name,
        }

   