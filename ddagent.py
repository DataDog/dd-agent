#!/opt/datadog-agent/embedded/bin/python
'''
    Datadog
    www.datadoghq.com
    ----
    Make sense of your IT Data

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
    (C) Datadog, Inc. 2010-2013 all rights reserved
'''

# set up logging before importing any other components
from config import initialize_logging; initialize_logging('forwarder')
from config import get_logging_config

import os; os.umask(022)

# Standard imports
import logging
import os
import sys
import threading
import zlib
from Queue import Queue, Full
from subprocess import Popen
from hashlib import md5
from datetime import datetime, timedelta
from socket import gaierror, error as socket_error
from urlparse import urlparse

# Tornado
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.escape import json_decode
from tornado.options import define, parse_command_line, options

# agent import
from util import Watchdog, get_uuid, get_hostname, json, get_tornado_ioloop
from emitter import http_emitter
from config import get_config, get_version
from checks.check_status import ForwarderStatus
from transaction import Transaction, TransactionManager
import modules

# 3rd party
try:
    import pycurl
except ImportError:
    # For the source install, pycurl might not be installed
    pycurl = None

log = logging.getLogger('forwarder')
log.setLevel(get_logging_config()['log_level'] or logging.INFO)

DD_ENDPOINT  = "dd_url"

TRANSACTION_FLUSH_INTERVAL = 5000 # Every 5 seconds
WATCHDOG_INTERVAL_MULTIPLIER = 10 # 10x flush interval
HEADERS_TO_REMOVE = [
    'Host',
    'Content-Length',
]


# Maximum delay before replaying a transaction
MAX_WAIT_FOR_REPLAY = timedelta(seconds=90)

# Maximum queue size in bytes (when this is reached, old messages are dropped)
MAX_QUEUE_SIZE = 30 * 1024 * 1024 # 30MB

THROTTLING_DELAY = timedelta(microseconds=1000000/2) # 2 msg/second

LEGACY_DATADOG_URLS = [
    "app.datadoghq.com",
    "app.datad0g.com",
]

class EmitterThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.__name = kwargs['name']
        self.__emitter = kwargs.pop('emitter')()
        self.__logger = kwargs.pop('logger')
        self.__config = kwargs.pop('config')
        self.__max_queue_size = kwargs.pop('max_queue_size', 100)
        self.__queue = Queue(self.__max_queue_size)
        threading.Thread.__init__(self, *args, **kwargs)
        self.daemon = True

    def run(self):
        while True:
            (data, headers) = self.__queue.get()
            try:
                self.__logger.debug('Emitter %r handling a packet', self.__name)
                self.__emitter(data, self.__logger, self.__config)
            except Exception:
                self.__logger.error('Failure during operation of emitter %r', self.__name, exc_info=True)

    def enqueue(self, data, headers):
        try:
            self.__queue.put((data, headers), block=False)
        except Full:
            self.__logger.warn('Dropping packet for %r due to backlog', self.__name)

class EmitterManager(object):
    """Track custom emitters"""

    def __init__(self, config):
        self.agentConfig = config
        self.emitterThreads = []
        for emitter_spec in [s.strip() for s in self.agentConfig.get('custom_emitters', '').split(',')]:
            if len(emitter_spec) == 0: continue
            logging.info('Setting up custom emitter %r', emitter_spec)
            try:
                thread = EmitterThread(
                    name=emitter_spec,
                    emitter=modules.load(emitter_spec, 'emitter'),
                    logger=logging,
                    config=config,
                )
                thread.start()
                self.emitterThreads.append(thread)
            except Exception, e:
                logging.error('Unable to start thread for emitter: %r', emitter_spec, exc_info=True)
        logging.info('Done with custom emitters')

    def send(self, data, headers=None):
        if not self.emitterThreads:
            return # bypass decompression/decoding
        if headers and headers.get('Content-Encoding') == 'deflate':
            data = zlib.decompress(data)
        data = json_decode(data)
        for emitterThread in self.emitterThreads:
            logging.info('Queueing for emitter %r', emitterThread.name)
            emitterThread.enqueue(data, headers)

