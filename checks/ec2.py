"""EC2 metadata and metrics"""
import socket
import types
import urllib2

from checks import Check

class EC2(Check):
    """Retrieve EC2 metadata
    """
    URL = "http://169.254.169.254/latest/meta-data/"
    TIMEOUT = 0.1 # second

    def __init__(self, logger):
        Check.__init__(self, logger)
    
    @staticmethod
    def get_metadata():
        """Use the ec2 http service to introspect the instance. This adds latency if not running on EC2
        """
        # >>> import urllib2
        # >>> urllib2.urlopen('http://169.254.169.254/1.0/', timeout=1).read()
        # 'meta-data\nuser-data'
        # >>> urllib2.urlopen('http://169.254.169.254/latest/meta-data', timeout=1).read()
        # 'ami-id\nami-launch-index\nami-manifest-path\nhostname\ninstance-id\nlocal-ipv4\npublic-keys/\nreservation-id\nsecurity-groups'
        # >>> urllib2.urlopen('http://169.254.169.254/latest/meta-data/instance-id', timeout=1).read()
        # 'i-deadbeef'
        metadata = {}

        # Every call may add TIMEOUT seconds in latency so don't abuse this call
        # python 2.4 does not support an explicit timeout argument so force it here
        # Rather than monkey-patching urllib2, just lower the timeout globally for these calls
        socket_to = None
        try:
            socket_to = socket.getdefaulttimeout()
            socket.setdefaulttimeout(EC2.TIMEOUT)
        except:
            pass

        for k in ('instance-id', 'hostname', 'ami-id', 'local-ipv4', 'public-keys', 'reservation-id', 'security-groups'):
            try:
                v = urllib2.urlopen(EC2.URL + "/" + unicode(k)).read().strip()
                assert type(v) in (types.StringType, types.UnicodeType) and len(v) > 0, "%s is not a string" % v
                metadata[k] = v
            except:
                pass

        # Get fqdn
        try:
            metadata['fqdn'] = socket.getfqdn()
        except:
            pass

        try:
            if socket_to is None:
                socket_to = 3
            socket.setdefaulttimeout(socket_to)
        except:
            pass

        return metadata

    @staticmethod
    def get_instance_id():
        try:
            return EC2.get_metadata().get("instance-id", None)
        except:
            return None
