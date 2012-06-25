#!/usr/bin/python
"""
Pup.py
	Datadog
	www.datadoghq.com
	---
	Make sense of your IT Data

	Licensed uner the Simplified BSD License (see LICENSE)
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


# Check if using old version of Python. Pup's usage of defaultdict requires 2.5 or later,
# and tornado only supports 2.5 or later. The agent supports 2.6 onwards it seems.
if int(sys.version_info[1]) <= 5:
	sys.stderr.write("Pup requires python 2.6 or later.\n")
	sys.exit(2)

metrics = defaultdict(lambda : defaultdict(list))
listeners = {}
waiting = dict({"Waiting":1})
port = 8888

def is_number(n):
    try:
        float(n)
        return True
    except:
        return False

def is_histogram(s):
    split = s['metric'].rsplit('.')
    if len(split) > 1:
        return True
    else:
        return False

def flush(message):
    for listener in listeners:
        listener.write_message(message)

def send_metrics():
    if metrics == {}:
        flush(waiting)
    else: flush(metrics)
    metrics.clear()
        
def update(series):
    for s in series:
        tags = s['tags']
        if is_histogram(s):
            split = re.findall(r'\w+', s['metric'])
            metric = split[0]
            stack_name = ".".join(split[1:])
            values = s['points']
            metrics[metric]['points'].append({ "stackName" : stack_name, "values" : values })
            metrics[metric]['type'] = "histogram"
            metrics[metric]['tags'] = tags
        else:
            metric_type = s['type']
            metric = s['metric']
            points = s['points']
            metrics[metric] = {"points" : points, "type" : metric_type, "tags" : tags}

def agent_update(payload):
    for p in payload:
        timestamp = payload['collection_timestamp']
        if (is_number(payload[p])) and p not in ['collection_timestamp', 'networkTraffic']:
            metric = p
            metrics[metric] = {"points" : [[timestamp, float(payload[p])]], "type" : "gauge"}

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("pup.html",
        title="Pup, by Datadog",
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
    "login_url": "/login",
    "xsrf_cookies": True,
}

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/(graph\.png)", tornado.web.StaticFileHandler,
     dict(path=settings['static_path'])),
	(r"/(favicon\.ico)", tornado.web.StaticFileHandler,
	 dict(path=settings['static_path'])),
    (r"/(logo\.png)", tornado.web.StaticFileHandler,
     dict(path=settings['static_path'])),
	(r"/(OpenSans-Regular-webfont\.ttf)", tornado.web.StaticFileHandler,
	 dict(path=settings['static_path'])),
    (r"/(highlight.pack\.js)", tornado.web.StaticFileHandler,
     dict(path=settings['static_path'])),
 	(r"/(d3\.v2\.min\.js)", tornado.web.StaticFileHandler,
	 dict(path=settings['static_path'])),
	(r"/(jquery-1\.7\.2\.min\.js)", tornado.web.StaticFileHandler,
	 dict(path=settings['static_path'])),
	(r"/(jquery\.color\.min\.js)", tornado.web.StaticFileHandler,
	 dict(path=settings['static_path'])),
   	(r"/(pup\.full\.js)", tornado.web.StaticFileHandler,
     dict(path=settings['static_path'])),
   	(r"/(pup\.js)", tornado.web.StaticFileHandler,
     dict(path=settings['static_path'])),
    (r"/(pup\.css)", tornado.web.StaticFileHandler,
     dict(path=settings['static_path'])),
	(r"/(dark\.css)", tornado.web.StaticFileHandler,
	 dict(path=settings['static_path'])),
    (r"/pupsocket", PupSocket),
    (r"/api/v1/series?", PostHandler),
    (r"/intake/", AgentPostHandler),
])

def main():
    global port
    parser = argparse.ArgumentParser(description='Pup server to collect and display metrics at localhost (default port 8888) from dogapi, StatsD, and dd-agent.')
    parser.add_argument('-p', dest='port', default=8888, type=int, nargs='?',
                       help='localhost port number for the server to listen on. Default is port 8888.')
    args = parser.parse_args()
    port = args.port
    application.listen(port)

    interval_ms = 1000
    io_loop = ioloop.IOLoop.instance()
    scheduler = ioloop.PeriodicCallback(send_metrics, interval_ms, io_loop=io_loop)
    scheduler.start()
    io_loop.start()

if __name__ == "__main__":
    main()
