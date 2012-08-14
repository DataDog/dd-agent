#! /usr/bin/python
import urlparse
import urllib2
import socket

from checks import Check, gethostname
from util import json, headers

from datetime import datetime
import time

STATS_URL = ";csv;norefresh"
KINDS = ['BACKEND', 'FRONTEND']

class HAProxyEvents(Check):
    key = 'HAProxy'
    
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.host_status = {}

    def check(self, logger, config):
        self.events = []

        # Check if we are configured properly
        if config.get('haproxy_url', None) is None:
            return False
        data = None
        try:
            data = get_data(config, self.logger)
        except:
            self.logger.exception('Unable to get haproxy statistics')
            return False

        process_data(self, config, data)
        return self.events

    def _process_metric(self, data_list, kind, agentConfig):
        for data in data_list:
            hostname = data['svname']
            service = data['pxname']
            status = self.host_status.get("%s:%s" % (hostname,service), None)
            if not status:
                self.host_status["%s:%s" % (hostname,service)]=data['status']
                continue
            else:
                if status != data['status']:
                    # If the status of a host has changed, we trigger an event
                    try:
                        lastchg = int(data['lastchg'])
                    except:
                        lastchg = 0
                    self.events.append(self.create_event(agentConfig, data['status'], hostname, lastchg))
                    self.host_status["%s:%s" % (hostname,service)]=data['status']

    def create_event(self, agentConfig, status, hostname, lastchg):
        if status=="DOWN":
            alert_type = "error"
            title = "HAProxy reported a failure"
            msg = "%s has just been reported %s" % (hostname, status) 
            
        else:
            alert_type = "info"
            title = "HAProxy status update"
            msg = "%s is back and %s" % (hostname, status)
            

        return { 'timestamp': int(time.mktime(datetime.utcnow().timetuple()))-int(lastchg),
                 'event_type': 'haproxy',
                 'host': hostname,
                 'api_key': agentConfig['apiKey'],
                 'msg_text':msg,
                 'msg_title': title,
                 "alert_type": alert_type,
                 "source_type": "HAProxy",
                 "event_object": hostname
            }

