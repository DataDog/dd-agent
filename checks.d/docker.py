import urllib2
import urllib
import httplib
import socket
import os
import re
import time
from urlparse import urlsplit
from util import json
try:
    from collections import defaultdict
except ImportError:
    from compat.defaultdict import defaultdict
from checks import AgentCheck

DEFAULT_MAX_CONTAINERS = 20
EVENT_TYPE = SOURCE_TYPE_NAME = 'docker'

LXC_METRICS = [
    {
        "cgroup": "memory",
        "file": "%s/%s/memory.stat",
        "metrics": {
            "active_anon": ("docker.mem.active_anon", "gauge"),
            "active_file": ("docker.mem.active_file", "gauge"),
            "cache": ("docker.mem.cache", "gauge"),
            "hierarchical_memory_limit": ("docker.mem.hierarchical_memory_limit", "gauge"),
            "hierarchical_memsw_limit": ("docker.mem.hierarchical_memsw_limit", "gauge"),
            "inactive_anon": ("docker.mem.inactive_anon", "gauge"),
            "inactive_file": ("docker.mem.inactive_file", "gauge"),
            "mapped_file": ("docker.mem.mapped_file", "gauge"),
            "pgfault": ("docker.mem.pgfault", "gauge"),
            "pgmajfault": ("docker.mem.pgmajfault", "gauge"),
            "pgpgin": ("docker.mem.pgpgin", "gauge"),
            "pgpgout": ("docker.mem.pgpgout", "gauge"),
            "rss": ("docker.mem.rss", "gauge"),
            "swap": ("docker.mem.swap", "gauge"),
            "unevictable": ("docker.mem.unevictable", "gauge"),
            "total_active_anon": ("docker.mem.total_active_anon", "gauge"),
            "total_active_file": ("docker.mem.total_active_file", "gauge"),
            "total_cache": ("docker.mem.total_cache", "gauge"),
            "total_inactive_anon": ("docker.mem.total_inactive_anon", "gauge"),
            "total_inactive_file": ("docker.mem.total_inactive_file", "gauge"),
            "total_mapped_file": ("docker.mem.total_mapped_file", "gauge"),
            "total_pgfault": ("docker.mem.total_pgfault", "gauge"),
            "total_pgmajfault": ("docker.mem.total_pgmajfault", "gauge"),
            "total_pgpgin": ("docker.mem.total_pgpgin", "gauge"),
            "total_pgpgout": ("docker.mem.total_pgpgout", "gauge"),
            "total_rss": ("docker.mem.total_rss", "gauge"),
            "total_swap": ("docker.mem.total_swap", "gauge"),
            "total_unevictable": ("docker.mem.total_unevictable", "gauge"),
        }
    },
    {
        "cgroup": "cpuacct",
        "file": "%s/%s/cpuacct.stat",
        "metrics": {
            "user": ("docker.cpu.user", "rate"),
            "system": ("docker.cpu.system", "rate"),
        },
    },
]

DOCKER_METRICS = {
    "SizeRw": ("docker.disk.size", "gauge"),
}

DOCKER_TAGS = [
    "Command",
    "Image",
]

SOCKET_TIMEOUT = 5

class UnixHTTPConnection(httplib.HTTPConnection, object):
    """Class used in conjuction with UnixSocketHandler to make urllib2
    compatible with Unix sockets."""
    def __init__(self, unix_socket):
        self._unix_socket = unix_socket

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._unix_socket)
        sock.settimeout(SOCKET_TIMEOUT)
        self.sock = sock

    def __call__(self, *args, **kwargs):
        httplib.HTTPConnection.__init__(self, *args, **kwargs)
        return self


