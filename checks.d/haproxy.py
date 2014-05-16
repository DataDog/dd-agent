import urllib2

from checks import AgentCheck
from util import headers

import time

try:
    from collections import defaultdict
except ImportError:
    from compat.defaultdict import defaultdict

STATS_URL = "/;csv;norefresh"
EVENT_TYPE = SOURCE_TYPE_NAME = 'haproxy'

class Services(object):
    BACKEND = 'BACKEND'
    FRONTEND = 'FRONTEND'
    ALL = (BACKEND, FRONTEND)
    ALL_STATUSES = (
            'up', 'open', 'no_check', 'down', 'maint', 'nolb'
        )

class HAProxy(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

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
        "req_rate": ("gauge", "requests.rate"),
        "hrsp_1xx": ("rate", "response.1xx"),
        "hrsp_2xx": ("rate", "response.2xx"),
        "hrsp_3xx": ("rate", "response.3xx"),
        "hrsp_4xx": ("rate", "response.4xx"),
        "hrsp_5xx": ("rate", "response.5xx"),
        "hrsp_other": ("rate", "response.other"),
    }

    def check(self, instance):
        url = instance.get('url')
        username = instance.get('username')
        password = instance.get('password')
        collect_aggregates_only = instance.get('collect_aggregates_only', True)
        collect_status_metrics = instance.get('collect_status_metrics', False)
        collect_status_metrics_by_host = instance.get('collect_status_metrics_by_host', False)

        self.log.debug('Processing HAProxy data for %s' % url)

        data = self._fetch_data(url, username, password)

        process_events = instance.get('status_check', self.init_config.get('status_check', False))

        self._process_data(
            data, collect_aggregates_only, process_events,
            url=url, collect_status_metrics=collect_status_metrics,
            collect_status_metrics_by_host=collect_status_metrics_by_host
        )

    def _fetch_data(self, url, username, password):
        ''' Hit a given URL and return the parsed json '''
        # Try to fetch data from the stats URL

        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, url, username, password)
        authhandler = urllib2.HTTPBasicAuthHandler(passman)
        opener = urllib2.build_opener(authhandler)
        urllib2.install_opener(opener)
        url = "%s%s" % (url, STATS_URL)

        self.log.debug("HAProxy Fetching haproxy search data from: %s" % url)

        req = urllib2.Request(url, None, headers(self.agentConfig))
        request = urllib2.urlopen(req)
        response = request.read()
        # Split the data by line
        return response.split('\n')

    def _process_data(
            self, data, collect_aggregates_only, process_events, url=None,
            collect_status_metrics=False, collect_status_metrics_by_host=False
        ):
        ''' Main data-processing loop. For each piece of useful data, we'll
        either save a metric, save an event or both. '''

        # Split the first line into an index of fields
        # The line looks like:
        # "# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,"
        fields = [f.strip() for f in data[0][2:].split(',') if f]

        hosts_statuses = defaultdict(int)

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
                data_dict, hosts_statuses
            )

            if self._should_process(data_dict, collect_aggregates_only):
                # Send the list of data to the metric and event callbacks
                self._process_metrics(data_dict, url)
            if process_events:
                self._process_event(data_dict, url)

        if collect_status_metrics:
            self._process_status_metric(hosts_statuses, collect_status_metrics_by_host)

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

    def _update_hosts_statuses_if_needed(self,
        collect_status_metrics, collect_status_metrics_by_host,
        data_dict, hosts_statuses
    ):
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

    def _process_status_metric(self, hosts_statuses, collect_status_metrics_by_host):
        agg_statuses = defaultdict(lambda:{'available':0, 'unavailable':0})
        for host_status, count in hosts_statuses.iteritems():
            try:
                service, hostname, status = host_status
            except:
                service, status = host_status
            status = status.lower()

            tags = ['service:%s' % service]
            if collect_status_metrics_by_host:
                tags.append('backend:%s' % hostname)
            self._gauge_all_statuses("haproxy.count_per_status", count, status, tags=tags)

            if 'up' in status or 'open' in status:
                agg_statuses[service]['available'] += count
            if 'down' in status or 'maint' in status or 'nolb' in status:
                agg_statuses[service]['unavailable'] += count

        for service in agg_statuses:
            for status, count in agg_statuses[service].iteritems():
                tags = ['status:%s' % status, 'service:%s' % service]
                self.gauge("haproxy.count_per_status", count, tags=tags)

    def _gauge_all_statuses(self, metric_name, count, status, tags):
        self.gauge(metric_name, count, tags + ['status:%s' % status])
        for state in Services.ALL_STATUSES:
            if state != status:
                self.gauge(metric_name, 0, tags + ['status:%s' % state])


    def _process_metrics(self, data, url):
        """
        Data is a dictionary related to one host
        (one line) extracted from the csv.
        It should look like:
        {'pxname':'dogweb', 'svname':'i-4562165', 'scur':'42', ...}
        """
        hostname = data['svname']
        service_name = data['pxname']
        back_or_front = data['back_or_front']
        tags = ["type:%s" % back_or_front, "instance_url:%s" % url]
        tags.append("service:%s" % service_name)
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

    def _process_event(self, data, url):
        ''' Main event processing loop. An event will be created for a service
        status change '''
        hostname = data['svname']
        service_name = data['pxname']
        key = "%s:%s" % (hostname,service_name)
        status = self.host_status[url][key]

        if status is None:
            self.host_status[url][key] = data['status']
            return

        if status != data['status'] and data['status'] in ('UP', 'DOWN'):
            # If the status of a host has changed, we trigger an event
            try:
                lastchg = int(data['lastchg'])
            except Exception:
                lastchg = 0

            # Create the event object
            ev = self._create_event(data['status'], hostname, lastchg, service_name)
            self.event(ev)

            # Store this host status so we can check against it later
            self.host_status[url][key] = data['status']

    def _create_event(self, status, hostname, lastchg, service_name):
        if status == "DOWN":
            alert_type = "error"
            title = "HAProxy %s reported %s %s" % (service_name, hostname, status)
        else:
            if status == "UP":
                alert_type = "success"
            else:
                alert_type = "info"
            title = "HAProxy %s reported %s back and %s" % (service_name, hostname, status)

        return {
             'timestamp': int(time.time() - lastchg),
             'event_type': EVENT_TYPE,
             'host': hostname,
             'msg_title': title,
             'alert_type': alert_type,
             "source_type_name": SOURCE_TYPE_NAME,
             "event_object": hostname,
             "tags": ["frontend:%s" % service_name, "host:%s" % hostname]
        }

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('haproxy_url'):
            return False

        return {
            'instances': [{
                'url': agentConfig.get('haproxy_url'),
                'username': agentConfig.get('haproxy_user'),
                'password': agentConfig.get('haproxy_password')
            }]
        }
