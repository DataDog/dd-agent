# stdlib
from datetime import datetime
import os.path
import re
import socket
import ssl
import time
from urlparse import urlparse

# 3rd party
import requests
import tornado

# project
from checks.network_checks import EventType, NetworkCheck, Status
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
    SC_STATUS = 'http.can_connect'
    SC_SSL_CERT = 'http.ssl_cert'

    def __init__(self, name, init_config, agentConfig, instances):
        self.ca_certs = init_config.get('ca_certs', get_ca_certs_path())
        NetworkCheck.__init__(self, name, init_config, agentConfig, instances)

    def _load_conf(self, instance):
        # Fetches the conf
        tags = instance.get('tags', [])
        username = instance.get('username')
        password = instance.get('password')
        http_response_status_code = str(instance.get('http_response_status_code', "(1|2|3)\d\d"))
        timeout = int(instance.get('timeout', 10))
        config_headers = instance.get('headers', {})
        headers = agent_headers(self.agentConfig)
        headers.update(config_headers)
        url = instance.get('url')
        content_match = instance.get('content_match')
        response_time = _is_affirmative(instance.get('collect_response_time', True))
        if not url:
            raise Exception("Bad configuration. You must specify a url")
        include_content = _is_affirmative(instance.get('include_content', False))
        ssl = _is_affirmative(instance.get('disable_ssl_validation', True))
        ssl_expire = _is_affirmative(instance.get('check_certificate_expiration', True))
        instance_ca_certs = instance.get('ca_certs', self.ca_certs)

        return url, username, password, http_response_status_code, timeout, include_content,\
            headers, response_time, content_match, tags, ssl, ssl_expire, instance_ca_certs

    def _check(self, instance):
        addr, username, password, http_response_status_code, timeout, include_content, headers,\
            response_time, content_match, tags, disable_ssl_validation,\
            ssl_expire, instance_ca_certs = self._load_conf(instance)
        start = time.time()

        service_checks = []
        try:
            self.log.debug("Connecting to %s" % addr)
            if disable_ssl_validation and urlparse(addr)[0] == "https":
                self.warning("Skipping SSL certificate validation for %s based on configuration"
                             % addr)

            auth = None
            if username is not None and password is not None:
                auth = (username, password)

            r = requests.get(addr, auth=auth, timeout=timeout, headers=headers,
                             verify=False if disable_ssl_validation else instance_ca_certs)

        except (socket.timeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms"
                          % (addr, str(e), length))
            service_checks.append((
                self.SC_STATUS,
                Status.DOWN,
                "%s. Connection failed after %s ms" % (str(e), length)
            ))

        except socket.error, e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms"
                          % (addr, repr(e), length))
            service_checks.append((
                self.SC_STATUS,
                Status.DOWN,
                "Socket error: %s. Connection failed after %s ms" % (repr(e), length)
            ))

        except Exception, e:
            length = int((time.time() - start) * 1000)
            self.log.error("Unhandled exception %s. Connection failed after %s ms"
                           % (str(e), length))
            raise

        # Only report this metric if the site is not down
        if response_time and not service_checks:
            # Stop the timer as early as possible
            running_time = time.time() - start
            # Store tags in a temporary list so that we don't modify the global tags data structure
            tags_list = list(tags)
            tags_list.append('url:%s' % addr)
            self.gauge('network.http.response_time', running_time, tags=tags_list)

        # Check HTTP response status code
        if not (service_checks or re.match(http_response_status_code, str(r.status_code))):
            self.log.info("Incorrect HTTP return code. Expected %s, got %s"
                          % (http_response_status_code, str(r.status_code)))

            service_checks.append((
                self.SC_STATUS,
                Status.DOWN,
                "Incorrect HTTP return code. Expected %s, got %s"
                % (http_response_status_code, str(r.status_code))
            ))

        if not service_checks:
            # Host is UP
            # Check content matching is set
            if content_match:
                content = r.content
                if re.search(content_match, content):
                    self.log.debug("%s is found in return content" % content_match)
                    service_checks.append((
                        self.SC_STATUS, Status.UP, "UP"
                    ))
                else:
                    self.log.info("%s not found in content" % content_match)
                    self.log.debug("Content returned:\n%s" % content)
                    service_checks.append((
                        self.SC_STATUS,
                        Status.DOWN,
                        'Content "%s" not found in response' % content_match
                    ))
            else:
                self.log.debug("%s is UP" % addr)
                service_checks.append((
                    self.SC_STATUS, Status.UP, "UP"
                ))

        if ssl_expire and urlparse(addr)[0] == "https":
            status, msg = self.check_cert_expiration(instance, timeout, instance_ca_certs)
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
            msg = "%s %s %s reported that %s (%s) failed %s time(s) within %s last attempt(s)."\
                " Last error: %s" % (notify_message, custom_message, self.hostname,
                                     name, url, nb_failures, nb_tries, msg)
            event_type = EventType.DOWN

        else:  # Status is UP
            title = "[Recovered] %s reported that %s is up" % (self.hostname, name)
            alert_type = "success"
            msg = "%s %s %s reported that %s (%s) recovered" \
                % (notify_message, custom_message, self.hostname, name, url)
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
        instance_name = self.normalize(instance['name'])
        url = instance.get('url', None)
        sc_tags = ['url:{0}'.format(url), "instance:{0}".format(instance_name)]
        custom_tags = instance.get('tags', [])
        tags = sc_tags + custom_tags

        if sc_name == self.SC_STATUS:
            # format the HTTP response body into the event
            if isinstance(msg, tuple):
                code, reason, content = msg

                # truncate and html-escape content
                if len(content) > 200:
                    content = content[:197] + '...'

                msg = "%d %s\n\n%s" % (code, reason, content)
                msg = msg.rstrip()

        self.service_check(sc_name,
                           NetworkCheck.STATUS_TO_SERVICE_CHECK[status],
                           tags=tags,
                           message=msg
                           )

    def check_cert_expiration(self, instance, timeout, instance_ca_certs):
        warning_days = int(instance.get('days_warning', 14))
        url = instance.get('url')

        o = urlparse(url)
        host = o.netloc

        port = o.port or 443

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(float(timeout))
            sock.connect((host, port))
            ssl_sock = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED,
                                       ca_certs=instance_ca_certs)
            cert = ssl_sock.getpeercert()

        except Exception as e:
            return Status.DOWN, "%s" % (str(e))

        exp_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        days_left = exp_date - datetime.utcnow()

        if days_left.days < 0:
            return Status.DOWN, "Expired by {0} days".format(days_left.days)

        elif days_left.days < warning_days:
            return Status.WARNING, "This cert is almost expired, only {0} days left"\
                .format(days_left.days)

        else:
            return Status.UP, "Days left: {0}".format(days_left.days)