class MetricTransaction(Transaction):

    _application = None
    _trManager = None
    _endpoints = []
    _emitter_manager = None

    @classmethod
    def set_application(cls, app):
        cls._application = app
        cls._emitter_manager = EmitterManager(cls._application._agentConfig)

    @classmethod
    def set_tr_manager(cls, manager):
        cls._trManager = manager

    @classmethod
    def get_tr_manager(cls):
        return cls._trManager

    @classmethod
    def set_endpoints(cls):

        # Only send data to Datadog if an API KEY exists
        # i.e. user is also Datadog user
        try:
            is_dd_user = 'api_key' in cls._application._agentConfig\
                and 'use_dd' in cls._application._agentConfig\
                and cls._application._agentConfig['use_dd']\
                and cls._application._agentConfig.get('api_key')
            if is_dd_user:
                log.warn("You are a Datadog user so we will send data to https://app.datadoghq.com")
                cls._endpoints.append(DD_ENDPOINT)
        except Exception:
            log.info("Not a Datadog user")

    def __init__(self, data, headers):
        self._data = data
        self._headers = headers
        self._headers['DD-Forwarder-Version'] = get_version()

        # Call after data has been set (size is computed in Transaction's init)
        Transaction.__init__(self)

        # Emitters operate outside the regular transaction framework
        if self._emitter_manager is not None:
            self._emitter_manager.send(data, headers)

        # Insert the transaction in the Manager
        self._trManager.append(self)
        log.debug("Created transaction %d" % self.get_id())
        self._trManager.flush()

    def __sizeof__(self):
        return sys.getsizeof(self._data)

    @classmethod
    def get_url_endpoint(cls, endpoint):
        default_url = cls._application._agentConfig[endpoint]
        parsed_url = urlparse(default_url)
        if parsed_url.netloc not in LEGACY_DATADOG_URLS:
            return default_url

        subdomain = parsed_url.netloc.split(".")[0]

        # Replace https://app.datadoghq.com in https://5-2-0-app.agent.datadoghq.com
        return default_url.replace(subdomain, 
            "{0}-{1}.agent".format(
                get_version().replace(".", "-"),
                subdomain))

    def get_url(self, endpoint):
        endpoint_base_url = self.get_url_endpoint(endpoint)
        api_key = self._application._agentConfig.get('api_key')
        if api_key:
            return endpoint_base_url + '/intake?api_key=%s' % api_key
        return endpoint_base_url + '/intake'

    def flush(self):
        for endpoint in self._endpoints:
            url = self.get_url(endpoint)
            log.debug("Sending metrics to endpoint %s at %s" % (endpoint, url))

            # Getting proxy settings
            proxy_settings = self._application._agentConfig.get('proxy_settings', None)

            tornado_client_params = {
                'url': url,
                'method': 'POST',
                'body': self._data,
                'headers': self._headers,
                'validate_cert': not self._application.skip_ssl_validation,
            }

            # Remove headers that were passed by the emitter. Those don't apply anymore
            # This is pretty hacky though as it should be done in pycurl or curl or tornado
            for h in HEADERS_TO_REMOVE:
                if h in tornado_client_params['headers']:
                    del tornado_client_params['headers'][h]
                    log.debug("Removing {0} header.".format(h))

            force_use_curl = False

            if proxy_settings is not None:
                force_use_curl = True
                if pycurl is not None:
                    log.debug("Configuring tornado to use proxy settings: %s:****@%s:%s" % (proxy_settings['user'],
                        proxy_settings['host'], proxy_settings['port']))
                    tornado_client_params['proxy_host'] = proxy_settings['host']
                    tornado_client_params['proxy_port'] = proxy_settings['port']
                    tornado_client_params['proxy_username'] = proxy_settings['user']
                    tornado_client_params['proxy_password'] = proxy_settings['password']

                    if self._application._agentConfig.get('proxy_forbid_method_switch'):
                        # See http://stackoverflow.com/questions/8156073/curl-violate-rfc-2616-10-3-2-and-switch-from-post-to-get
                        tornado_client_params['prepare_curl_callback'] = lambda curl: curl.setopt(pycurl.POSTREDIR, pycurl.REDIR_POST_ALL)
                
            if (not self._application.use_simple_http_client or force_use_curl) and pycurl is not None:
                ssl_certificate = self._application._agentConfig.get('ssl_certificate', None)
                tornado_client_params['ca_certs'] = ssl_certificate

            req = tornado.httpclient.HTTPRequest(**tornado_client_params)
            use_curl = force_use_curl or self._application._agentConfig.get("use_curl_http_client") and not self._application.use_simple_http_client
            
            if use_curl:
                if pycurl is None:
                    log.error("dd-agent is configured to use the Curl HTTP Client, but pycurl is not available on this system.")
                else:
                    log.debug("Using CurlAsyncHTTPClient")
                    tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
            else:
                log.debug("Using SimpleHTTPClient")
            http = tornado.httpclient.AsyncHTTPClient()
            http.fetch(req, callback=self.on_response)

    def on_response(self, response):
        if response.error:
            log.error("Response: %s" % response)
            self._trManager.tr_error(self)
        else:
            self._trManager.tr_success(self)

        self._trManager.flush_next()


