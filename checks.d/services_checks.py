from checks import AgentCheck
from util import headers
import urllib2
import time
import socket
import logging
from Queue import Queue
import hashlib

from thread_pool import Pool

EVENT_TYPE = SOURCE_TYPE_NAME = 'servicecheck'
TIMEOUT = 150

class Status:
    DOWN = "DOWN"
    UP = "UP"

class BadConfException(Exception): pass


class ServicesCheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        # A dictionnary to keep track of service statuses
        self.statuses = {}
        self._init_pool()

    def _init_pool(self):
        self.pool = Pool(int(self.init_config.get('nb_workers', 4)))
        self.eventsq = Queue()
        self.jobs_status = {}

    def restart_pool(self):
        self.pool.terminate()
        self._init_pool()

    def _clean(self):
        now = time.time()
        stuck_process = None
        stuck_time = time.time()
        for key in self.jobs_status.keys():
            start_time = self.jobs_status[key]
            # We find the oldest job
            if now - start_time > TIMEOUT and start_time < stuck_time:
                stuck_process = key
                stuck_time = start_time

        if stuck_process is not None:
            self.restart_pool()
            self.log.critical("Restarting Pool. One check is stuck.")

    def _generate_key(self, instance):
        return hashlib.md5(str(instance)).digest()[:8]
        
    def _create_status_event(self, status, msg, instance):
        url = instance.get('url', None)
        name = instance.get('name', None)

        if status == Status.DOWN:
            title = "Alert: %s is Down" % name
            alert_type = "error"
            msg = "%%%%%%\n * %s has just been reported %s \n * URL: %s \n * Reporting agent: %s \n * Error: %s \n%%%%%%" \
                    % (name, status, url, self.hostname, msg)

        else:
            title = "Alert: %s recovered" % name
            alert_type = "info"
            msg = "%%%%%%\n * %s has just been reported %s \n * URL: %s \n * Reporting agent: %s \n%%%%%%" \
                    % (name, url, status, self.hostname)

        return {
             'timestamp': int(time.time()),
             'event_type': EVENT_TYPE,
             'host': self.hostname,
             'api_key': self.agentConfig['api_key'],
             'msg_text': msg,
             'msg_title': title,
             'alert_type': alert_type,
             "source_type_name": SOURCE_TYPE_NAME,
             "event_object": name,
        }

    def _load_tcp_conf(self, instance):
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
        except:
            raise BadConfException("A valid url must be specified")

        if len(split) == 8:
            for block in split:
                if len(block) != 4:
                    raise BadConfException("%s is not a correct IPv6 address." % url)

            addr = url
            socket_type = socket.AF_INET6
            
        if socket_type is None:
            try:
                addr = socket.gethostbyname(url)
                socket_type = socket.AF_INET
            except Exception:
                raise BadConfException("URL: %s is not a correct IPv4, IPv6 or hostname" % url)

        return addr, port, timeout, socket_type

    def _load_http_conf(self, instance):
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        url = instance.get('url', None)
        return url, username, password, timeout

    def check(self, instance):
        self._clean()
        key = self._generate_key(instance)
        if key not in self.jobs_status:
            self.jobs_status[key] = time.time()
            self.pool.apply_async(self._process, args=(instance,), 
                callback=self._job_finished)

        time.sleep(1)
        for i in range(self.eventsq.qsize()):
            event, instance = self.eventsq.get_nowait()
            self.events.append(event)
            del self.jobs_status[self._generate_key(instance)]

    def _job_finished(self, result):
        if result[0] is not None:
            self.eventsq.put(result)

    def _process(self, instance):
        event = None
        connect_type = instance.get('type', None)
        name = instance.get('name', None)

        if connect_type not in ['http', 'tcp']:
            self.log.error("The service type must be 'http' or 'tcp'")
            return None

        try:
            if connect_type == 'http':
                addr, username, password, timeout = self._load_http_conf(instance)
                status, msg = self._check_http(addr, username, password, timeout)

            if connect_type == 'tcp':
                addr, port, timeout, socket_type = self._load_tcp_conf(instance)
                status, msg = self._check_tcp(addr, port, socket_type, timeout)

            if self.statuses.get(name, None) is None and status == Status.DOWN:
                # First time the check is run since agent startup and the service is down
                # We trigger an event
                self.statuses[name] = status
                event = self._create_status_event(status, msg, instance)

            if self.statuses.get(name, None) is None and status == Status.UP:
                # First time the check is run since agent startup and the service is UP
                # We don't trigger an event
                self.statuses[name] = status

            if self.statuses[name] != status:
                # There is a change in the state versus previous state
                # We trigger an event
                self.statuses[name] = status
                event =self._create_status_event(status, msg, instance)

        except Exception, e:
            self.log.exception(e)

        return (event,instance)


    def _check_tcp(self, addr, port, socket_type, timeout=10):
        try:
            self.log.debug("Connecting to %s %s" % (addr, port))
            sock = socket.socket(socket_type)
            sock.settimeout(timeout)
            sock.connect((addr, port))
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
            request = urllib2.urlopen(req, timeout=timeout)
        
        except urllib2.URLError, e:
            self.log.info("%s is DOWN" % addr)
            return Status.DOWN, str(e)

        except  urllib2.HTTPError, e:
            if int(e.code) >= 400:
                self.log.info("%s is DOWN" % addr)
                return Status.DOWN, str(e)

        except Exception, e:
            self.log.error("Unhandled exception %s" % str(e))
            return False

        self.log.info("%s is UP" % addr)
        return Status.UP, "UP"
