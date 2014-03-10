import urlparse
import urllib2
import socket

from checks import AgentCheck
from util import json, headers

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

        self.log.debug('Processing HAProxy data for %s' % url)

        data = self._fetch_data(url, username, password)

        process_events = instance.get('status_check', self.init_config.get('status_check', False))

        self._process_data(data, collect_aggregates_only, process_events, url=url, collect_status_metrics=collect_status_metrics)

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

    def _process_data(self, data, collect_aggregates_only, process_events, url=None, collect_status_metrics=False):
        ''' Main data-processing loop. For each piece of useful data, we'll
        either save a metric, save an event or both. '''

        # Split the first line into an index of fields
        # The line looks like:
        # "# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,"
        fields = [f.strip() for f in data[0][2:].split(',') if f]

        hosts_statuses = defaultdict(int)

        # Holds a list of dictionaries describing each system
        data_list = []

        for line in data[1:]: # Skip the first line
            if not line.strip():
                continue
            data_dict = {}
            values = line.split(',')

            # Store each line's values in a dictionary
            for i, val in enumerate(values):
                if val:
                    try:
                        # Try converting to a long, if failure, just leave it
                        val = float(val)
                    except Exception:
                        pass
                    data_dict[fields[i]] = val

            # The percentage of used sessions based on 'scur' and 'slim'
            if 'slim' in data_dict and 'scur' in data_dict:
                try:
                    data_dict['spct'] = (data_dict['scur'] / data_dict['slim']) * 100
                except (TypeError, ZeroDivisionError):
                    pass

            service = data_dict['svname']

            if collect_status_metrics and 'status' in data_dict and 'pxname' in data_dict:
                hosts_statuses[(data_dict['pxname'], data_dict['status'])] += 1


            if data_dict['svname'] in Services.ALL:
                data_list.append(data_dict)

                # Send the list of data to the metric and event callbacks
                self._process_metrics(data_list, service, url)
                if process_events:
                    self._process_events(data_list, url)

                # Clear out the event list for the next service
                data_list = []
            elif not collect_aggregates_only:
                data_list.append(data_dict)

        if collect_status_metrics:
            self._process_status_metric(hosts_statuses)

        return data

    def _process_status_metric(self, hosts_statuses):
        agg_statuses = defaultdict(lambda:{'available':0, 'unavailable':0})
        for (service, status), count in hosts_statuses.iteritems():
            status = status.lower()

            tags = ['status:%s' % status, 'service:%s' % service]
            self.gauge("haproxy.count_per_status", count, tags=tags)

            if 'up' in status:
                agg_statuses[service]['available'] += count
            if 'down' in status or 'maint' in status or 'nolb' in status:
                agg_statuses[service]['unavailable'] += count

        for service in agg_statuses:
            for status, count in agg_statuses[service].iteritems():
                tags = ['status:%s' % status, 'service:%s' % service]
                self.gauge("haproxy.count_per_status", count, tags=tags)

    def _process_metrics(self, data_list, service, url):
        for data in data_list:
            """
            Each element of data_list is a dictionary related to one host
            (one line) extracted from the csv. All of these elements should
            have the same value for 'pxname' key
            It should look like:
            data_list = [
                {'svname':'i-4562165', 'pxname':'dogweb', 'scur':'42', ...},
                {'svname':'i-2854985', 'pxname':'dogweb', 'scur':'1337', ...},
                ...
            ]
            """
            tags = ["type:%s" % service, "instance_url:%s" % url]
            hostname = data['svname']
            service_name = data['pxname']

            if service == Services.BACKEND:
                tags.append('backend:%s' % hostname)
            tags.append("service:%s" % service_name)

            for key, value in data.items():
                if HAProxy.METRICS.get(key):
                    suffix = HAProxy.METRICS[key][1]
                    name = "haproxy.%s.%s" % (service.lower(), suffix)
                    if HAProxy.METRICS[key][0] == 'rate':
                        self.rate(name, value, tags=tags)
                    else:
                        self.gauge(name, value, tags=tags)

    def _process_events(self, data_list, url):
        ''' Main event processing loop. Events will be created for a service
        status change '''
        for data in data_list:
            hostname = data['svname']
            service_name = data['pxname']
            key = "%s:%s" % (hostname,service_name)
            status = self.host_status[url][key]

            if status is None:
                self.host_status[url][key] = data['status']
                continue

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
            title = "HAProxy %s front-end reported %s %s" % (service_name, hostname, status)
        else:
            if status == "UP":
                alert_type = "success"
            else:
                alert_type = "info"
            title = "HAProxy %s front-end reported %s back and %s" % (service_name, hostname, status)

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
