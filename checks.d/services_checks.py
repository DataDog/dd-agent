from checks import AgentCheck
from util import headers
import urllib2
import time
import socket
import logging
from Queue import Queue
import hashlib

from thread_pool import Pool

SOURCE_TYPE_NAME = 'servicecheck'

TIMEOUT = 180

class Status:
    DOWN = "DOWN"
    UP = "UP"

class EventType:
    DOWN = "servicecheck.state_change.down"
    UP = "servicecheck.state_change.up"

class BadConfException(Exception): pass


class ServicesCheck(AgentCheck):
    """
    Work flow:
        This class is instanciated ONCE during the whole agent life
        The main agent loop will call the check function for each instance for 
        each iteration of the loop.
        The check method will make an asynchronous call to the _process method in 
        one of the thread initiated in the thread pool created in this class constructor.

    """
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        # A dictionnary to keep track of service statuses
        self.statuses = {}
        self._init_pool()

    def _init_pool(self):
        self.pool = Pool(int(self.init_config.get('nb_threads', 4)))
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
        connect_type = instance.get('type', None)
        name = instance.get('name', None)

        if connect_type not in ['http', 'tcp']:
            self.log.error("The service type must be 'http' or 'tcp'")
            return (None, None, None, None)

        try:
            if connect_type == 'http':
                addr, username, password, timeout = self._load_http_conf(instance)
                status, msg = self._check_http(addr, username, password, timeout)

            if connect_type == 'tcp':
                addr, port, timeout, socket_type = self._load_tcp_conf(instance)
                status, msg = self._check_tcp(addr, port, socket_type, timeout)

            result = (status, msg, name, instance)
            # We put the results in the result queue
            self.resultsq.put(result)

        except Exception, e:
            self.log.exception(e)

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
        url = instance.get('url', None)
        name = instance.get('name', None)
        notify = instance.get('notify', self.init_config.get('notify', None))
        notify_message = ""
        if notify is not None:
            notify_list = []
            for handle in notify.split(','):
                notify_list.append("@%s" % handle.strip())
            notify_message = " ".join(notify_list)

        if status == Status.DOWN:
            title = "Alert: %s is Down" % name
            alert_type = "error"
            msg = "%s \n %%%%%%\n * %s has just been reported %s \n * URL: %s \n * Reporting agent: %s \n * Error: %s \n %%%%%%" \
                    % (notify_message, name, status, url, self.hostname, msg)
            event_type = EventType.DOWN

        else: # Status is UP
            title = "Alert: %s recovered" % name
            alert_type = "info"
            msg = "%s \n %%%%%%\n * %s has just been reported %s \n * URL: %s \n * Reporting agent: %s \n %%%%%%" \
                    % (notify_message, name, url, status, self.hostname)
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

    def _load_tcp_conf(self, instance):
        # Fetches the conf

        port = instance.get('port', None)
        timeout = int(instance.get('timeout', 10))
        socket_type = None
        try:
            port = int(port)
        except Exception:
            raise BadConfException("%s is not a correct port." % str(port))

        try:
            url = instance.get('url', None)
            split = url.split(":")
        except Exception: # Would be raised if url is not a string 
            raise BadConfException("A valid url must be specified")

        # IPv6 address format: 2001:db8:85a3:8d3:1319:8a2e:370:7348
        if len(split) == 8: # It may then be a IP V8 address, we check that
            for block in split:
                if len(block) != 4:
                    raise BadConfException("%s is not a correct IPv6 address." % url)

            addr = url
            # It's a correct IP V6 address
            socket_type = socket.AF_INET6
            
        if socket_type is None:
            try:
                addr = socket.gethostbyname(url)
                socket_type = socket.AF_INET
            except Exception:
                raise BadConfException("URL: %s is not a correct IPv4, IPv6 or hostname" % url)

        return addr, port, timeout, socket_type

    def _load_http_conf(self, instance):
        # Fetches the conf
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        url = instance.get('url', None)
        return url, username, password, timeout

    def _check_tcp(self, addr, port, socket_type, timeout=10):
        try:
            self.log.debug("Connecting to %s %s" % (addr, port))
            sock = socket.socket(socket_type)
            try:
                sock.settimeout(timeout)
                sock.connect((addr, port))
            finally:
                sock.close()

        except Exception, e:
            self.log.info("%s:%s is down" % (addr, port))
            return Status.DOWN, str(e)

        self.log.info("%s:%s is UP" % (addr, port))
        return Status.UP, "UP"

    def _check_http(self, addr, username=None, password=None, timeout=10):
        try:
            self.log.debug("Connecting to %s" % addr)
            passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, addr, username, password)
            authhandler = urllib2.HTTPBasicAuthHandler(passman)
            opener = urllib2.build_opener(authhandler)
            urllib2.install_opener(opener)
            req = urllib2.Request(addr, None, headers(self.agentConfig))
            self.log.info("TIMEOUT: {0}".format(timeout))
            request = urllib2.urlopen(req, timeout=timeout)
        
        except urllib2.URLError, e:
            self.log.info("%s is DOWN" % addr)
            return Status.DOWN, str(e)

        except  urllib2.HTTPError, e:
            if int(e.code) >= 400:
                self.log.info("%s is DOWN, error code: %s" % (addr, str(e.code)))
                return Status.DOWN, str(e)

        except Exception, e:
            self.log.error("Unhandled exception %s" % str(e))
            raise

        self.log.info("%s is UP" % addr)
        return Status.UP, "UP"
