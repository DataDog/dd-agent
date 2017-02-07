# (C) Datadog, Inc. 2012-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict
import copy
import re
import socket
import time
import urlparse

# 3rd party
import requests

# project
from checks import AgentCheck
from config import _is_affirmative
from util import headers

STATS_URL = "/;csv;norefresh"
EVENT_TYPE = SOURCE_TYPE_NAME = 'haproxy'
BUFSIZE = 8192


class Services(object):
    BACKEND = 'BACKEND'
    FRONTEND = 'FRONTEND'
    ALL = (BACKEND, FRONTEND)

    # Statuses that we normalize to and that are reported by
    # `haproxy.count_per_status` by default (unless `collate_status_tags_per_host` is enabled)
    ALL_STATUSES = (
        'up', 'open', 'down', 'maint', 'nolb'
    )

    AVAILABLE = 'available'
    UNAVAILABLE = 'unavailable'
    COLLATED_STATUSES = (AVAILABLE, UNAVAILABLE)

    BACKEND_STATUS_TO_COLLATED = {
        'up': AVAILABLE,
        'down': UNAVAILABLE,
        'maint': UNAVAILABLE,
        'nolb': UNAVAILABLE,
    }

    STATUS_TO_COLLATED = {
        'up': AVAILABLE,
        'open': AVAILABLE,
        'down': UNAVAILABLE,
        'maint': UNAVAILABLE,
        'nolb': UNAVAILABLE,
    }

    STATUS_TO_SERVICE_CHECK = {
        'up': AgentCheck.OK,
        'down': AgentCheck.CRITICAL,
        'no_check': AgentCheck.UNKNOWN,
        'maint': AgentCheck.OK,
    }


