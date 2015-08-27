"""cAdvisor check
Collects metrics from cAdvisor instance
"""

# stdlib
import urllib2
from urlparse import urljoin

# project
from checks import AgentCheck
from util import json
# import json

DEFAULT_BASEURL = "http://localhost:4194/"
DEFAULT_METRICS_CMD = "/api/v1.3/subcontainers/"
DEFAULT_EVENTS_CMD = "/api/v1.3/events/"
DEFAULT_DOCKER_API_ENDPOINT = "unix://var/run/docker.sock/containers/json"

DEFAULT_SOCKET_TIMEOUT = 5

class cAdvisor(AgentCheck):
    """ Collect metrics and events from cAdvisor instance"""

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    # def _retrieve_docker_json(self, uri, params=None, multi=False):
    #     if params:
    #         uri = "%s?%s" % (uri, urllib.urlencode(params))
    #     self.log.debug("Connecting to Docker API at: %s" % uri)
    #     req = urllib2.Request(uri, None)

    #     try:
    #         request = self.url_opener.open(req)
    #     except urllib2.URLError, e:
    #         if "Errno 13" in str(e):
    #             raise Exception("Unable to connect to socket. dd-agent user must be part of the 'docker' group")
    #         raise

    #     response = request.read()
    #     response = response.replace('\n', '') # Some Docker API versions occassionally send newlines in responses
    #     self.log.debug('Docker API response: %s', response)
    #     if multi and "}{" in response: # docker api sometimes returns juxtaposed json dictionaries
    #         response = "[{0}]".format(response.replace("}{", "},{"))

    #     if not response:
    #         return []

    #     try:
    #         return json.loads(response)
    #     except Exception as e:
    #         self.log.error('Failed to parse Docker API response: %s', response)
    #         raise DockerJSONDecodeError

    def _retrieve_json(self, url):
        try:
            fd = urllib2.urlopen(url)
            raw_response = fd.read()
            fd.close()
            parsed_response = json.loads(raw_response)
        except Exception:
            return None
        
        return parsed_response

    def _retrieve_json_mock(self, url):
        return json.loads(open('cadvisor-subcontainers.json').read())

    def check(self, instance):
        self.baseurl = instance.get('baseurl', DEFAULT_BASEURL)
        self.metrics_cmd = urljoin(self.baseurl, DEFAULT_METRICS_CMD)
        self.events_cmd = urljoin(self.baseurl, DEFAULT_EVENTS_CMD)
        self._update_metrics(instance)

    def _discover_metrics(self, metric, dat, tags):
        type_ = type(dat)
        if type_ is int or type_ is long or type_ is float:
            self.rate(metric, long(dat), tags)
        elif type_ is dict:
            for k,v in dat.iteritems():
                self._discover_metrics(metric+'.%s'%k.lower(), v, tags)
        elif type_ is list:
            self._discover_metrics(metric, dat[-1], tags)
        else:
            return

    def _retrieve_docker_tags(self):
        params = {'all': True}
        docker_tags = {}
        for container in _retrieve_docker_json("unix://var/run/docker.sock/containers/json", params=params):
            id = container['Id']
            names = container['Names']
            docker_tags[id] = names
        
    def _update_metrics(self, instance):
        # docker_tags = self._retrieve_docker_tags()
        for subcontainer in self._retrieve_json(self.metrics_cmd):
            name = subcontainer['name']
            tags = [ 'container_name:%s' % name ]

            try:
                for label_name,label in subcontainer['spec']['labels'].iteritems():
                    tags.append('label.%s:%s'% (label_name, label))
            except KeyError:
                pass
            
            try:
                namespace = subcontainer['namespace']
                tags.append('namespace:%s' % namespace)
            except KeyError:
                namespace = 'kubernetes'
            
            stats = subcontainer['stats'][-1]
            try:
                self._discover_metrics(namespace+'.cpu', stats['cpu'], tags)
            except KeyError:
                pass
                
            try:
                self._discover_metrics(namespace+'.diskio', stats['diskio'], tags)
            except KeyError:
                pass

            try:
                self._discover_metrics(namespace+'.network', stats['network'], tags)
            except KeyError:
                pass
