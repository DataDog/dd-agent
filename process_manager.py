from multiprocessing import Lock, Process, Queue
from Queue import Empty
import time
import logging
import traceback

TIMEOUT = 240
log = logging.getLogger('process_manager')

def run_parallel(check_cls, instance, lock, metrics_queue, events_queue,
     status_queue, shared_queue, shared_object):
    try:
        status_queue.put("Started")
        
        check_cls.set_shared(shared_object)
        check_cls.check(instance)
        
        status_queue.put("Check Done")
        
        lock.acquire()
        
        metrics = check_cls.get_metrics()
        events = check_cls.get_events()
        
        metrics_queue.put(metrics)
        events_queue.put(events)
        shared_queue.put(check_cls.get_shared())
        status_queue.put("Done")
        
        lock.release()
    
    except Exception, e:
        log.error(e)

class ProcessManager():

    @classmethod
    def instance(cls):
        try:
            return cls._instance
        except AttributeError:
            cls._instance = cls()
            return cls._instance

    def __init__(self):
        # To keep informations about all the processes
        self.processes = {}
        
        self.lock = Lock()
        
        # To store the objects that will be shared over the processes for 
        # a given instance
        self.shared_objects = {}

    def _clean(self):
        keys_to_remove = []
        for key in self.processes.keys():
            if time.time() - self.processes[key]['start_time'] > TIMEOUT:
                p = self.processes[key]['process']
                p.terminate()
                p.join()
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.processes[key]


    def run_parallel(self, check_cls, instance):
        key = check_cls.name+str(instance)
        
        # If there is already a process running with the same instance 
        # we do nothing
        if key not in self.processes:
            try:

                #Will be used to share data from check process to main process
                metrics_queue = Queue()
                events_queue = Queue()
                status_queue = Queue()
                shared_queue = Queue()


                p = Process(target=run_parallel, args=(check_cls, instance, 
                    self.lock, metrics_queue, events_queue, status_queue, 
                    shared_queue, self.shared_objects.get(key, None)))
                p.start()
                
                # We store information about the created process
                self.processes[key]={'process':p, 
                                    'start_time':time.time(),
                                    'metrics_queue': metrics_queue,
                                    'events_queue':events_queue,
                                    'status_queue':status_queue,
                                    'status': self.get_status(key),
                                    'shared_queue':shared_queue,
                                    }
            except Exception, e:
                log.error(traceback.format_exc())
                log.error(e)

        # If some process are stuck it will kill them
        self._clean()

    def _get_metrics(self, key):
        return self.processes[key]['metrics_queue'].get()

    def _get_events(self, key):
        return self.processes[key]['events_queue'].get()

    def get_metrics_and_events(self, check_cls, instance):
        key = check_cls.name+str(instance)
        if key in self.processes.keys() and self.is_process_finished(key):
            self.processes[key]['process'].join()
            metrics = self._get_metrics(key)
            events = self._get_events(key)

            # We fetch the object that will be shared over all the processes
            # running the same instance and we store it to send it to the next
            # process
            self.shared_objects[key] = self._get_shared_object(key)
            
            del self.processes[key]
            return metrics, events
        return [], []


    def get_status(self, key):
        status = None
        if key in self.processes.keys():
            old_status = self.processes[key]['status']
            while True:
                try:
                    # We don't want this call to block the process so we use 
                    # block=False
                    status = self.processes[key]['status_queue'].get(block=False)
                except Empty:
                    break
            if status is not None:
                self.processes[key]['status'] = status
            else:
                status = old_status
            self.processes[key]['status'] = status

        return status

    def _get_shared_object(self, key):
        if key in self.processes.keys():
            return self.processes[key]['shared_queue'].get()

    def is_process_finished(self, key):
        if self.get_status(key)=="Done":
            return True
        else:
            return False