class HAProxy(AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Host status needs to persist across all checks
        self.host_status = defaultdict(lambda: defaultdict(lambda: None))

    METRICS = {
        "qcur": ("gauge", "queue.current"),
        "scur": ("gauge", "session.current"),
        "slim": ("gauge", "session.limit"),
        "spct": ("gauge", "session.pct"),    # Calculated as: (scur/slim)*100
        "stot": ("rate", "session.rate"),
        "bin": ("rate", "bytes.in_rate"),
        "bout": ("rate", "bytes.out_rate"),
        "dreq": ("rate", "denied.req_rate"),
        "dresp": ("rate", "denied.resp_rate"),
        "ereq": ("rate", "errors.req_rate"),
        "econ": ("rate", "errors.con_rate"),
        "eresp": ("rate", "errors.resp_rate"),
        "wretr": ("rate", "warnings.retr_rate"),
        "wredis": ("rate", "warnings.redis_rate"),
        "req_rate": ("gauge", "requests.rate"),  # HA Proxy 1.4 and higher
        "hrsp_1xx": ("rate", "response.1xx"),  # HA Proxy 1.4 and higher
        "hrsp_2xx": ("rate", "response.2xx"),  # HA Proxy 1.4 and higher
        "hrsp_3xx": ("rate", "response.3xx"),  # HA Proxy 1.4 and higher
        "hrsp_4xx": ("rate", "response.4xx"),  # HA Proxy 1.4 and higher
        "hrsp_5xx": ("rate", "response.5xx"),  # HA Proxy 1.4 and higher
        "hrsp_other": ("rate", "response.other"),  # HA Proxy 1.4 and higher
        "qtime": ("gauge", "queue.time"),  # HA Proxy 1.5 and higher
        "ctime": ("gauge", "connect.time"),  # HA Proxy 1.5 and higher
        "rtime": ("gauge", "response.time"),  # HA Proxy 1.5 and higher
        "ttime": ("gauge", "session.time"),  # HA Proxy 1.5 and higher
        "lastchg": ("gauge", "uptime")
    }

    SERVICE_CHECK_NAME = 'haproxy.backend_up'

    def check(self, instance):
        url = instance.get('url')
        self.log.debug('Processing HAProxy data for %s' % url)

        parsed_url = urlparse.urlparse(url)

        if parsed_url.scheme == 'unix':
            data = self._fetch_socket_data(parsed_url.path)

        else:
            username = instance.get('username')
            password = instance.get('password')
            verify = not _is_affirmative(instance.get('disable_ssl_validation', False))

            data = self._fetch_url_data(url, username, password, verify)

        collect_aggregates_only = _is_affirmative(
            instance.get('collect_aggregates_only', True)
        )
        collect_status_metrics = _is_affirmative(
            instance.get('collect_status_metrics', False)
        )

        collect_status_metrics_by_host = _is_affirmative(
            instance.get('collect_status_metrics_by_host', False)
        )

        collate_status_tags_per_host = _is_affirmative(
            instance.get('collate_status_tags_per_host', False)
        )

        count_status_by_service = _is_affirmative(
            instance.get('count_status_by_service', True)
        )

        tag_service_check_by_host = _is_affirmative(
            instance.get('tag_service_check_by_host', False)
        )

        services_incl_filter = instance.get('services_include', [])
        services_excl_filter = instance.get('services_exclude', [])

        custom_tags = instance.get('tags', [])

        process_events = instance.get('status_check', self.init_config.get('status_check', False))

        self._process_data(
            data, collect_aggregates_only, process_events,
            url=url, collect_status_metrics=collect_status_metrics,
            collect_status_metrics_by_host=collect_status_metrics_by_host,
            tag_service_check_by_host=tag_service_check_by_host,
            services_incl_filter=services_incl_filter,
            services_excl_filter=services_excl_filter,
            collate_status_tags_per_host=collate_status_tags_per_host,
            count_status_by_service=count_status_by_service,
            custom_tags=custom_tags,
        )

    def _fetch_url_data(self, url, username, password, verify):
        ''' Hit a given http url and return the stats lines '''
        # Try to fetch data from the stats URL

        auth = (username, password)
        url = "%s%s" % (url, STATS_URL)

        self.log.debug("Fetching haproxy stats from url: %s" % url)

        response = requests.get(url, auth=auth, headers=headers(self.agentConfig), verify=verify, timeout=self.default_integration_http_timeout)
        response.raise_for_status()

        return response.content.splitlines()

    def _fetch_socket_data(self, socket_path):
        ''' Hit a given stats socket and return the stats lines '''

        self.log.debug("Fetching haproxy stats from socket: %s" % socket_path)

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        sock.send("show stat\r\n")

        response = ""
        output = sock.recv(BUFSIZE)
        while output:
            response += output.decode("ASCII")
            output = sock.recv(BUFSIZE)

        sock.close()

        return response.splitlines()

    def _process_data(self, data, collect_aggregates_only, process_events, url=None,
                      collect_status_metrics=False, collect_status_metrics_by_host=False,
                      tag_service_check_by_host=False, services_incl_filter=None,
                      services_excl_filter=None, collate_status_tags_per_host=False,
                      count_status_by_service=True, custom_tags=[]):
        ''' Main data-processing loop. For each piece of useful data, we'll
        either save a metric, save an event or both. '''

        # Split the first line into an index of fields
        # The line looks like:
        # "# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,"
        fields = [f.strip() for f in data[0][2:].split(',') if f]

        self.hosts_statuses = defaultdict(int)

        back_or_front = None

        # Skip the first line, go backwards to set back_or_front
        for line in data[:0:-1]:
            if not line.strip():
                continue

            # Store each line's values in a dictionary
            data_dict = self._line_to_dict(fields, line)

            if self._is_aggregate(data_dict):
                back_or_front = data_dict['svname']

            self._update_data_dict(data_dict, back_or_front)

            self._update_hosts_statuses_if_needed(
                collect_status_metrics, collect_status_metrics_by_host,
                data_dict, self.hosts_statuses
            )

            if self._should_process(data_dict, collect_aggregates_only):
                # update status
                # Send the list of data to the metric and event callbacks
                self._process_metrics(
                    data_dict, url,
                    services_incl_filter=services_incl_filter,
                    services_excl_filter=services_excl_filter,
                    custom_tags=custom_tags
                )
            if process_events:
                self._process_event(
                    data_dict, url,
                    services_incl_filter=services_incl_filter,
                    services_excl_filter=services_excl_filter,
                    custom_tags=custom_tags
                )
            self._process_service_check(
                data_dict, url,
                tag_by_host=tag_service_check_by_host,
                services_incl_filter=services_incl_filter,
                services_excl_filter=services_excl_filter,
                custom_tags=custom_tags
            )

        if collect_status_metrics:
            self._process_status_metric(
                self.hosts_statuses, collect_status_metrics_by_host,
                services_incl_filter=services_incl_filter,
                services_excl_filter=services_excl_filter,
                collate_status_tags_per_host=collate_status_tags_per_host,
                count_status_by_service=count_status_by_service,
                custom_tags=custom_tags
            )

            self._process_backend_hosts_metric(
                self.hosts_statuses,
                services_incl_filter=services_incl_filter,
                services_excl_filter=services_excl_filter,
                custom_tags=custom_tags
            )

        return data

    def _line_to_dict(self, fields, line):
        data_dict = {}
        for i, val in enumerate(line.split(',')[:]):
            if val:
                try:
                    # Try converting to a long, if failure, just leave it
                    val = float(val)
                except Exception:
                    pass
                data_dict[fields[i]] = val

        if 'status' in data_dict:
            data_dict['status'] = self._normalize_status(data_dict['status'])

        return data_dict

    def _update_data_dict(self, data_dict, back_or_front):
        """
        Adds spct if relevant, adds service
        """
        data_dict['back_or_front'] = back_or_front
        # The percentage of used sessions based on 'scur' and 'slim'
        if 'slim' in data_dict and 'scur' in data_dict:
            try:
                data_dict['spct'] = (data_dict['scur'] / data_dict['slim']) * 100
            except (TypeError, ZeroDivisionError):
                pass

    def _is_aggregate(self, data_dict):
        return data_dict['svname'] in Services.ALL

    def _update_hosts_statuses_if_needed(self, collect_status_metrics,
                                         collect_status_metrics_by_host,
                                         data_dict, hosts_statuses):
        if data_dict['svname'] == Services.BACKEND:
            return
        if collect_status_metrics and 'status' in data_dict and 'pxname' in data_dict:
            if collect_status_metrics_by_host and 'svname' in data_dict:
                key = (data_dict['pxname'], data_dict['svname'], data_dict['status'])
            else:
                key = (data_dict['pxname'], data_dict['status'])
            hosts_statuses[key] += 1

    def _should_process(self, data_dict, collect_aggregates_only):
        """
            if collect_aggregates_only, we process only the aggregates
            else we process all except Services.BACKEND
        """
        if collect_aggregates_only:
            if self._is_aggregate(data_dict):
                return True
            return False
        elif data_dict['svname'] == Services.BACKEND:
            return False
        return True

    def _is_service_excl_filtered(self, service_name, services_incl_filter,
                                  services_excl_filter):
        if self._tag_match_patterns(service_name, services_excl_filter):
            if self._tag_match_patterns(service_name, services_incl_filter):
                return False
            return True
        return False

    def _tag_match_patterns(self, tag, filters):
        if not filters:
            return False
        for rule in filters:
            if re.search(rule, tag):
                return True
        return False

    @staticmethod
    def _normalize_status(status):
        """
        Try to normalize the HAProxy status as one of the statuses defined in `ALL_STATUSES`,
        if it can't be matched return the status as-is in a tag-friendly format
        ex: 'UP 1/2' -> 'up'
            'no check' -> 'no_check'
        """
        formatted_status = status.lower().replace(" ", "_")
        for normalized_status in Services.ALL_STATUSES:
            if formatted_status.startswith(normalized_status):
                return normalized_status
        return formatted_status

    def _process_backend_hosts_metric(self, hosts_statuses, services_incl_filter=None,
                                      services_excl_filter=None, custom_tags=[]):
        agg_statuses = defaultdict(lambda: {status: 0 for status in Services.COLLATED_STATUSES})
        for host_status, count in hosts_statuses.iteritems():
            try:
                service, hostname, status = host_status
            except Exception:
                service, status = host_status

            if self._is_service_excl_filtered(service, services_incl_filter, services_excl_filter):
                continue

            collated_status = Services.BACKEND_STATUS_TO_COLLATED.get(status)
            if collated_status:
                agg_statuses[service][collated_status] += count
            else:
                # create the entries for this service anyway
                agg_statuses[service]

        for service in agg_statuses:
            tags = ['service:%s' % service]
            tags.extend(custom_tags)
            self.gauge(
                'haproxy.backend_hosts',
                agg_statuses[service][Services.AVAILABLE],
                tags=tags + ['available:true'])
            self.gauge(
                'haproxy.backend_hosts',
                agg_statuses[service][Services.UNAVAILABLE],
                tags=tags + ['available:false'])
        return agg_statuses

    def _process_status_metric(self, hosts_statuses, collect_status_metrics_by_host,
                               services_incl_filter=None, services_excl_filter=None,
                               collate_status_tags_per_host=False, count_status_by_service=True, custom_tags=[]):
        agg_statuses_counter = defaultdict(lambda: {status: 0 for status in Services.COLLATED_STATUSES})

        # Initialize `statuses_counter`: every value is a defaultdict initialized with the correct
        # keys, which depends on the `collate_status_tags_per_host` option
        reported_statuses = Services.ALL_STATUSES
        if collate_status_tags_per_host:
            reported_statuses = Services.COLLATED_STATUSES
        reported_statuses_dict = defaultdict(int)
        for reported_status in reported_statuses:
            reported_statuses_dict[reported_status] = 0
        statuses_counter = defaultdict(lambda: copy.copy(reported_statuses_dict))

        for host_status, count in hosts_statuses.iteritems():
            hostname = None
            try:
                service, hostname, status = host_status
            except Exception:
                if collect_status_metrics_by_host:
                    self.warning('`collect_status_metrics_by_host` is enabled but no host info\
                                 could be extracted from HAProxy stats endpoint for {0}'.format(service))
                service, status = host_status

            if self._is_service_excl_filtered(service, services_incl_filter, services_excl_filter):
                continue

            tags = []
            if count_status_by_service:
                tags.append('service:%s' % service)
            if hostname:
                tags.append('backend:%s' % hostname)

            tags.extend(custom_tags)

            counter_status = status
            if collate_status_tags_per_host:
                # An unknown status will be sent as UNAVAILABLE
                counter_status = Services.STATUS_TO_COLLATED.get(status, Services.UNAVAILABLE)
            statuses_counter[tuple(tags)][counter_status] += count

            # Compute aggregates with collated statuses. If collate_status_tags_per_host is enabled we
            # already send collated statuses with fine-grained tags, so no need to compute/send these aggregates
            if not collate_status_tags_per_host:
                agg_tags = []
                if count_status_by_service:
                    agg_tags.append('service:%s' % service)
                # An unknown status will be sent as UNAVAILABLE
                agg_statuses_counter[tuple(agg_tags)][Services.STATUS_TO_COLLATED.get(status, Services.UNAVAILABLE)] += count

        for tags, count_per_status in statuses_counter.iteritems():
            for status, count in count_per_status.iteritems():
                self.gauge('haproxy.count_per_status', count, tags=tags + ('status:%s' % status, ))

        # Send aggregates
        for service_tags, service_agg_statuses in agg_statuses_counter.iteritems():
            for status, count in service_agg_statuses.iteritems():
                self.gauge("haproxy.count_per_status", count, tags=service_tags + ('status:%s' % status, ))

    def _process_metrics(self, data, url, services_incl_filter=None,
                         services_excl_filter=None, custom_tags=[]):
        """
        Data is a dictionary related to one host
        (one line) extracted from the csv.
        It should look like:
        {'pxname':'dogweb', 'svname':'i-4562165', 'scur':'42', ...}
        """
        hostname = data['svname']
        service_name = data['pxname']
        back_or_front = data['back_or_front']
        tags = [
            "type:%s" % back_or_front,
            "instance_url:%s" % url,
            "service:%s" % service_name,
        ]
        tags.extend(custom_tags)

        if self._is_service_excl_filtered(service_name, services_incl_filter,
                                          services_excl_filter):
            return

        if back_or_front == Services.BACKEND:
            tags.append('backend:%s' % hostname)

        for key, value in data.items():
            if HAProxy.METRICS.get(key):
                suffix = HAProxy.METRICS[key][1]
                name = "haproxy.%s.%s" % (back_or_front.lower(), suffix)
                if HAProxy.METRICS[key][0] == 'rate':
                    self.rate(name, value, tags=tags)
                else:
                    self.gauge(name, value, tags=tags)

    def _process_event(self, data, url, services_incl_filter=None,
                       services_excl_filter=None, custom_tags=[]):
        '''
        Main event processing loop. An event will be created for a service
        status change.
        Service checks on the server side can be used to provide the same functionality
        '''
        hostname = data['svname']
        service_name = data['pxname']
        key = "%s:%s" % (hostname, service_name)
        status = self.host_status[url][key]

        if self._is_service_excl_filtered(service_name, services_incl_filter,
                                          services_excl_filter):
            return

        if status is None:
            self.host_status[url][key] = data['status']
            return

        if status != data['status'] and data['status'] in ('up', 'down'):
            # If the status of a host has changed, we trigger an event
            try:
                lastchg = int(data['lastchg'])
            except Exception:
                lastchg = 0

            # Create the event object
            ev = self._create_event(
                data['status'], hostname, lastchg, service_name,
                data['back_or_front'], custom_tags=custom_tags
            )
            self.event(ev)

            # Store this host status so we can check against it later
            self.host_status[url][key] = data['status']

    def _create_event(self, status, hostname, lastchg, service_name, back_or_front,
                      custom_tags=[]):
        HAProxy_agent = self.hostname.decode('utf-8')
        if status == 'down':
            alert_type = "error"
            title = "%s reported %s:%s %s" % (HAProxy_agent, service_name, hostname, status.upper())
        else:
            if status == "up":
                alert_type = "success"
            else:
                alert_type = "info"
            title = "%s reported %s:%s back and %s" % (HAProxy_agent, service_name, hostname, status.upper())

        tags = ["service:%s" % service_name]
        if back_or_front == Services.BACKEND:
            tags.append('backend:%s' % hostname)
        tags.extend(custom_tags)
        return {
            'timestamp': int(time.time() - lastchg),
            'event_type': EVENT_TYPE,
            'host': HAProxy_agent,
            'msg_title': title,
            'alert_type': alert_type,
            "source_type_name": SOURCE_TYPE_NAME,
            "event_object": hostname,
            "tags": tags
        }

    def _process_service_check(self, data, url, tag_by_host=False,
                               services_incl_filter=None, services_excl_filter=None, custom_tags=[]):
        ''' Report a service check, tagged by the service and the backend.
            Statuses are defined in `STATUS_TO_SERVICE_CHECK` mapping.
        '''
        service_name = data['pxname']
        status = data['status']
        haproxy_hostname = self.hostname.decode('utf-8')
        check_hostname = haproxy_hostname if tag_by_host else ''

        if self._is_service_excl_filtered(service_name, services_incl_filter,
                                          services_excl_filter):
            return

        if status in Services.STATUS_TO_SERVICE_CHECK:
            service_check_tags = ["service:%s" % service_name]
            service_check_tags.extend(custom_tags)
            hostname = data['svname']
            if data['back_or_front'] == Services.BACKEND:
                service_check_tags.append('backend:%s' % hostname)

            status = Services.STATUS_TO_SERVICE_CHECK[status]
            message = "%s reported %s:%s %s" % (haproxy_hostname, service_name,
                                                hostname, status)
            self.service_check(self.SERVICE_CHECK_NAME, status,  message=message,
                               hostname=check_hostname, tags=service_check_tags)
