import urllib2
import urllib
import httplib
import socket
import os
from urlparse import urlsplit, urljoin
from util import json, headers
from checks import AgentCheck


USER_HZ = 1000

LXC_METRICS = [
    {
        "cgroup": "memory",
        "file": "lxc/{0}/memory.stat",
        "metrics": {
            "active_anon": ("docker.memory.active_anon", "gauge"),
            "active_file": ("docker.memory.active_file", "gauge"),
            "cache": ("docker.memory.cache", "gauge"),
            "hierarchical_memory_limit": ("docker.memory.hierarchical_memory_limit", "gauge"),
            "hierarchical_memsw_limit": ("docker.memory.hierarchical_memsw_limit", "gauge"),
            "inactive_anon": ("docker.memory.inactive_anon", "gauge"),
            "inactive_file": ("docker.memory.inactive_file", "gauge"),
            "mapped_file": ("docker.memory.mapped_file", "gauge"),
            "pgfault": ("docker.memory.pgfault", "gauge"),
            "pgmajfault": ("docker.memory.pgmajfault", "gauge"),
            "pgpgin": ("docker.memory.pgpgin", "gauge"),
            "pgpgout": ("docker.memory.pgpgout", "gauge"),
            "rss": ("docker.memory.rss", "gauge"),
            "swap": ("docker.memory.swap", "gauge"),
            "unevictable": ("docker.memory.unevictable", "gauge"),
            "total_active_anon": ("docker.memory.total_active_anon", "gauge"),
            "total_active_file": ("docker.memory.total_active_file", "gauge"),
            "total_cache": ("docker.memory.total_cache", "gauge"),
            "total_inactive_anon": ("docker.memory.total_inactive_anon", "gauge"),
            "total_inactive_file": ("docker.memory.total_inactive_file", "gauge"),
            "total_mapped_file": ("docker.memory.total_mapped_file", "gauge"),
            "total_pgfault": ("docker.memory.total_pgfault", "gauge"),
            "total_pgmajfault": ("docker.memory.total_pgmajfault", "gauge"),
            "total_pgpgin": ("docker.memory.total_pgpgin", "gauge"),
            "total_pgpgout": ("docker.memory.total_pgpgout", "gauge"),
            "total_rss": ("docker.memory.total_rss", "gauge"),
            "total_swap": ("docker.memory.total_swap", "gauge"),
            "total_unevictable": ("docker.memory.total_unevictable", "gauge"),
        }
    },
    {
        "cgroup": "cpuacct",
        "file": "lxc/{0}/cpuacct.stat",
        "metrics": {
            "user": ("docker.cpu.user", "gauge"),
            "system": ("docker.cpu.system", "gauge"),
        },
    },
]

DOCKER_METRICS = {
    "SizeRw": ("docker.disk.size_in_bytes", "gauge"),
}

DOCKER_TAGS = [
    "ID",
    "Name",
    "Created",
    "Driver",
    "Path",
]

DOCKER_CONFIG_TAGS = [
    "Hostname",
    "Image"
]



class UnixHTTPConnection(httplib.HTTPConnection, object):
    """Class used in conjuction with UnixSocketHandler to make urllib2
    compatible with Unix sockets."""
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
    """Class that makes Unix sockets work with urllib2 without any additional
    dependencies."""
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
        self._mounpoints = {}
        for metric in LXC_METRICS:
            self._mounpoints[metric["cgroup"]] = self._find_cgroup(metric["cgroup"])

    def check(self, instance):
        tags = instance.get("tags") or []

        for container in self._get_containers(instance):
            container_details = self._get_container(instance, container["Id"])
            container_tags = list(tags)
            for key in DOCKER_TAGS:
                container_tags.append("%s:%s" % (key.lower(), container_details[key]))
            for key, (dd_key, metric_type) in DOCKER_METRICS.items():
                if key in container:
                    getattr(self, metric_type)(dd_key, int(container[key]), tags=container_tags)
            for metric in LXC_METRICS:
                mountpoint = self._mounpoints[metric["cgroup"]]
                stat_file = os.path.join(mountpoint, metric["file"].format(container["Id"]))
                stats = self._parse_cgroup_file(stat_file)
                for key, (dd_key, metric_type) in metric["metrics"].items():
                    if key in stats:
                        getattr(self, metric_type)(dd_key, int(stats[key]), tags=container_tags)

    def _get_containers(self, instance):
        """Gets the list of running containers in Docker."""
        return self._get_json("%(url)s/containers/json" % instance, params={"size": 1})

    def _get_container(self, instance, cid):
        """Get container information from Docker, gived a container Id."""
        return self._get_json("%s/containers/%s/json" % (instance["url"], cid))

    def _get_json(self, uri, params=None):
        """Utility method to get and parse JSON streams."""
        if params:
            uri = "%s?%s" % (uri, urllib.urlencode(params))
        req = urllib2.Request(uri, None)
        request = urllib2.urlopen(req)
        response = request.read()
        return json.loads(response)

    def _find_cgroup(self, hierarchy):
        """Finds the mount point for a specified cgroup hierarchy. Works with
        old style and new style mounts."""
        with open("/proc/mounts") as fp:
            mounts = map(lambda x: x.split(), fp.read().splitlines())
        cgroup_mounts = filter(lambda x: x[2] == "cgroup", mounts)
        # Old cgroup style
        if len(cgroup_mounts) == 1:
            return cgroup_mounts[0][1]
        for _, mountpoint, _, opts, _, _ in cgroup_mounts:
            if hierarchy in opts:
                return mountpoint

    def _parse_cgroup_file(self, file_):
        """Parses a cgroup pseudo file for key/values."""
        with open(file_) as fp:
            return dict(map(lambda x: x.split(), fp.read().splitlines()))


if __name__ == "__main__":
    from pprint import pprint
    check, instances = Docker.from_yaml("/home/vagrant/.datadog-agent/agent/conf.d/docker.yaml")
    for instance in instances:
        print "\nRunning the check against url: %s" % (instance["url"])
        check.check(instance)
        if check.has_events():
            print "Events: %s" % (check.get_events())
        print "Metrics:"
        pprint(check.get_metrics())
