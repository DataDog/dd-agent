import sys, os, re, struct
import logging
import cPickle as pickle

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

try:
    from tornado.netutil import TCPServer
except Exception, e:
    logging.warn("Tornado < 2.1.1 detected, using compatibility TCPServer")
    from compat.tornadotcpserver import TCPServer


class GraphiteServer(TCPServer):

    def __init__(self, app, hostname, io_loop=None, ssl_options=None, **kwargs):
        logging.info('Graphite listener is started')
        self.app = app
        self.hostname = hostname
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)

    def handle_stream(self, stream, address):
        GraphiteConnection(stream, address, self.app, self.hostname)


class GraphiteConnection(object):

    def __init__(self, stream, address, app, hostname):
        logging.debug('received a new connection from %s', address)
        self.app = app
        self.stream = stream
        self.address = address
        self.hostname = hostname
        self.stream.set_close_callback(self._on_close)
        self.stream.read_bytes(4, self._on_read_header)

    def _on_read_header(self,data):
        try:
            size = struct.unpack("!I",data)[0]
            logging.debug("Receiving a string of size:" + str(size))
            self.stream.read_bytes(size, self._on_read_line)
        except Exception, e:
            logging.error(e)

    def _on_read_line(self, data):
        logging.debug('read a new line from %s', self.address)
        self._decode(data)

    def _on_close(self):
        logging.debug('client quit %s', self.address)

    def _parseMetric(self, metric):
        """Graphite does not impose a particular metric structure.
        So this is where you can insert logic to extract various bits
        out of the graphite metric name.

        For instance, if the hostname is in 4th position,
        you could use: host = components[3]
        """
        
        try:
            components = metric.split('.')

            host = self.hostname
            metric = metric
            device = "N/A"
        
            return metric, host, device
        except Exception, e:
            logging.exception("Unparsable metric: {0}".format(metric))
            return None, None, None

    def _postMetric(self, name, host, device, datapoint):

        ts = datapoint[0]
        value = datapoint[1]
        self.app.appendMetric("graphite", name, host, device, ts, value)        

    def _processMetric(self, metric, datapoint):
        """Parse the metric name to fetch (host, metric, device) and
            send the datapoint to datadog"""

        logging.debug("New metric: %s, values: %s" % (metric, datapoint))
        (metric,host,device) = self._parseMetric(metric)
        if metric is not None:    
            self._postMetric(metric,host,device, datapoint)
            logging.info("Posted metric: %s, host: %s, device: %s" % (metric, host, device))

    def _decode(self,data):

        try:
            datapoints = pickle.loads(data)
        except:
            logging.exception("Cannot decode grapite points")
            return
   
        for (metric, datapoint) in datapoints:
            try:
                datapoint = ( float(datapoint[0]), float(datapoint[1]) )
            except Exception, e:
                logging.error(e)
                continue
            
            self._processMetric(metric,datapoint) 

        self.stream.read_bytes(4, self._on_read_header)

def start_graphite_listener(port):
    echo_server = GraphiteServer()
    echo_server.listen(port)
    IOLoop.instance().start()

if __name__ == '__main__':
    start_graphite_listener(17124)