class HAProxyMetrics(Check):
    METRICS = {
        "qcur": ("gauge", "queue.current"),
        "scur": ("gauge", "session.current"),
        "slim": ("gauge", "session.limit"),
        "stot": ("counter", "session.rate"),
        "bin": ("counter", "bytes.in_rate"),
        "bout": ("counter", "bytes.out_rate"),
        "dreq": ("counter", "denied.req_rate"),
        "dresp": ("counter", "denied.resp_rate"),
        "ereq": ("counter", "errors.req_rate"),
        "econ": ("counter", "errors.con_rate"),
        "eresp": ("counter", "errors.resp_rate"),
        "wretr": ("counter", "warnings.retr_rate"),
        "wredis": ("counter", "warnings.redis_rate"),
    }


    def __init__(self, logger):
        Check.__init__(self, logger)
        
        for metric_type, metric_suffix in HAProxyMetrics.METRICS.values():
            for kind in KINDS:
                name = ".".join(["haproxy", kind.lower(), metric_suffix])
                if metric_type == "counter":
                    self.counter(name)
                elif metric_type == "gauge":
                    self.gauge(name)
                else:
                    logger.error("Unknown metric type: %s" % metric_type)

    def check(self, config):
        # Check if we are configured properly
        if config.get('haproxy_url', None) is None:
            return False

        data = None
        try:
            data = get_data(config, self.logger)
            process_data(self, config, data)
            metrics = self.get_metrics()
            self.logger.info("metrics: {0}".format(metrics))
            return metrics
        except:
            self.logger.exception('Unable to get haproxy statistics')
            return False

    def _process_metric(self, data_list, kind, agentConfig):

        hosts_to_aggregate = {}
        for data in data_list:
            """
            Each element of data_list is a dictionary related to one host (one line) extracted from the csv.
            All of these elements should have the same value for 'pxname' key
            It should look like:
            data_list = [
            {'svname':'i-4562165', 'pxname':'dogweb', 'scur':'42', ...},
            {'svname':'i-2854985', 'pxname':'dogweb', 'scur':'1337', ...},
            ...
            ]
            """
            tags = ["type:%s" % kind]
            hostname = data['svname']
            service = data['pxname']

            if hostname==KINDS[1]:
                hostname = gethostname(agentConfig)

            if kind==KINDS[0]:
                tags.append('frontend:%s' % gethostname(agentConfig))
            tags.append('host:%s' % hostname)
            tags.append("service:%s" % service)

            hp = hostname.split(':')
            if len(hp) > 1:
                data_to_aggregate = hosts_to_aggregate.get(hp[0],[])
                data_to_aggregate.append(data)
                hosts_to_aggregate[hp[0]]=data_to_aggregate
                continue

            for key in data.keys():
                if HAProxyMetrics.METRICS.get(key):
                    self.logger.info("PROCESSING key:{0} value:{1} kind:{2} service:{3} host:{4}".format(key,data[key], kind,service, hostname))
                    try:
                        name = "haproxy."+kind.lower()+"."+HAProxyMetrics.METRICS.get(key,["nokey","nokey"])[1]
                        value = long(data[key])
                    except:
                        self.logger.info("SKIPPING key:{0} value:{1} kind:{2} service:{3} host:{4}".format(key,data[key], kind,service, hostname))
                        continue

                    self.logger.info("SAVING name:{0} value:{1} tags:{2}, host:{3}".format(name,value,tags, hostname))
                    self.save_sample(name, value, tags=tags, hostname=hostname)


        if hosts_to_aggregate:
            self._aggregate_hosts(hosts_to_aggregate, kind, agentConfig)


    def _aggregate_hosts(self, hosts_to_aggregate, kind, agentConfig):
        """If there are many instances of a service running on different ports of a same host,
        we don't want to create as many metrics as the number of instances.
        So we aggregate these metrics into one host"""
        return_list = []
        for hostname in hosts_to_aggregate.keys():
            data_list = hosts_to_aggregate[hostname]
            new_data = {}
            if len(data_list) == 1:
                new_data = data_list[0]

            else:
                for key in data_list[0]:
                    if data_list[0][key] and HAProxyMetrics.METRICS.get(key):
                        for i in range(len(data_list)):
                            new_data[key] = long(new_data.get(key,0)) + long(data_list[i][key])

            new_data['svname'] = hostname
            new_data['pxname'] = data_list[0]['pxname']

            return_list.append(new_data)

        self._process_metric(return_list, kind, agentConfig)


def process_data(check, agentConfig, data):
    # data[0] should look like this: "# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,"
    data_index = data[0].replace('#','').strip().split(',')
    
    data_list = []

    kind = ""
    for j in range(len(data)):
        line = data[j]
        data_dict = {}
        values = line.split(',')
        
        # We don't process the first line
        if len(values) < 2 or values[1]==data_index[1]:
            continue
        
        # We store each line's values in a dictionary
        for i in range(len(values)):
            if data_index[i].strip():
                data_dict[data_index[i].strip()]=values[i]

        kind = data_dict['svname']

        # We don't create metrics for aggregates
        if kind in KINDS:
            if not data_list and kind ==KINDS[1]:
                data_list.append(data_dict)
            check._process_metric(data_list, kind, agentConfig)
            data_list=[]

        else:
            data_list.append(data_dict)


def get_data(agentConfig, logger):
    "Hit a given URL and return the parsed json"
    # Try to fetch data from the stats URL
    url = agentConfig.get('haproxy_url', None)
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, agentConfig.get('haproxy_user', None), agentConfig.get('haproxy_password', None))
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)
    url = "%s%s" % (url,STATS_URL)

    logger.info("HAProxy Fetching haproxy search data from: %s" % url)

    req = urllib2.Request(url, None, headers(agentConfig))
    request = urllib2.urlopen(req)
    response = request.read()
    logger.debug(response)
    return response.split('\n')
