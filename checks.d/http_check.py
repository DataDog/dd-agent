from checks.services_checks import ServicesCheck, Status
from util import headers
import urllib2

class HTTPCheck(ServicesCheck):

    def _load_conf(self, instance):
        # Fetches the conf
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        url = instance.get('url', None)
        if url is None:
            raise Exception("Bad configuration. You must specify a url")
        return url, username, password, timeout

    def _check(self, instance):
        addr, username, password, timeout = self._load_conf(instance)
        try:
            self.log.debug("Connecting to %s" % addr)
            passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, addr, username, password)
            authhandler = urllib2.HTTPBasicAuthHandler(passman)
            opener = urllib2.build_opener(authhandler)
            urllib2.install_opener(opener)
            req = urllib2.Request(addr, None, headers(self.agentConfig))
            request = urllib2.urlopen(req, timeout=timeout)
        
        except urllib2.URLError, e:
            self.log.info("%s is DOWN" % addr)
            return Status.DOWN, str(e)

        except  urllib2.HTTPError, e:
            if int(e.code) >= 400:
                self.log.info("%s is DOWN, error code: %s" % (addr, str(e.code)))
                return Status.DOWN, str(e)

        except Exception, e:
            self.log.error("Unhandled exception %s" % str(e))
            raise

        self.log.info("%s is UP" % addr)
        return Status.UP, "UP"



