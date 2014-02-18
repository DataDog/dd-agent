import urllib2
import urllib
import httplib
import socket
import os
from urlparse import urlsplit, urljoin
from util import json, headers
from checks import AgentCheck

LXC_PATH = "/sys/fs/cgroup/{0}/lxc/{1}/{0}.stat"
LXC_METRICS = ["memory", "cpuacct", "blkio"]
USER_HZ = 1000


class UnixHTTPConnection(httplib.HTTPConnection, object):
    def __init__(self, unix_socket):
        self._unix_socket = unix_socket

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._unix_socket)
        self.sock = sock

    def __call__(self, *args, **kwargs):
        httplib.HTTPConnection.__init__(self, *args, **kwargs)
        return self


class UnixSocketHandler(urllib2.AbstractHTTPHandler):
    def unix_open(self, req):
        full_path = "{1}{2}".format(*urlsplit(req.get_full_url()))
        path = os.path.sep
        for part in full_path.split("/"):
            path = os.path.join(path, part)
            if not os.path.exists(path):
                break
            unix_socket = path
        # add a host or else urllib2 complains
        url = req.get_full_url().replace(unix_socket, "/localhost")
        new_req = urllib2.Request(url, req.get_data(), dict(req.header_items()))
        new_req.timeout = req.timeout
        return self.do_open(UnixHTTPConnection(unix_socket), new_req)

    unix_request = urllib2.AbstractHTTPHandler.do_request_


class Docker(AgentCheck):
    def __init__(self, *args, **kwargs):
        super(Docker, self).__init__(*args, **kwargs)
        urllib2.install_opener(urllib2.build_opener(UnixSocketHandler()))

    def check(self, instance):
        tags = instance.get("tags") or []

        for container in self._get_containers(instance):
            container = self._get_container(instance, container["Id"])

            container_tags = list(tags)
            for key in ["ID", "Name", "Created", "Driver", "Path"]:
                container_tags.append("%s:%s" % (key.lower(), container[key]))
            for key in ["Hostname", "Image"]:
                container_tags.append("%s:%s" % (key.lower(), container["Config"][key]))

            for metric in LXC_METRICS:
                stat_file = LXC_PATH.format(metric, container["ID"])
                if not os.path.exists(stat_file):
                    continue
                with open(stat_file) as fp:
                    for line in fp:
                        data, value = line.strip().split(" ")
                        self.gauge("docker.{0}.{1}".format(metric, data), int(value), tags=container_tags)

    def _get_containers(self, instance):
        return self._get_json("%(url)s/containers/json" % instance, params={"size": 1})

    def _get_container(self, instance, cid):
        return self._get_json("%s/containers/%s/json" % (instance["url"], cid))

    def _get_json(self, uri, params=None):
        if params:
            uri = "%s?%s" % (uri, urllib.urlencode(params))
        req = urllib2.Request(uri, None)
        request = urllib2.urlopen(req)
        response = request.read()
        return json.loads(response)


if __name__ == '__main__':
    check, instances = Docker.from_yaml('/home/vagrant/.datadog-agent/agent/conf.d/docker.yaml')
    for instance in instances:
        print "\nRunning the check against url: %s" % (instance['url'])
        check.check(instance)
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())
