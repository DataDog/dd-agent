#!/usr/bin/env python

"""
Pup.py
    Datadog
    www.datadoghq.com
    ---
    Make sense of your IT Data

    (C) Datadog, Inc. 2012-2013 all rights reserved
"""

# set up logging before importing any other components
from config import initialize_logging; initialize_logging('pup')

import os; os.umask(022)

# stdlib
from collections import defaultdict
import sys
import optparse
import os
import re
import time
import logging
import zlib

# Status page
import platform
from checks.check_status import DogstatsdStatus, ForwarderStatus, CollectorStatus, logger_info

# 3p
import tornado
from tornado import ioloop
from tornado import web
from tornado import websocket

# project
from config import get_config, get_version
from util import json, get_tornado_ioloop

log = logging.getLogger('pup')

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

# Define settings, path is different if using py2exe
frozen = getattr(sys, 'frozen', '')
if not frozen:
    agent_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
else:
    # Using py2exe
    agent_root = os.path.dirname(sys.executable)

settings = {
    "static_path": os.path.join(agent_root, "pup", "static"),
    "cookie_secret": "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
    "xsrf_cookies": True,
}

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
    except Exception:
        return False

def is_histogram(metric_name):
    split = metric_name.rsplit('.')
    if len(split) > 1:
        if split[-1] in HISTOGRAM_IGNORE:
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

def process_metric(metric_name, tags, points):
    split_metric_name = metric_name.split(".")
    if is_histogram(metric_name):
        # split everything
        namespace = split_metric_name[0]
        if namespace in AGENT_IGNORE:
            return
        metric_name = ".".join(split_metric_name[0:-1])
        stack_name = split_metric_name[-1]
        metrics[metric_name]['points'].append({ "stackName" : stack_name, "values" : points })
        metrics[metric_name]['type'] = "histogram"
        metrics[metric_name]['tags'] = tags
        metrics[metric_name]['freq'] = 15
    else:
        metrics[metric_name] = {"points" : points, "type" : "gauge", "tags" : tags, "freq" : 20}


def update(series):
    """ Updates statsd metrics from POST to /api/v1/series """
    for s in series:
        process_metric(s['metric'], s['tags'], s['points'])
        tags = s['tags']

def update_agent_metrics(metrics):
    for m in metrics:
        # m = ["system.net.bytes_sent", 1378995258, 8.552631578947368, { "hostname":"my-hostname, "device_name":"ham0"}]
        process_metric(m[0], m[3], [[m[1], m[2]]])

def agent_update(payload):
    """ Updates system metrics from POST to /intake """
    for p in payload:
        timestamp = payload['collection_timestamp']
        if (is_number(payload[p])) and p not in ['collection_timestamp', 'networkTraffic', 'metrics']:
            metric = AGENT_TRANSLATION.get(p, p)
            metrics[metric] = {"points" : [[timestamp, float(payload[p])]], "type" : "gauge", "freq" : 20}
        elif p == 'metrics':
            update_agent_metrics(payload[p])




class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render(os.path.join(agent_root, "pup", "pup.html"),
        title="Pup",
        port=port)

class StatusHandler(tornado.web.RequestHandler):
    def get(self):
        dogstatsd_status = DogstatsdStatus.load_latest_status()
        forwarder_status = ForwarderStatus.load_latest_status()
        collector_status = CollectorStatus.load_latest_status()
        self.render(os.path.join(agent_root, "pup", "status.html"),
            port=port,
            platform=platform.platform(),
            agent_version=get_version(),
            python_version=platform.python_version(),
            logger_info=logger_info(),
            dogstatsd=dogstatsd_status.to_dict(),
            forwarder=forwarder_status.to_dict(),
            collector=collector_status.to_dict(),
        )

class PostHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            body = json.loads(self.request.body)
            series = body['series']
        except Exception:
            return
        update(series)

class AgentPostHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            payload = json.loads(zlib.decompress(self.request.body))
        except Exception:
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

def tornado_logger(handler):
    """ Override the tornado logging method.
    If everything goes well, log level is DEBUG.
    Otherwise it's WARNING or ERROR depending on the response code. """
    if handler.get_status() < 400:
        log_method = log.debug
    elif handler.get_status() < 500:
        log_method = log.warning
    else:
        log_method = log.error
    request_time = 1000.0 * handler.request.request_time()
    log_method("%d %s %.2fms", handler.get_status(),
               handler._request_summary(), request_time)

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/status", StatusHandler),
    (r"/(.*\..*$)", tornado.web.StaticFileHandler,
     dict(path=settings['static_path'])),
    (r"/pupsocket", PupSocket),
    (r"/api/v1/series?", PostHandler),
    (r"/intake", AgentPostHandler),
], log_function=tornado_logger)

def run_pup(config):
    """ Run the pup server. """
    global port

    port = config.get('pup_port', 17125)
    interface = config.get('pup_interface', 'localhost')

    if config.get('non_local_traffic', False) is True:
        application.listen(port)
    else:
        # localhost in lieu of 127.0.0.1 allows for ipv6
        application.listen(port, address=interface)

    interval_ms = 2000
    io_loop = get_tornado_ioloop()
    scheduler = ioloop.PeriodicCallback(send_metrics, interval_ms, io_loop=io_loop)
    scheduler.start()
    io_loop.start()

def stop():
    """ Only used by the Windows service """
    get_tornado_ioloop().stop()

def main():
    """ Parses arguments and starts Pup server """

    c = get_config(parse_args=False)
    is_enabled = c['use_pup']

    if is_enabled:
        log.info("Starting pup.")
        log.warning("Pup is now deprecated and will be removed in a future release of the Datadog Agent")
        run_pup(c)
    else:
        log.info("Pup is disabled. Exiting")
        # We're exiting purposefully, so exit with zero (supervisor's expected
        # code). HACK: Sleep a little bit so supervisor thinks we've started cleanly
        # and thus can exit cleanly.
        time.sleep(4)
        sys.exit(0)


if __name__ == "__main__":
    main()