class UnixSocketHandler(urllib2.AbstractHTTPHandler):
    """Class that makes Unix sockets work with urllib2 without any additional
    dependencies."""
    def unix_open(self, req):
        full_path = "%s%s" % urlsplit(req.get_full_url())[1:3]
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
        self._mountpoints = {}
        self.cgroup_path_prefix = None # Depending on the version
        for metric in LXC_METRICS:
            self._mountpoints[metric["cgroup"]] = self._find_cgroup(metric["cgroup"])
        self._path_prefix = None
        self._last_event_collection_ts = defaultdict(lambda: None)
        self.url_opener = urllib2.build_opener(UnixSocketHandler())
        self.should_get_size = True

    @property
    def path_prefix(self):
        if self._path_prefix is None:
            metric = LXC_METRICS[0]
            mountpoint = self._mountpoints[metric["cgroup"]]
            stat_file_lxc = os.path.join(mountpoint, "lxc")
            stat_file_docker = os.path.join(mountpoint, "docker")

            if os.path.exists(stat_file_lxc):
                self._path_prefix = "lxc"
            elif os.path.exists(stat_file_docker):
                self._path_prefix = "docker"
            else:
                raise Exception("Cannot find Docker cgroup file. If you are using Docker 0.9 or 0.10, it is a known bug in Docker fixed in Docker 0.11")
        return self._path_prefix

    def check(self, instance):
        tags = instance.get("tags") or []

        try:
            self._process_events(self._get_events(instance))
        except socket.timeout:
            self.warning('Timeout during socket connection. Events will be missing.')

        if self.should_get_size:
            try:
                containers = self._get_containers(instance, with_size=True)
            except socket.timeout:
                # Probably because of: https://github.com/DataDog/dd-agent/issues/963
                # Then we should stop trying to get size info
                self.log.info('Cannot get container size because of API timeout. Turn size flag off.')
                self.should_get_size = False

        if not self.should_get_size:
            containers = self._get_containers(instance, with_size=False)

        if not containers:
            self.gauge("docker.containers.running", 0)
            raise Exception("No containers are running.")

        self.gauge("docker.containers.running", len(containers))

        max_containers = instance.get('max_containers', DEFAULT_MAX_CONTAINERS)

        if not instance.get("exclude") or not instance.get("include"):
            if len(containers) > max_containers:
                self.warning("Too many containers to collect. Please refine the containers to collect by editing the configuration file. Truncating to %s containers" % max_containers)
                containers = containers[:max_containers]

        collected_containers = 0
        for container in containers:
            container_tags = list(tags)
            for name in container["Names"]:
                container_tags.append(self._make_tag("name", name.lstrip("/")))
            for key in DOCKER_TAGS:
                container_tags.append(self._make_tag(key, container[key]))

            # Check if the container is included/excluded via its tags
            if not self._is_container_included(instance, container_tags):
                continue

            collected_containers += 1
            if collected_containers > max_containers:
                self.warning("Too many containers are matching the current configuration. Some containers will not be collected. Please refine your configuration")
                break

            for key, (dd_key, metric_type) in DOCKER_METRICS.items():
                if key in container:
                    getattr(self, metric_type)(dd_key, int(container[key]), tags=container_tags)
            for metric in LXC_METRICS:
                mountpoint = self._mountpoints[metric["cgroup"]]
                stat_file = os.path.join(mountpoint, metric["file"] % (self.path_prefix, container["Id"]))
                stats = self._parse_cgroup_file(stat_file)
                for key, (dd_key, metric_type) in metric["metrics"].items():
                    if key.startswith("total_") and not instance.get("collect_total"):
                        continue
                    if key in stats:
                        getattr(self, metric_type)(dd_key, int(stats[key]), tags=container_tags)

    def _process_events(self, events):
        for ev in events:
            self.log.debug("Creating event for %s" % ev)
            self.event({
                'timestamp': ev['time'],
                'host': self.hostname,
                'event_type': EVENT_TYPE,
                'msg_title': "%s %s on %s" % (ev['from'], ev['status'], self.hostname),
                'source_type_name': EVENT_TYPE,
                'event_object': ev['from'],
            })


    def _make_tag(self, key, value):
        return "%s:%s" % (key.lower(), value.strip())

    def _is_container_included(self, instance, tags):
        def _is_tag_included(tag):
            for exclude_rule in instance.get("exclude") or []:
                if re.match(exclude_rule, tag):
                    for include_rule in instance.get("include") or []:
                        if re.match(include_rule, tag):
                            return True
                    return False
            return True
        for tag in tags:
            if _is_tag_included(tag):
                return True
        return False

    def _get_containers(self, instance, with_size=True):
        """Gets the list of running containers in Docker."""
        return self._get_json("%(url)s/containers/json" % instance, params={'size': with_size})

    def _get_events(self, instance):
        """Get the list of events """
        now = int(time.time())
        result = self._get_json("%s/events" % instance["url"], params={
                "until": now,
                "since": self._last_event_collection_ts[instance["url"]] or now - 60,
            }, multi=True)
        self._last_event_collection_ts[instance["url"]] = now
        if type(result) == dict:
            result = [result]
        return result

    def _get_json(self, uri, params=None, multi=False):
        """Utility method to get and parse JSON streams."""
        if params:
            uri = "%s?%s" % (uri, urllib.urlencode(params))
        self.log.debug("Connecting to: %s" % uri)
        req = urllib2.Request(uri, None)
        try:
            request = self.url_opener.open(req)
        except urllib2.URLError, e:
            if "Errno 13" in str(e):
                raise Exception("Unable to connect to socket. dd-agent user must be part of the 'docker' group")
            raise
        response = request.read()
        if multi and "}{" in response: # docker api sometimes returns juxtaposed json dictionaries
            response = "[{0}]".format(response.replace("}{", "},{"))

        if not response:
            return []

        return json.loads(response)

    def _find_cgroup(self, hierarchy):
        """Finds the mount point for a specified cgroup hierarchy. Works with
        old style and new style mounts."""
        try:
            fp = open("/proc/mounts")
            mounts = map(lambda x: x.split(), fp.read().splitlines())
        finally:
            fp.close()
        cgroup_mounts = filter(lambda x: x[2] == "cgroup", mounts)
        # Old cgroup style
        if len(cgroup_mounts) == 1:
            return cgroup_mounts[0][1]
        for _, mountpoint, _, opts, _, _ in cgroup_mounts:
            if hierarchy in opts:
                return mountpoint

    def _parse_cgroup_file(self, file_):
        """Parses a cgroup pseudo file for key/values."""
        fp = None
        try:
            self.log.debug("Opening file: %s" % file_)
            try:
                fp = open(file_)
            except IOError:
                raise IOError("Can't open %s. If you are using Docker 0.9 or 0.10, it is a known bug in Docker fixed in Docker 0.11" % file_)
            return dict(map(lambda x: x.split(), fp.read().splitlines()))

        finally:
            if fp is not None:
                fp.close()
