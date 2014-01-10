from checks import Check
import socket
from cStringIO import StringIO

class Ganglia(Check):
    BUFFER = 4096
    TIMEOUT = 0.5
    PORT = 8651

    def __init__(self, logger):
        Check.__init__(self, logger)

    def check(self, agentConfig):
        self.logger.debug('Ganglia status: start')
        if 'ganglia_host' not in agentConfig or agentConfig['ganglia_host'] == '':
            self.logger.debug('ganglia_host configuration not set, skipping ganglia')
            return False

        try:
            host = agentConfig['ganglia_host']
            port = Ganglia.PORT
            try:
                port = int(agentConfig.get('ganglia_port', Ganglia.PORT))
            except Exception:
                pass
            self.logger.debug("Retrieving Ganglia XML from %s:%d" % (host, port))

            sio = StringIO()

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(Ganglia.TIMEOUT)
            try:
                s.connect((host, port))
                while True:
                    data = s.recv(Ganglia.BUFFER)
                    if len(data) > 0:
                        sio.write(data)
                    else:
                        break
            finally:
                if s is not None:
                    s.close()

            self.logger.debug('Ganglia status: done')
            return sio.getvalue()
        except Exception:
            self.logger.exception("Unable to get ganglia data")
            return False

