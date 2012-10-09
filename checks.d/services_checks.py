from checks import AgentCheck
from util import headers
import urllib2
import time
import socket
import logging

EVENT_TYPE = SOURCE_TYPE_NAME = 'servicecheck'

class Status:
    DOWN = "DOWN"
    UP = "UP"

class ServicesCheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        # A dictionnary to keep track of service statuses
        self.statuses = {}
        
    def _create_event(self, status, msg, url, name):
        if status==Status.DOWN:
            title = "Alert: %s is Down" % name
            alert_type = "error"
            msg = "%%%%%%\n * %s has just been reported %s \n * URL: %s \n * Reporting agent: %s \n * Error: %s \n%%%%%%" \
                    % (name, status, url, self.hostname, msg)

        else:
            title = "Alert: %s recovered" % name
            alert_type = "info"
            msg = "%%%%%%\n * %s has just been reported %s \n * URL: %s \n * Reporting agent: %s \n%%%%%%" \
                    % (name, url, status, self.hostname)

        self.event({
             'timestamp': int(time.time()),
             'event_type': EVENT_TYPE,
             'host': self.hostname,
             'api_key': self.agentConfig['api_key'],
             'msg_text': msg,
             'msg_title': title,
             'alert_type': alert_type,
             "source_type_name": SOURCE_TYPE_NAME,
             "event_object": url,
        })


    def check(self, instance):
        url = instance.get('url', None)
        connect_type = instance.get('type', None)
        name = instance.get('name', None)

        if url is None or connect_type not in ['http', 'tcp']:
            return False

        if connect_type=='http':
            status, msg = _check_http(url, instance, self.agentConfig, self.log)

        if connect_type=='tcp':
            status, msg = _check_tcp(url, instance, self.agentConfig, self.log)

        if self.statuses.get(name, None) is None and status == Status.DOWN:
            # First time the check is run since agent startup and the service is down
            # We trigger an event
            self.statuses[name] = status
            self._create_event(status, msg, url, name)

        if self.statuses.get(name, None) is None and status == Status.UP:
            # First time the check is run since agent startup and the service is UP
            # We don't trigger an event
            self.statuses[name] = status

        if self.statuses[name] != status:
            # There is a change in the state versus previous state
            # We trigger an event
            self.statuses[name] = status
            self._create_event(status, msg, url, name)

    def set_shared(self, shared_object):
        """
        Overriden by the check class. Used when you want to parallelize the checks over
        your instances. This object will be shared over the iterations of your check.
        """
        if shared_object is not None:
            self.statuses = shared_object

    def get_shared(self):
        """
        Overriden by the check class. Used when you want to parallelize the checks over
        your instances. This object will be shared over the iterations of your check.
        """
        return self.statuses



def _check_tcp(url, instance, agentConfig, log):
    socket_type = None

    port = instance.get('port', None)
    try:
        port = int(port)
    except Exception:
        log.error("A correct port must be specified")
        return False

    split = url.split(":")
    if len(split) == 8:
        for block in split:
            if len(block) != 4:
                log.error("%s is not a correct IPv6 address." % url)
                return False
        addr = url
        socket_type = socket.AF_INET6
        
    if socket_type is None:
        try:
            addr = socket.gethostbyname(url)
            socket_type = socket.AF_INET
        except Exception:
            log.error("URL: %s is not a correct IPv4, IPv6 or hostname" % url)
            return False

    try:
        log.debug("Connecting to %s %s" % (addr, port))
        sock = socket.socket(socket_type)
        sock.settimeout(int(instance.get('timeout', 10)))
        sock.connect((addr, port))
        sock.close()

    except Exception, e:
        log.info("%s:%s is down" % (url, port))
        return Status.DOWN, str(e)

    log.info("%s:%s is UP" % (url, port))
    return Status.UP, "UP"

def _check_http(url, instance, agentConfig, log):
    try:
        log.debug("Connecting to %s" % url)
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, url, username, password)
        authhandler = urllib2.HTTPBasicAuthHandler(passman)
        opener = urllib2.build_opener(authhandler)
        urllib2.install_opener(opener)
        req = urllib2.Request(url, None, headers(agentConfig))
        request = urllib2.urlopen(req, timeout=timeout)
    
    except urllib2.URLError, e:
        log.info("%s is DOWN" % url)
        return Status.DOWN, str(e)

    except  urllib2.HTTPError, e:
        if int(e.code) >= 400:
            log.info("%s is DOWN" % url)
            return Status.DOWN, str(e)

    except Exception, e:
        log.error("Unhandled exception %s" % str(e))
        return False

    log.info("%s is UP" % url)
    return Status.UP, "UP"
