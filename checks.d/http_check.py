# stdlib
from datetime import datetime
import os.path
import socket
import ssl
import time
from urlparse import urlparse

# 3rd party
import tornado
import requests

# project
from checks.network_checks import NetworkCheck, Status, EventType
from config import _is_affirmative
from util import headers as agent_headers


def get_ca_certs_path():
    """
    Get a path to the trusted certificates of the system
    """
    CA_CERTS = [
        '/opt/datadog-agent/embedded/ssl/certs/cacert.pem',
        os.path.join(os.path.dirname(tornado.__file__), 'ca-certificates.crt'),
        '/etc/ssl/certs/ca-certificates.crt',
    ]

    for f in CA_CERTS:
        if os.path.exists(f):
            return f
    return None


class HTTPCheck(NetworkCheck):
    SOURCE_TYPE_NAME = 'system'
    SC_STATUS = 'http_check'
    SC_SSL_CERT = 'http_check.ssl_cert'

    def __init__(self, name, init_config, agentConfig, instances):
        self.ca_certs = init_config.get('ca_certs', get_ca_certs_path())
        NetworkCheck.__init__(self, name, init_config, agentConfig, instances)

    def _load_conf(self, instance):
        # Fetches the conf
        tags = instance.get('tags', [])
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        config_headers = instance.get('headers', {})
        headers = agent_headers(self.agentConfig)
        headers.update(config_headers)
        url = instance.get('url', None)
        response_time = _is_affirmative(instance.get('collect_response_time', True))
        if url is None:
            raise Exception("Bad configuration. You must specify a url")
        include_content = _is_affirmative(instance.get('include_content', False))
        ssl = _is_affirmative(instance.get('disable_ssl_validation', True))
        ssl_expire = _is_affirmative(instance.get('check_certificate_expiration', True))

        return url, username, password, timeout, include_content, headers, response_time, tags, ssl, ssl_expire

    def _check(self, instance):
        addr, username, password, timeout, include_content, headers, response_time, tags, disable_ssl_validation, ssl_expire = self._load_conf(instance)
        content = ''
        start = time.time()

        service_checks = []
        resp = None

        try:
            self.log.debug("Connecting to %s" % addr)
            if disable_ssl_validation and urlparse(addr)[0] == "https":
                self.warning("Skipping SSL certificate validation for %s based on configuration" % addr)
            
            auth = None
            if username is not None and password is not None:
                auth = (username, password)

            r = requests.get(addr, auth=auth,timeout=timeout, headers=headers,
                verify=not disable_ssl_validation)
            r.raise_for_status()
            

        except socket.timeout, e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms" % (addr, str(e), length))
            service_checks.append((
                self.SC_STATUS,
                Status.DOWN,
                "%s. Connection failed after %s ms" % (str(e), length)
            ))

        except requests.exceptions.HTTPError, r:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error code: %s" % (addr, str(r.status_code)))

            content = r.content if include_content else ''

            service_checks.append((
                self.SC_STATUS, Status.DOWN, (r.status_code, r.reason, content or '')
            ))

        except requests.exceptions.ConnectionError, e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms" % (addr, str(e), length))
            service_checks.append((
                self.SC_STATUS,
                Status.DOWN,
                "%s. Connection failed after %s ms" % (str(e), length)
            ))

        except socket.error, e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms" % (addr, repr(e), length))
            service_checks.append((
                self.SC_STATUS,
                Status.DOWN,
                "Socket error: %s. Connection failed after %s ms" % (repr(e), length)
            ))

        except Exception, e:
            length = int((time.time() - start) * 1000)
            self.log.error("Unhandled exception %s. Connection failed after %s ms" % (str(e), length))
            raise

        # Only report this metric if the site is not down
        if response_time and not service_checks:
            # Stop the timer as early as possible
            running_time = time.time() - start
            # Store tags in a temporary list so that we don't modify the global tags data structure
            tags_list = list(tags)
            tags_list.append('url:%s' % addr)
            self.gauge('network.http.response_time', running_time, tags=tags_list)

        if not service_checks:
            self.log.debug("%s is UP" % addr)
            service_checks.append((
                self.SC_STATUS, Status.UP, "UP"
            ))

        if ssl_expire and urlparse(addr)[0] == "https":
            status, msg = self.check_cert_expiration(instance)
            service_checks.append((
                self.SC_SSL_CERT, status, msg
            ))

        return service_checks

    # FIXME: 5.3 drop this function
    def _create_status_event(self, sc_name, status, msg, instance):
        # Create only this deprecated event for old check
        if sc_name != self.SC_STATUS:
            return
        # Get the instance settings
        url = instance.get('url', None)
        name = instance.get('name', None)
        nb_failures = self.statuses[name][sc_name].count(Status.DOWN)
        nb_tries = len(self.statuses[name][sc_name])
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

    def report_as_service_check(self, sc_name, status, instance, msg=None):
        instance_name = instance['name']
        service_check_name = self.normalize(instance_name, sc_name)
        url = instance.get('url', None)
        sc_tags = ['url:%s' % url]

        if sc_name == self.SC_STATUS:
            # format the HTTP response body into the event
            if isinstance(msg, tuple):
                code, reason, content = msg

                # truncate and html-escape content
                if len(content) > 200:
                    content = content[:197] + '...'

                msg = "%d %s\n\n%s" % (code, reason, content)
                msg = msg.rstrip()

        self.service_check(service_check_name,
                           NetworkCheck.STATUS_TO_SERVICE_CHECK[status],
                           tags=sc_tags,
                           message=msg
                           )

    def check_cert_expiration(self, instance):
        warning_days = int(instance.get('days_warning', 14))
        url = instance.get('url')

        o = urlparse(url)
        host = o.netloc

        port = o.port or 443

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            ssl_sock = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED,
                                           ca_certs=self.ca_certs)
            cert = ssl_sock.getpeercert()

        except Exception as e:
            return Status.DOWN, "%s" % (str(e))

        exp_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        days_left = exp_date - datetime.utcnow()

        if days_left.days < 0:
            return Status.DOWN, "Expired by {0} days".format(days_left.days)

        elif days_left.days < warning_days:
            return Status.WARNING, "This cert is almost expired, only {0} days left".format(days_left.days)

        else:
            return Status.UP, "Days left: {0}".format(days_left.days)
