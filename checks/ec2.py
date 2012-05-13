"""EC2 metadata and metrics"""
import types
import urllib2

from checks import Check

class EC2(Check):
    """Retrieve EC2 metadata
    """
    URL = "http://169.254.169.254/1.0/meta-data/"
    TIMEOUT = 0.1 # second

    def __init__(self, logger):
        Check.__init__(self, logger)
    
    def get_metadata(self):
        """Use the ec2 http service to introspect the instance. This adds latency if not running on EC2
        """
        # >>> import urllib2
        # >>> urllib2.urlopen('http://169.254.169.254/1.0/', timeout=1).read()
        # 'meta-data\nuser-data'
        # >>> urllib2.urlopen('http://169.254.169.254/1.0/meta-data', timeout=1).read()
        # 'ami-id\nami-launch-index\nami-manifest-path\nhostname\ninstance-id\nlocal-ipv4\npublic-keys/\nreservation-id\nsecurity-groups'
        # >>> urllib2.urlopen('http://169.254.169.254/1.0/meta-data/instance-id', timeout=1).read()
        # 'i-deadbeef'
        metadata = {}

        # Every call may add TIMEOUT seconds in latency so don't abuse this call
        for k in ('instance-id', 'hostname', 'ami-id', 'local-ipv4', 'public-keys', 'reservation-id', 'security-groups'):
            try:
                v = urllib2.urlopen(self.URL + "/" + unicode(k), timeout=self.TIMEOUT).read().strip()
                assert type(v) in (types.StringType, types.UnicodeType) and len(v) > 0, "%s is not a string" % v
                metadata[k] = v
            except:
                self.logger.exception("(Ignore if !ec2) Cannot extract EC2 metadata %s" % k)
        return metadata
