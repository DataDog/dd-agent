'''
A Python Statsd implementation with some datadog special sauce.
'''


import logging
import optparse
import random
import socket
import sys
import time
import threading

import dogapi


from metrics import MetricsAggregator

# create logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add formatter to ch
ch.setFormatter(formatter)
logger.addHandler(ch)


logger = logging.getLogger('dogstatsd')



class Reporter(threading.Thread):
    """
    The reporter periodically sends the aggregated metrics to the
    server.
    """

    def __init__(self, interval, metrics_aggregator, dog_http_api):
        threading.Thread.__init__(self)
        self.daemon = True
        self.interval = int(interval)
        self.finished = threading.Event()
        self.metrics_aggregator = metrics_aggregator
        self.dog_http_api = dog_http_api
        self.flush_count = 0

    def end(self):
        self.finished.set()

    def run(self):
        while True:
            if self.finished.is_set():
                break
            self.finished.wait(self.interval)
            self.flush()

    def flush(self):
        try:
            self.flush_count += 1
            metrics = self.metrics_aggregator.flush()
            count = len(metrics)
            if not count:
                logger.info("Flush #{0}: No metrics to flush.".format(self.flush_count))
                return
            logger.info("Flush #{0}: flushing {1} metrics".format(self.flush_count, count))
            self.dog_http_api.metrics(metrics)
        except:
            logger.exception("Error flushing metrics")



class Server(object):
    """
    A statsd udp server.
    """

    def __init__(self, metrics_aggregator, host, port):
        self.host = host
        self.port = int(port)
        self.address = (self.host, self.port)

        self.metrics_aggregator = metrics_aggregator

        self.buffer_size = 1024
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.address)

    def start(self):
        """ Run the server. """
        logger.info('Starting dogstatsd server on %s' % str(self.address))
        while True:
            try:
                data = self.socket.recv(self.buffer_size)
                self.metrics_aggregator.submit(data)
            except (KeyboardInterrupt, SystemExit):
                break
            except:
                logger.exception('Error receiving datagram')


def main():
    parser = optparse.OptionParser("usage: %prog [options] api_key")
    parser.add_option("-H", '--host', dest='host', default='localhost')
    parser.add_option("-p", '--port', dest='port', default='8125')
    parser.add_option("-a", '--api-host', dest='api_host', default='https://app.datadoghq.com')
    parser.add_option("-i", '--interval', dest='interval', default='10')
    options, args = parser.parse_args()

    if not len(args):
        parser.print_help()
        return sys.exit(1)

    api_key = args[0]
    dog_http_api = dogapi.http.DogHttpApi(api_key=api_key, api_host=options.api_host)

    # Create the aggregator (which is the point of communication between the
    # server and reporting threads.
    metrics_aggregator = MetricsAggregator()

    # Start the reporting thread.
    reporter = Reporter(options.interval, metrics_aggregator, dog_http_api)
    reporter.start()

    # Start the server.
    server = Server(metrics_aggregator, options.host, options.port)
    server.start()

    # If we're here, we're done.
    logger.info("Shutting down ...")


if __name__ == '__main__':
    main()