class APIMetricTransaction(MetricTransaction):

    def get_url(self, endpoint):
        endpoint_base_url = self.get_url_endpoint(endpoint)
        config = self._application._agentConfig
        api_key = config['api_key']
        url = endpoint_base_url + '/api/v1/series/?api_key=' + api_key
        return url

    def get_data(self):
        return self._data


class StatusHandler(tornado.web.RequestHandler):

    def get(self):
        threshold = int(self.get_argument('threshold', -1))

        m = MetricTransaction.get_tr_manager()

        self.write("<table><tr><td>Id</td><td>Size</td><td>Error count</td><td>Next flush</td></tr>")
        transactions = m.get_transactions()
        for tr in transactions:
            self.write("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" %
                (tr.get_id(), tr.get_size(), tr.get_error_count(), tr.get_next_flush()))
        self.write("</table>")

        if threshold >= 0:
            if len(transactions) > threshold:
                self.set_status(503)

class AgentInputHandler(tornado.web.RequestHandler):

    def post(self):
        """Read the message and forward it to the intake"""

        # read message
        msg = self.request.body
        headers = self.request.headers

        if msg is not None:
            # Setup a transaction for this message
            tr = MetricTransaction(msg, headers)
        else:
            raise tornado.web.HTTPError(500)

        self.write("Transaction: %s" % tr.get_id())

class ApiInputHandler(tornado.web.RequestHandler):

    def post(self):
        """Read the message and forward it to the intake"""

        # read message
        msg = self.request.body
        headers = self.request.headers

        if msg is not None:
            # Setup a transaction for this message
            tr = APIMetricTransaction(msg, headers)
        else:
            raise tornado.web.HTTPError(500)


