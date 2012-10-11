from checks.services_checks import ServicesCheck, Status
import socket

class BadConfException(Exception): pass

class TCPCheck(ServicesCheck):

    def _load_conf(self, instance):
        # Fetches the conf

        port = instance.get('port', None)
        timeout = int(instance.get('timeout', 10))
        socket_type = None
        try:
            port = int(port)
        except Exception:
            raise BadConfException("%s is not a correct port." % str(port))

        try:
            url = instance.get('host', None)
            split = url.split(":")
        except Exception: # Would be raised if url is not a string 
            raise BadConfException("A valid url must be specified")

        # IPv6 address format: 2001:db8:85a3:8d3:1319:8a2e:370:7348
        if len(split) == 8: # It may then be a IP V6 address, we check that
            for block in split:
                if len(block) != 4:
                    raise BadConfException("%s is not a correct IPv6 address." % url)

            addr = url
            # It's a correct IP V6 address
            socket_type = socket.AF_INET6
            
        if socket_type is None:
            try:
                addr = socket.gethostbyname(url)
                socket_type = socket.AF_INET
            except Exception:
                raise BadConfException("URL: %s is not a correct IPv4, IPv6 or hostname" % addr)

        return addr, port, socket_type, timeout

    def _check(self, instance):
        addr, port, socket_type, timeout = self._load_conf(instance)
        try:    
            self.log.debug("Connecting to %s %s" % (addr, port))
            sock = socket.socket(socket_type)
            try:
                sock.settimeout(timeout)
                sock.connect((addr, port))
            finally:
                sock.close()

        except Exception, e:
            self.log.info("%s:%s is down" % (addr, port))
            return Status.DOWN, str(e)

        self.log.info("%s:%s is UP" % (addr, port))
        return Status.UP, "UP"