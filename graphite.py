import sys, os, re, struct
import logging
import cPickle as pickle

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

logging.basicConfig(level=logging.INFO, format='%(levelname)s - - %(asctime)s %(message)s', datefmt='[%d/%b/%Y %H:%M:%S]')

try:
    from tornado.netutil import TCPServer
except Exception, e:
    logging.warn("Tornado < 2.1.1 detected, using compatibility TCPServer")
    from compat.tornadotcpserver import TCPServer


class GraphiteServer(TCPServer):

    def __init__(self, io_loop=None, ssl_options=None, **kwargs):
        logging.info('Graphite server is started')
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)

    def handle_stream(self, stream, address):
        GraphiteConnection(stream, address)


class GraphiteConnection(object):

    def __init__(self, stream, address):
        logging.info('receive a new connection from %s', address)
        self.stream = stream
        self.address = address
        self.stream.set_close_callback(self._on_close)
        self.stream.read_bytes(4, self._on_read_header)

    def _on_read_header(self,data):
        try:
            size = struct.unpack("!I",data)[0]
            logging.info("Receiving a string of size:" + str(size))
            self.stream.read_bytes(size, self._on_read_line)
        except Exception, e:
            logging.error(e)

    def _on_read_line(self, data):
        logging.info('read a new line from %s', self.address)
        self._decode(data)

    def _on_close(self):
        logging.info('client quit %s', self.address)
        self.stream_set.remove(self.stream)

    def _processMetric(metric, datapoint):
        logging.info("New metric: %s, values: %s" % (metric, datapoint))

    def _decode(self,data):

        try:
            datapoints = pickle.loads(data)
        except Error, e:
            logging.error(e)
            return
   
        print datapoints
 
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
