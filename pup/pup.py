#!/usr/bin/python

"""
Pup.py
    Datadog
    www.datadoghq.com
    ---
    Make sense of your IT Data

    (C) Datadog, Inc. 2012 all rights reserved
"""

import tornado
from tornado import ioloop
from tornado import web
from tornado import websocket

from collections import defaultdict

import sys
import os
import json
import argparse
import re

AGENT_TRANSLATION = {
    'cpuUser'     : 'CPU user (%)',
    'cpuSystem'   : 'CPU system (%)',
    'cpuWait'     : 'CPU iowait (%)',
    'cpuIdle'     : 'CPU idle (%)',
    'cpuStolen'   : 'CPU stolen (%)',
    'memPhysUsed' : 'Memory used',
    'memPhysFree' : 'Memory free',
    'memPhysTotal': 'system.mem.total',
    'memCached'   : 'system.mem.cached',
    'memBuffers'  : 'system.mem.buffered',
    'memShared'   : 'system.mem.shared',
    'memPhysUsable': 'system.mem.usable',
    'memSwapUsed' : 'Used Swap',
    'memSwapFree' : 'Available Swap',
    'memSwapTotal': 'system.swap.total',
    'loadAvrg'    : 'Load Averages 1',
    'loadAvrg1'   : 'Load Averages 1',
    'loadAvrg5'   : 'Load Averages 5',
    'loadAvrg15'  : 'Load Averages 15',
    'nginxConnections'          : 'nginx.net.connections',
    'nginxReqPerSec'            : 'nginx.net.request_per_s',
    'nginxReading'              : 'nginx.net.reading',
    'nginxWriting'              : 'nginx.net.writing',
    'nginxWaiting'              : 'nginx.net.waiting',
    'mysqlConnections'          : 'mysql.net.connections',
    'mysqlCreatedTmpDiskTables' : 'mysql.performance.created_tmp_disk_tables',
    'mysqlMaxUsedConnections'   : 'mysql.net.max_connections',
    'mysqlQueries'              : 'mysql.performance.queries',
    'mysqlQuestions'            : 'mysql.performance.questions',
    'mysqlOpenFiles'            : 'mysql.performance.open_files',
    'mysqlSlowQueries'          : 'mysql.performance.slow_queries',
    'mysqlTableLocksWaited'     : 'mysql.performance.table_locks_waited',
    'mysqlInnodbDataReads'      : 'mysql.innodb.data_reads', 
    'mysqlInnodbDataWrites'     : 'mysql.innodb.data_writes',
    'mysqlInnodbOsLogFsyncs'    : 'mysql.innodb.os_log_fsyncs',
    'mysqlThreadsConnected'     : 'mysql.performance.threads_connected',
    'mysqlKernelTime'           : 'mysql.performance.kernel_time',
    'mysqlUserTime'             : 'mysql.performance.user_time',
    'mysqlSecondsBehindMaster'  : 'mysql.replication.seconds_behind_master',
    'apacheReqPerSec'           : 'apache.net.request_per_s',
    'apacheConnections'         : 'apache.net.connections',
    'apacheIdleWorkers'         : 'apache.performance.idle_workers',
    'apacheBusyWorkers'         : 'apache.performance.busy_workers',
    'apacheCPULoad'             : 'apache.performance.cpu_load',
    'apacheUptime'              : 'apache.performance.uptime',
    'apacheTotalBytes'          : 'apache.net.bytes',
    'apacheTotalAccesses'       : 'apache.net.hits',
    'apacheBytesPerSec'         : 'apache.net.bytes_per_s',
}

# Comes along with the histogram series. Only min/avg/max are plotted.
HISTOGRAM_IGNORE = [
    "count",
    "50percentile",
    "75percentile",
    "85percentile",
    "95percentile",
    "99percentile"
]

# Ignored namespaces for agent and other Datadog software
AGENT_IGNORE = [
    'dd',
    'app',
    'events'
]

# Check if using old version of Python. Pup's usage of defaultdict requires 2.5 or later,
# and tornado only supports 2.5 or later. The agent supports 2.6 onwards it seems.
if int(sys.version_info[1]) <= 5:
    sys.stderr.write("Pup requires python 2.6 or later.\n")
    sys.exit(2)

metrics = defaultdict(lambda : defaultdict(list))
listeners = {}
port = 17125

def is_number(n):
    try:
        float(n)
        return True
    except:
        return False

def is_histogram(s):
    split = s['metric'].rsplit('.')
    if len(split) > 1:
        if split[-1] not in HISTOGRAM_IGNORE:
            return True
    return False

def flush(message):
    for listener in listeners:
        listener.write_message(message)

def send_metrics():
    if metrics == {}:
        flush(dict({"Waiting":1}))
    else: flush(metrics)
    metrics.clear()

def update(series):
    """ Updates statsd metrics from POST to /api/v1/series """
    for s in series:
        tags = s['tags']
        split_metric_name = s['metric'].split(".")
        if is_histogram(s):
            # split everything
            namespace = split_metric_name[0]
            if namespace in AGENT_IGNORE:
                continue
            metric_name = ".".join(split_metric_name[0:-1])
            stack_name = split_metric_name[-1]
            values = s['points']
            metrics[metric_name]['points'].append({ "stackName" : stack_name, "values" : values })
            metrics[metric_name]['type'] = "histogram"
            metrics[metric_name]['tags'] = tags
            metrics[metric_name]['freq'] = 15
        else:
            if split_metric_name[-1] in HISTOGRAM_IGNORE:
                continue
            metric_name = s['metric']
            points = s['points']
            metrics[metric_name] = {"points" : points, "type" : "line", "tags" : tags, "freq" : 15}

def agent_update(payload):
    """ Updates system metrics from POST to /intake """
    for p in payload:
        timestamp = payload['collection_timestamp']
        if (is_number(payload[p])) and p not in ['collection_timestamp', 'networkTraffic']:
            metric = AGENT_TRANSLATION.get(p, p)
            metrics[metric] = {"points" : [[timestamp, float(payload[p])]], "type" : "gauge", "freq" : 20}

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("pup.html",
        title="Pup",
        port=port)
            
class PostHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            body = json.loads(self.request.body)
            series = body['series']
        except:
            #log.exception("Error parsing the POST request body")
            return
        update(series)

class AgentPostHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            payload = json.loads(self.get_argument('payload'))
        except:
            #log.exception("Error parsing the agent's POST request body")
            return
        agent_update(payload)

class PupSocket(websocket.WebSocketHandler):
    def open(self):
        metrics = {}
        listeners[self] = self

    def on_message(self):
        pass

    def on_close(self):
        del listeners[self]

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
    "xsrf_cookies": True,
}

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/(.*\..*$)", tornado.web.StaticFileHandler,
     dict(path=settings['static_path'])),
    (r"/pupsocket", PupSocket),
    (r"/api/v1/series?", PostHandler),
    (r"/intake/", AgentPostHandler),
])

def main():
    """ Parses arguments and starts Pup server """
    global port
    parser = argparse.ArgumentParser(description='Pup server to collect and display metrics at localhost (default port 17125) from dogapi, StatsD, and dd-agent.')
    parser.add_argument('-p', dest='port', default=17125, type=int, nargs='?',
                       help='localhost port number for the server to listen on. Default is port 17125.')
    args = parser.parse_args()
    port = args.port
    application.listen(port)

    interval_ms = 2000
    io_loop = ioloop.IOLoop.instance()
    scheduler = ioloop.PeriodicCallback(send_metrics, interval_ms, io_loop=io_loop)
    scheduler.start()
    io_loop.start()

if __name__ == "__main__":
    main()
