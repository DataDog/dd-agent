# stdlib
import socket
import time
from urlparse import urlparse

# project
from checks.network_checks import NetworkCheck, Status, EventType
from util import headers as agent_headers

# 3rd party
from httplib2 import Http, HttpLib2Error

class HTTPCheck(NetworkCheck):

    SOURCE_TYPE_NAME = 'system'
    SERVICE_CHECK_PREFIX = 'http_check'

    def _load_conf(self, instance):
        # Fetches the conf
        tags = instance.get('tags', [])
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        config_headers = instance.get('headers',{})
        headers = agent_headers(self.agentConfig)
        headers.update(config_headers)
        url = instance.get('url', None)
        response_time = instance.get('collect_response_time', True)
        if url is None:
            raise Exception("Bad configuration. You must specify a url")
        include_content = instance.get('include_content', False)
        ssl = instance.get('disable_ssl_validation', True)
        return url, username, password, timeout, include_content, headers, response_time, tags, ssl

    def _check(self, instance):
        addr, username, password, timeout, include_content, headers, response_time, tags, disable_ssl_validation = self._load_conf(instance)
        content = ''
        start = time.time()
        try:
            self.log.debug("Connecting to %s" % addr)
            if disable_ssl_validation and urlparse(addr)[0] == "https":
                self.warning("Skipping SSL certificate validation for %s based on configuration" % addr)
            h = Http(timeout=timeout, disable_ssl_certificate_validation=disable_ssl_validation)
            if username is not None and password is not None:
                h.add_credentials(username, password)
            resp, content = h.request(addr, "GET", headers=headers)

        except socket.timeout, e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms" % (addr, str(e), length))
            return Status.DOWN, "%s. Connection failed after %s ms" % (str(e), length)

        except HttpLib2Error, e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms" % (addr, str(e), length))
            return Status.DOWN, "%s. Connection failed after %s ms" % (str(e), length)

        except socket.error, e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms" % (addr, repr(e), length))
            return Status.DOWN, "Socket error: %s. Connection failed after %s ms" % (repr(e), length)

        except Exception, e:
            length = int((time.time() - start) * 1000)
            self.log.error("Unhandled exception %s. Connection failed after %s ms" % (str(e), length))
            raise

        if response_time:
           # Stop the timer as early as possible
           running_time = time.time() - start
           # Store tags in a temporary list so that we don't modify the global tags data structure
           tags_list = []
           tags_list.extend(tags)
           tags_list.append('url:%s' % addr)
           self.gauge('network.http.response_time', running_time, tags=tags_list)

        if int(resp.status) >= 400:
            self.log.info("%s is DOWN, error code: %s" % (addr, str(resp.status)))
            if not include_content:
                content = ''
            return Status.DOWN, (resp.status, resp.reason, content or '')

        self.log.debug("%s is UP" % addr)
        return Status.UP, "UP"

    def _create_status_event(self, status, msg, instance):
        # Get the instance settings
        url = instance.get('url', None)
        name = instance.get('name', None)
        nb_failures = self.statuses[name].count(Status.DOWN)
        nb_tries = len(self.statuses[name])
        tags = instance.get('tags', [])
        tags_list = []
        tags_list.extend(tags)
        tags_list.append('url:%s' % url)

        # Get a custom message that will be displayed in the event
        custom_message = instance.get('message', "")
        if custom_message:
            custom_message += " \n"

        # Let the possibility to override the source type name
        instance_source_type_name = instance.get('source_type', None)
        if instance_source_type_name is None:
            source_type = "%s.%s" % (NetworkCheck.SOURCE_TYPE_NAME, name)
        else:
            source_type = "%s.%s" % (NetworkCheck.SOURCE_TYPE_NAME, instance_source_type_name)


        # Get the handles you want to notify
        notify = instance.get('notify', self.init_config.get('notify', []))
        notify_message = ""
        if notify:
            notify_list = []
            for handle in notify:
                notify_list.append("@%s" % handle.strip())
            notify_message = " ".join(notify_list) + " \n"

        if status == Status.DOWN:
            # format the HTTP response body into the event
            if isinstance(msg, tuple):
                code, reason, content = msg

                # truncate and html-escape content
                if len(content) > 200:
                    content = content[:197] + '...'

                msg = "%d %s\n\n%s" % (code, reason, content)
                msg = msg.rstrip()

            title = "[Alert] %s reported that %s is down" % (self.hostname, name)
            alert_type = "error"
            msg = "%s %s %s reported that %s (%s) failed %s time(s) within %s last attempt(s). Last error: %s" % (notify_message,
                custom_message, self.hostname, name, url, nb_failures, nb_tries, msg)
            event_type = EventType.DOWN

        else: # Status is UP
            title = "[Recovered] %s reported that %s is up" % (self.hostname, name)
            alert_type = "success"
            msg = "%s %s %s reported that %s (%s) recovered" % (notify_message,
                custom_message, self.hostname, name,url)
            event_type = EventType.UP

        return {
             'timestamp': int(time.time()),
             'event_type': event_type,
             'host': self.hostname,
             'msg_text': msg,
             'msg_title': title,
             'alert_type': alert_type,
             "source_type_name": source_type,
             "event_object": name,
             "tags": tags_list
        }

    def report_as_service_check(self, name, status, instance, msg=None):
        service_check_name = self.normalize(name, self.SERVICE_CHECK_PREFIX)
        url = instance.get('url', None)

        if status == Status.DOWN:
            # format the HTTP response body into the event
            if isinstance(msg, tuple):
                code, reason, content = msg

                # truncate and html-escape content
                if len(content) > 200:
                    content = content[:197] + '...'

                msg = "%d %s\n\n%s" % (code, reason, content)
                msg = msg.rstrip()
        else:
            msg=None

        self.service_check(service_check_name,
                           NetworkCheck.STATUS_TO_SERVICE_CHECK[status],
                           tags= ['url:%s' % url],
                           message=msg
                           )

