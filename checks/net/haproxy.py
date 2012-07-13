"""haproxy support

To enable stats in haproxy, declare the following in the default backend

    stats uri /my_stats
    stats auth datadog:isdevops
    stats refresh 5s

Verify that stats are acccesible at /my_stats with browser.

The csv link is then http://localhost:port/my_stats;csv;norefresh

#
pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,
public,FRONTEND,,,1,2,2000,68,43140,288607,0,0,2,,,,,OPEN,,,,,,,,,1,1,0,,,,0,1,0,2,,,,0,33,0,27,8,0,,1,2,69,,,
datadog,singleton,0,0,0,1,,58,20311,19313,,0,,8,0,25,0,no check,1,1,0,,,,,,1,2,1,,33,,2,0,,2,,,,0,1,0,24,0,0,0,,,,0,0,
datadog,BACKEND,0,0,1,1,0,67,43140,288183,0,0,,8,0,25,0,UP,1,1,0,,0,484,0,,1,2,0,,33,,1,1,,2,,,,0,33,0,25,8,0,,,,,0,0,
"""
import urllib2
from checks import *

def __init__(self, logger):
	Check.__init__(self, logger)
    self.logger.info('HAAAAAAPROXY')


def check(self, config):

    self.logger.info('HAAAAAAPROXY')

	host = config.get("haproxy", None)

	# Check if we are configured properly
    if host is None:
    	return False

    # Try to fetch data from the stats URL
    url = urlparse.urljoin(host,self.STATS_URL)

    self.logger.info("Fetching haproxy search data from: %s" % url)

    data = None
    try:
        data = self._get_data(config, url)
        raise Exception(data)

    except Exception,e:
        self.logger.exception('Unable to get haproxy statistics {0}'.format(e))
        raise Exception(data)
        return False

    raise exception(data)

    def _get_data(self, agentConfig, url):
        "Hit a given URL and return the parsed json"

        req = urllib2.Request(url, None, headers(agentConfig))
        request = urllib2.urlopen(req)
        response = request.read()

        raise Exception(data)

        return json.loads(response)




