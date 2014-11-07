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
# from config import initialize_logging; initialize_logging('pup')

import os; os.umask(022)

# stdlib
import sys
import os
import time
import logging

# Status page
import platform
from checks.check_status import DogstatsdStatus, ForwarderStatus, CollectorStatus, logger_info

# 3p
import tornado
from tornado import ioloop

# project
from config import get_version
from util import get_tornado_ioloop

log = logging.getLogger('pup')

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

port = 17125

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
    (r"/status", StatusHandler),
    (r"/(.*\..*$)", tornado.web.StaticFileHandler,
     dict(path=settings['static_path'])),
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

    io_loop = get_tornado_ioloop()
    io_loop.start()

def stop():
    """ Only used by the Windows service """
    get_tornado_ioloop().stop()