class Application(tornado.web.Application):

    def __init__(self, port, agentConfig, watchdog=True, skip_ssl_validation=False, use_simple_http_client=False):
        self._port = int(port)
        self._agentConfig = agentConfig
        self._metrics = {}
        MetricTransaction.set_application(self)
        MetricTransaction.set_endpoints()
        self._tr_manager = TransactionManager(MAX_WAIT_FOR_REPLAY,
            MAX_QUEUE_SIZE, THROTTLING_DELAY)
        MetricTransaction.set_tr_manager(self._tr_manager)

        self._watchdog = None
        self.skip_ssl_validation = skip_ssl_validation or agentConfig.get('skip_ssl_validation', False)
        self.use_simple_http_client = use_simple_http_client
        if self.skip_ssl_validation:
            log.info("Skipping SSL hostname validation, useful when using a transparent proxy")

        if watchdog:
            watchdog_timeout = TRANSACTION_FLUSH_INTERVAL * WATCHDOG_INTERVAL_MULTIPLIER
            self._watchdog = Watchdog(watchdog_timeout,
                max_mem_mb=agentConfig.get('limit_memory_consumption', None))

    def log_request(self, handler):
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

    def appendMetric(self, prefix, name, host, device, ts, value):

        if self._metrics.has_key(prefix):
            metrics = self._metrics[prefix]
        else:
            metrics = {}
            self._metrics[prefix] = metrics

        if metrics.has_key(name):
            metrics[name].append([host, device, ts, value])
        else:
            metrics[name] = [[host, device, ts, value]]

    def _postMetrics(self):

        if len(self._metrics) > 0:
            self._metrics['uuid'] = get_uuid()
            self._metrics['internalHostname'] = get_hostname(self._agentConfig)
            self._metrics['apiKey'] = self._agentConfig['api_key']
            MetricTransaction(json.dumps(self._metrics),
                headers={'Content-Type': 'application/json'})
            self._metrics = {}

    def run(self):
        handlers = [
            (r"/intake/?", AgentInputHandler),
            (r"/api/v1/series/?", ApiInputHandler),
            (r"/status/?", StatusHandler),
        ]

        settings = dict(
            cookie_secret="12oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            xsrf_cookies=False,
            debug=False,
            log_function=self.log_request
        )

        non_local_traffic = self._agentConfig.get("non_local_traffic", False)

        tornado.web.Application.__init__(self, handlers, **settings)
        http_server = tornado.httpserver.HTTPServer(self)

        try:
            # non_local_traffic must be == True to match, not just some non-false value
            if non_local_traffic is True:
                http_server.listen(self._port)
            else:
                # localhost in lieu of 127.0.0.1 to support IPv6
                try:
                    http_server.listen(self._port, address = self._agentConfig['bind_host'])
                except gaierror:
                    log.warning("localhost seems undefined in your host file, using 127.0.0.1 instead")
                    http_server.listen(self._port, address = "127.0.0.1")
                except socket_error, e:
                    if "Errno 99" in str(e):
                        log.warning("IPv6 doesn't seem to be fully supported. Falling back to IPv4")
                        http_server.listen(self._port, address = "127.0.0.1")
                    else:
                        raise
        except socket_error, e:
            log.exception("Socket error %s. Is another application listening on the same port ? Exiting", e)
            sys.exit(1)
        except Exception, e:
            log.exception("Uncaught exception. Forwarder is exiting.")
            sys.exit(1)

        log.info("Listening on port %d" % self._port)

        # Register callbacks
        self.mloop = get_tornado_ioloop()

        logging.getLogger().setLevel(get_logging_config()['log_level'] or logging.INFO)

        def flush_trs():
            if self._watchdog:
                self._watchdog.reset()
            self._postMetrics()
            self._tr_manager.flush()

        tr_sched = tornado.ioloop.PeriodicCallback(flush_trs,TRANSACTION_FLUSH_INTERVAL,
            io_loop = self.mloop)

        # Register optional Graphite listener
        gport = self._agentConfig.get("graphite_listen_port", None)
        if gport is not None:
            log.info("Starting graphite listener on port %s" % gport)
            from graphite import GraphiteServer
            gs = GraphiteServer(self, get_hostname(self._agentConfig), io_loop=self.mloop)
            if non_local_traffic is True:
                gs.listen(gport)
            else:
                gs.listen(gport, address = "localhost")

        # Start everything
        if self._watchdog:
            self._watchdog.reset()
        tr_sched.start()

        self.mloop.start()
        log.info("Stopped")

    def stop(self):
        self.mloop.stop()

def init(skip_ssl_validation=False, use_simple_http_client=False):
    agentConfig = get_config(parse_args = False)

    port = agentConfig.get('listen_port', 17123)
    if port is None:
        port = 17123
    else:
        port = int(port)

    app = Application(port, agentConfig, skip_ssl_validation=skip_ssl_validation, use_simple_http_client=use_simple_http_client)

    def sigterm_handler(signum, frame):
        log.info("caught sigterm. stopping")
        app.stop()

    import signal
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)

    return app

def main():
    define("sslcheck", default=1, help="Verify SSL hostname, on by default")
    define("use_simple_http_client", default=0, help="Use Tornado SimpleHTTPClient instead of CurlAsyncHTTPClient")
    args = parse_command_line()
    skip_ssl_validation = False
    use_simple_http_client = False

    if unicode(options.sslcheck) == u"0":
        skip_ssl_validation = True

    if unicode(options.use_simple_http_client) == u"1":
        use_simple_http_client = True

    # If we don't have any arguments, run the server.
    if not args:
        import tornado.httpclient
        app = init(skip_ssl_validation, use_simple_http_client=use_simple_http_client)
        try:
            app.run()
        except Exception:
            log.exception("Uncaught exception in the forwarder")
        finally:
            ForwarderStatus.remove_latest_status()

    else:
        usage = "%s [help|info]. Run with no commands to start the server" % (
                                        sys.argv[0])
        command = args[0]
        if command == 'info':
            logging.getLogger().setLevel(logging.ERROR)
            return ForwarderStatus.print_latest_status()
        elif command == 'help':
            print usage
        else:
            print "Unknown command: %s" % command
            print usage
            return -1
    return 0

if __name__ == "__main__":
    sys.exit(main())
