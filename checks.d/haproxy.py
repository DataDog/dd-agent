import urlparse
import urllib2
import socket

from checks import AgentCheck
from util import json, headers

import time

STATS_URL = ";csv;norefresh"
EVENT_TYPE = SOURCE_TYPE_NAME = 'haproxy'

class Services(object):
    BACKEND = 'BACKEND'
    FRONTEND = 'FRONTEND'
    ALL = (BACKEND, FRONTEND)

class HAProxy(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        # Host status needs to persist across all checks
        self.host_status = {}

    METRICS = {
        "qcur": ("gauge", "queue.current"),
        "scur": ("gauge", "session.current"),
        "slim": ("gauge", "session.limit"),
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
    }

    def check(self, instance):
        url = instance.get('url')
        username = instance.get('username')
        password = instance.get('password')

        self.log.debug('Processing HAProxy data for %s' % url)
       
        data = self._fetch_data(url, username, password)

        if instance.get('status_check', self.init_config.get('status_check', False)):
            events_cb = self._process_events
        else:
            events_cb = None

        self._process_data(data, self.hostname, self._process_metrics,
            events_cb, url)

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

    def _process_data(self, data, my_hostname, metric_cb=None, event_cb=None, url=None):
        ''' Main data-processing loop. For each piece of useful data, we'll
        either save a metric, save an event or both. '''

        # Split the first line into an index of fields
        # The line looks like:
        # "# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,"
        fields = [f.strip() for f in data[0][2:].split(',') if f]

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
                        val = long(val)
                    except:
                        pass
                    data_dict[fields[i]] = val

            # Don't create metrics for aggregates
            service = data_dict['svname']
            if data_dict['svname'] in Services.ALL:
                if not data_list and service == Services.FRONTEND:
                    data_list.append(data_dict)

                # Send the list of data to the metric and event callbacks
                if metric_cb:
                    metric_cb(data_list, service, my_hostname)
                if event_cb:
                    event_cb(data_list, url)

                # Clear out the event list for the next service
                data_list = []
            else:
                data_list.append(data_dict)

        return data

    def _process_metrics(self, data_list, service, my_hostname):
        hosts_to_aggregate = {}
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
            tags = ["type:%s" % service]
            hostname = data['svname']
            service_name = data['pxname']

            if hostname == Services.FRONTEND:
                hostname = my_hostname

            if service == Services.BACKEND:
                tags.append('frontend:%s' % my_hostname)
            tags.append('host:%s' % hostname)
            tags.append("service:%s" % service_name)

            hp = hostname.split(':')
            # If there are multiple instances running on different ports, we
            # want all of the data across the entire host to be aggregated
            if len(hp) > 1:
                data_to_aggregate = hosts_to_aggregate.get(hp[0], [])
                data_to_aggregate.append(data)
                hosts_to_aggregate[hp[0]] = data_to_aggregate
                continue

            for key, value in data.items():
                if HAProxy.METRICS.get(key):
                    suffix = HAProxy.METRICS[key][1]
                    name = "haproxy.%s.%s" % (service.lower(), suffix)
                    if HAProxy.METRICS[key][0] == 'rate':
                        self.rate(name, value, tags=tags, hostname=hostname)
                    else:
                        self.gauge(name, value, tags=tags, hostname=hostname)

        if hosts_to_aggregate:
            self._aggregate_hosts(hosts_to_aggregate, service, my_hostname)


    def _aggregate_hosts(self, hosts_to_aggregate, service, my_hostname):
        ''' If there are many instances of a service running on different ports
        of a same host, we don't want to create as many metrics as the number of
        instances So we aggregate these metrics into one host

        hosts_to_aggregate = [
            'i-4562165': [
                {'svname':'i-4562165:9001', 'pxname':'dogweb', 'scur':'42', ...},
                {'svname':'i-4562165:9002', 'pxname':'dogweb', 'scur':'1337', ...},
                ...
            ],
            'i-3920324': [
                {'svname':'i-3920324:5001', 'pxname':'dogweb', 'scur':'42', ...},
                {'svname':'i-3920324:5002', 'pxname':'dogweb', 'scur':'1337', ...},
                ...
            ],
            ...
        ]
        '''
        aggr_list = []
        for hostname, data_list in hosts_to_aggregate.items():
            aggr_data = {}
            if len(data_list) == 1:
                aggr_data = data_list[0]
            else:
                # Aggregate each key across all of the service instances
                for key in data_list[0]:
                    if HAProxy.METRICS.get(key):
                        aggr_data[key] = sum([inst.get(key, 0) for inst in data_list])

            aggr_data['svname'] = hostname
            aggr_data['pxname'] = data_list[0]['pxname']

            aggr_list.append(aggr_data)

        self._process_metrics(aggr_list, service, my_hostname)

    def _process_events(self, data_list, url):
        ''' Main event processing loop. Events will be created for a service
        status change '''
        for data in data_list:
            hostname = data['svname']
            service_name = data['pxname']
            key = "%s:%s" % (hostname,service_name)
            status_dic = self.host_status.get(url, {})
            status = status_dic.get(key, None)

            if status is None:
                status_dic[key] = data['status']
                self.host_status[url] = status_dic
                continue

            if status != data['status'] and data['status'] in ('UP', 'DOWN'):
                # If the status of a host has changed, we trigger an event
                try:
                    lastchg = int(data['lastchg'])
                except Exception:
                    lastchg = 0

                # Create the event object
                ev = self._create_event(self.agentConfig['api_key'],
                    data['status'], hostname, lastchg, service_name)
                self.event(ev)

                # Store this host status so we can check against it later
                status_dic[key] = data['status']
                self.host_status[url] = status_dic

    def _create_event(self, api_key, status, hostname, lastchg, service_name):
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
             'api_key': api_key,
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
