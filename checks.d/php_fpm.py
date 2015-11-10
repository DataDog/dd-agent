# 3p
import requests
import json

# FPM Client - https://github.com/saltstack/salt-contrib/blob/master/modules/flup_fcgi_client.py
import flup_fcgi_client as fcgi_client

# project
from checks import AgentCheck
from util import headers


class PHPFPMCheck(AgentCheck):
    """
    Tracks basic php-fpm metrics via the status module -
    Now you can access it using HTTP or talking directly to the FastCGI process (this method doesn't require a webserver to be configured)
    Requires php-fpm pools to have the status option.
    See http://www.php.net/manual/de/install.fpm.configuration.php#pm.status-path for more details
    """
    instance = None

    SERVICE_CHECK_NAME = 'php_fpm.can_ping'

    GAUGES = {
        'listen queue': 'php_fpm.listen_queue.size',
        'idle processes': 'php_fpm.processes.idle',
        'active processes': 'php_fpm.processes.active',
        'total processes': 'php_fpm.processes.total',
    }

    MONOTONIC_COUNTS = {
        'accepted conn': 'php_fpm.requests.accepted',
        'max children reached': 'php_fpm.processes.max_reached',
        'slow requests': 'php_fpm.requests.slow',
    }

    def check(self, instance):
        self.instance = instance
        status_location = instance.get('status_location')
        ping_location = instance.get('ping_location')
        server = instance.get('server')

        if status_location is None and ping_location is None and server is None:
            raise Exception("No status_location, ping_location or server specified for this instance")

        auth = None
        user = instance.get('user')
        password = instance.get('password')

        tags = instance.get('tags', [])

        if user and password:
            auth = (user, password)

        if ping_location is not None:
            self._process_ping(auth, tags)

        if status_location is not None:
            self._process_status(auth, tags)


    def get_data(self, location, auth):
        server = self.instance.get('server')
        port = str(self.instance.get('port'))
        listen = str(self.instance.get('listen'))
        monitoring_type = self.instance.get('monitoring_type')

        print "Getting data from : " + server + ":" + port + " with protocol: " + monitoring_type

        if "fcgi" in monitoring_type.lower():      # Lets talk directly with the FPM process
            if server.lower() is "unix":
                fcgi = fcgi_client.FCGIApp(connect = listen)
            else:
                fcgi = fcgi_client.FCGIApp(host = server, port = port)
            # We need the Json version of it
            env = {
                'SCRIPT_FILENAME': location,
                'QUERY_STRING': 'json',
                'REQUEST_METHOD': 'GET',
                'SCRIPT_NAME': location,
                'REQUEST_URI': location,
                'GATEWAY_INTERFACE': 'CGI/1.1',
                'SERVER_SOFTWARE': 'ztc',
                'REDIRECT_STATUS': '200',
                'CONTENT_TYPE': '',
                'CONTENT_LENGTH': '0',
                #'DOCUMENT_URI': url,
                'DOCUMENT_ROOT': '/',
                'DOCUMENT_ROOT': '/var/www/'
            }
            print env
            try:
                code, _headers, ret, err = fcgi(env)
            except Exception, e:
                error = "{\"Error\" : \"Cannot get location %s on server %s port %s using protocol %s : %s\"}" % (location, server, port, monitoring_type, str(e))
                self.log.error(error)
                return None, None, error

            try:
                ret = json.loads(ret)
            finally:
                return ret, code, err

        else:                           # Lets talk HTTP
            try:
                # TODO: adding the 'full' parameter gets you per-process detailed
                # informations, which could be nice to parse and output as metrics
                url = "http://" + server + ":" + port + location
                resp = requests.get(url, auth=auth,
                                    headers=headers(self.agentConfig),
                                    params={'json': True})
                if resp.status_code is not 200:
                    result = "{\"Error\" : \"Status code is %s\"}" % str(resp.status_code)
                    print result
                    return None, resp.status_code, result

                try:
                    ret = resp.json()
                except Exception, e:
                    ret = resp
                finally:
                    return ret, resp.status_code, None

                return resp.json(), resp.status_code, None
            except Exception as e:
                self.log.error("Failed to get metrics from {0}.\nError {1}".format(url, e))
                return None, None, e

    def _process_status(self, auth, tags):
        data = {}

        status_location = self.instance.get('status_location')

        data, code, error = self.get_data(status_location, auth)
        print data

        pool_name = data.get('pool', 'default')

        metric_tags = tags + ["pool:{0}".format(pool_name)]

        for key, mname in self.GAUGES.iteritems():
            if key not in data:
                self.log.warn("Gauge metric {0} is missing from FPM status".format(key))
                continue
            self.gauge(mname, int(data[key]), tags=metric_tags)

        for key, mname in self.MONOTONIC_COUNTS.iteritems():
            if key not in data:
                self.log.warn("Counter metric {0} is missing from FPM status".format(key))
                continue
            self.monotonic_count(mname, int(data[key]), tags=metric_tags)

        # return pool, to tag the service check with it if we have one
        return pool_name

    def _process_ping(self,auth, tags):

        ping_location = self.instance.get('ping_location')
        ping_reply = self.instance.get('ping_reply')

        if ping_reply is None:
            ping_reply = 'pong'

        sc_tags = ["ping_url:{0}".format(ping_location)]

        data, code, error = self.get_data(ping_location, auth)
        if code is not 200 or ping_reply not in data:
            self.service_check(self.SERVICE_CHECK_NAME,
                               AgentCheck.CRITICAL, tags=sc_tags, message=str(error))
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=sc_tags)

# There is only here to make it easy to test/dev the Check outside the DataDog Agent Environment, e.g. from a IDE
if __name__ == '__main__':
    #logging.basicConfig()
    check, instances = PHPFPMCheck.from_yaml('/etc/dd-agent/conf.d/php_fpm.yaml')
    for instance in instances:
        print "\nRunning the check against : %s ." % (instance['status_location'])
        check.check(instance)
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())
