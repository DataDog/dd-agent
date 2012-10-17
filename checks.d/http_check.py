from checks.services_checks import ServicesCheck, Status, EventType
from util import headers
import urllib2
import socket
import time

class HTTPCheck(ServicesCheck):

    def _load_conf(self, instance):
        # Fetches the conf
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        url = instance.get('url', None)
        if url is None:
            raise Exception("Bad configuration. You must specify a url")
        return url, username, password, timeout

    def _check(self, instance):
        addr, username, password, timeout = self._load_conf(instance)
        try:
            self.log.debug("Connecting to %s" % addr)
            passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, addr, username, password)
            authhandler = urllib2.HTTPBasicAuthHandler(passman)
            opener = urllib2.build_opener(authhandler)
            urllib2.install_opener(opener)
            req = urllib2.Request(addr, None, headers(self.agentConfig))
            socket.setdefaulttimeout(timeout)
            request = urllib2.urlopen(req)

        except socket.timeout, e:
            self.log.info("%s is DOWN, error: %s" % (addr, str(e)))
            return Status.DOWN, str(e)

        except urllib2.URLError, e:
            self.log.info("%s is DOWN, error: %s" % (addr, str(e)))
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

    def _create_status_event(self, status, msg, instance):
        custom_message = instance.get('message', "")
        url = instance.get('url', None)
        name = instance.get('name', None)
        notify = instance.get('notify', self.init_config.get('notify', []))
        notify_message = ""
        notify_list = []
        instance_source_type_name = instance.get('source_type', None)
        if instance_source_type_name is None:
            source_type = "%s.%s" % (ServicesCheck.SOURCE_TYPE_NAME, name)
        else:
            source_type = "%s.%s" % (ServicesCheck.SOURCE_TYPE_NAME, instance_source_type_name)
        
        for handle in notify:
            notify_list.append("@%s" % handle.strip())
        notify_message = " ".join(notify_list)

        if status == Status.DOWN:
            title = "[Alert] %s is down" % name
            alert_type = "error"
            msg = "%s \n %s \n %s reported that %s (%s) failed with %s" % (notify_message,
                custom_message, self.hostname, name, url, msg)
            event_type = EventType.DOWN

        else: # Status is UP
            title = "[Recovered] %s is up" % name
            alert_type = "success"
            msg = "%s \n %s \n %s reported that %s (%s) recovered" % (notify_message,
                custom_message, self.hostname, name,url)
            event_type = EventType.UP

        return {
             'timestamp': int(time.time()),
             'event_type': event_type,
             'host': self.hostname,
             'api_key': self.agentConfig['api_key'],
             'msg_text': msg,
             'msg_title': title,
             'alert_type': alert_type,
             "source_type_name": source_type,
             "event_object": name,
        }



