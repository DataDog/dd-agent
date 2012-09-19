import urlparse
import urllib2
import socket

from checks import CheckD, gethostname
from util import json, headers

from datetime import datetime
import time

CHECKS = [
    'HAProxy'
]

STATS_URL = ";csv;norefresh"
EVENT_TYPE = SOURCE_TYPE_NAME = 'haproxy'

class Services(object):
    BACKEND = 'BACKEND'
    FRONTEND = 'FRONTEND'
    ALL = (BACKEND, FRONTEND)

class HAProxy(CheckD):
    def __init__(self, name, config, agentConfig):
        CheckD.__init__(self, name, config, agentConfig)

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
    }

    def check(self):
        for host, conf in self.config.items():
            self.log.debug('Processing HAProxy data for %s' % host)
            try:
                data = self._fetch_data(conf)
            except:
                self.log.exception('Unable to get haproxy statistics for %s' % host)
                continue

            my_hostname = gethostname(self.agentConfig)
            self._process_data(data, my_hostname, self._process_metrics,
                self._process_events)

    def _fetch_data(self, conf):
        ''' Hit a given URL and return the parsed json '''
        # Try to fetch data from the stats URL
        agentConfig = self.agentConfig

        url = conf.get('url', None)
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, url, conf.get('username', None),
            conf.get('password', None))
        authhandler = urllib2.HTTPBasicAuthHandler(passman)
        opener = urllib2.build_opener(authhandler)
        urllib2.install_opener(opener)
        url = "%s%s" % (url, STATS_URL)

        self.log.debug("HAProxy Fetching haproxy search data from: %s" % url)

        req = urllib2.Request(url, None, headers(agentConfig))
        request = urllib2.urlopen(req)
        response = request.read()
        # Split the data by line
        return response.split('\n')

    def _process_data(self, data, my_hostname, metric_cb=None, event_cb=None):
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
            try:
                service = data_dict['svname']
            except:
                import pdb; pdb.set_trace()
            if data_dict['svname'] in Services.ALL:
                if not data_list and service == Services.FRONTEND:
                    data_list.append(data_dict)

                # Send the list of data to the metric and event callbacks
                if metric_cb:
                    metric_cb(data_list, service, my_hostname)
                if event_cb:
                    event_cb(data_list)

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

    def _process_events(self, data_list):
        ''' Main event processing loop. Events will be created for a service
        status change '''
        for data in data_list:
            hostname = data['svname']
            service_name = data['pxname']
            status = self.host_status.get("%s:%s" % (hostname,service_name), None)

            if status is None:
                self.host_status["%s:%s" % (hostname,service_name)] = data['status']
                continue

            if status != data['status']:
                # If the status of a host has changed, we trigger an event
                try:
                    lastchg = int(data['lastchg'])
                except:
                    lastchg = 0

                # Create the event object
                ev = self._create_event(self.agentConfig['api_key'],
                    data['status'], hostname, lastchg)
                self.event(ev)

                # Store this host status so we can check against it later
                self.host_status["%s:%s" % (hostname,service_name)] = data['status']

    def _create_event(self, api_key, status, hostname, lastchg):
        if status == "DOWN":
            alert_type = "error"
            title = "HAProxy reported a failure"
            msg = "%s has just been reported %s" % (hostname, status)
        else:
            alert_type = "info"
            title = "HAProxy status update"
            msg = "%s is back and %s" % (hostname, status)

        return {
            'timestamp': int(time.mktime(datetime.utcnow().timetuple())) - int(lastchg),
             'event_type': EVENT_TYPE,
             'host': hostname,
             'api_key': api_key,
             'msg_text': msg,
             'msg_title': title,
             'alert_type': alert_type,
             "source_type_name": SOURCE_TYPE_NAME,
             "event_object": hostname
        }