# stdlib
import urllib2
import urllib
import httplib
import socket
import os
import re
import time
from urlparse import urlsplit
from util import json
from collections import defaultdict

# project
from checks import AgentCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'docker'

CGROUP_METRICS = [
    {
        "cgroup": "memory",
        "file": "memory.stat",
        "metrics": {
            "active_anon": ("docker.mem.active_anon", "gauge"),
            "active_file": ("docker.mem.active_file", "gauge"),
            "cache": ("docker.mem.cache", "gauge"),
            "hierarchical_memory_limit": ("docker.mem.hierarchical_memory_limit", "gauge"),
            "hierarchical_memsw_limit": ("docker.mem.hierarchical_memsw_limit", "gauge"),
            "inactive_anon": ("docker.mem.inactive_anon", "gauge"),
            "inactive_file": ("docker.mem.inactive_file", "gauge"),
            "mapped_file": ("docker.mem.mapped_file", "gauge"),
            "pgfault": ("docker.mem.pgfault", "rate"),
            "pgmajfault": ("docker.mem.pgmajfault", "rate"),
            "pgpgin": ("docker.mem.pgpgin", "rate"),
            "pgpgout": ("docker.mem.pgpgout", "rate"),
            "rss": ("docker.mem.rss", "gauge"),
            "swap": ("docker.mem.swap", "gauge"),
            "unevictable": ("docker.mem.unevictable", "gauge"),
            "total_active_anon": ("docker.mem.total_active_anon", "gauge"),
            "total_active_file": ("docker.mem.total_active_file", "gauge"),
            "total_cache": ("docker.mem.total_cache", "gauge"),
            "total_inactive_anon": ("docker.mem.total_inactive_anon", "gauge"),
            "total_inactive_file": ("docker.mem.total_inactive_file", "gauge"),
            "total_mapped_file": ("docker.mem.total_mapped_file", "gauge"),
            "total_pgfault": ("docker.mem.total_pgfault", "rate"),
            "total_pgmajfault": ("docker.mem.total_pgmajfault", "rate"),
            "total_pgpgin": ("docker.mem.total_pgpgin", "rate"),
            "total_pgpgout": ("docker.mem.total_pgpgout", "rate"),
            "total_rss": ("docker.mem.total_rss", "gauge"),
            "total_swap": ("docker.mem.total_swap", "gauge"),
            "total_unevictable": ("docker.mem.total_unevictable", "gauge"),
        }
    },
    {
        "cgroup": "cpuacct",
        "file": "cpuacct.stat",
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

DEFAULT_SOCKET_TIMEOUT = 5


class UnixHTTPConnection(httplib.HTTPConnection, object):
    """Class used in conjuction with UnixSocketHandler to make urllib2
    compatible with Unix sockets."""

    socket_timeout = DEFAULT_SOCKET_TIMEOUT

    def __init__(self, unix_socket):
        self._unix_socket = unix_socket

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self._unix_socket)
        sock.settimeout(self.socket_timeout)
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
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self._mountpoints = {}
        docker_root = init_config.get('docker_root', '/')
        socket_timeout = int(init_config.get('socket_timeout', 0)) or DEFAULT_SOCKET_TIMEOUT
        UnixHTTPConnection.socket_timeout = socket_timeout
        for metric in CGROUP_METRICS:
            self._mountpoints[metric["cgroup"]] = self._find_cgroup(metric["cgroup"], docker_root)
        self._last_event_collection_ts = defaultdict(lambda: None)
        self.url_opener = urllib2.build_opener(UnixSocketHandler())
        self._cgroup_filename_pattern = None

    def _find_cgroup_filename_pattern(self):
        if self._mountpoints:
            # We try with different cgroups so that it works even if only one is properly working
            for mountpoint in self._mountpoints.values():
                stat_file_path_lxc = os.path.join(mountpoint, "lxc")
                stat_file_path_docker = os.path.join(mountpoint, "docker")
                stat_file_path_coreos = os.path.join(mountpoint, "system.slice")

                if os.path.exists(stat_file_path_lxc):
                    return os.path.join('%(mountpoint)s/lxc/%(id)s/%(file)s')
                elif os.path.exists(stat_file_path_docker):
                    return os.path.join('%(mountpoint)s/docker/%(id)s/%(file)s')
                elif os.path.exists(stat_file_path_coreos):
                    return os.path.join('%(mountpoint)s/system.slice/docker-%(id)s.scope/%(file)s')

        raise Exception("Cannot find Docker cgroup directory. Be sure your system is supported.")

    def _get_cgroup_file(self, cgroup, container_id, filename):
        # This can't be initialized at startup because cgroups may not be mounted
        if not self._cgroup_filename_pattern:
            self._cgroup_filename_pattern = self._find_cgroup_filename_pattern()

        return self._cgroup_filename_pattern % (dict(
                    mountpoint=self._mountpoints[cgroup],
                    id=container_id,
                    file=filename,
                ))

    def check(self, instance):
        if instance.get('collect_events', True):
            try:
                self._process_events(self._get_events(instance))
            except (socket.timeout, urllib2.URLError):
                self.warning('Timeout during socket connection. Events will be missing.')

        self._count_images(instance)
        containers = self._get_and_count_containers(instance)

        for container in containers:
            container_tags = instance.get("tags", [])
            for name in container["Names"]:
                container_tags.append(self._make_tag("name", name.lstrip("/")))
            for key in DOCKER_TAGS:
                container_tags.append(self._make_tag(key, container[key]))

            # Check if the container is included/excluded via its tags
            if not self._is_container_included(instance, container_tags):
                continue

            for key, (dd_key, metric_type) in DOCKER_METRICS.items():
                if key in container:
                    getattr(self, metric_type)(dd_key, int(container[key]), tags=container_tags)
            for cgroup in CGROUP_METRICS:
                stat_file = self._get_cgroup_file(cgroup["cgroup"], container['Id'], cgroup['file'])
                stats = self._parse_cgroup_file(stat_file)
                if stats:
                    for key, (dd_key, metric_type) in cgroup['metrics'].items():
                        if key.startswith('total_') and not instance.get('collect_total'):
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

    def _count_images(self, instance):
        tags = instance.get("tags", [])
        active_images = len(self._get_images(instance, get_all=False))
        all_images = len(self._get_images(instance, get_all=True))

        self.gauge("docker.images.available", active_images, tags=tags)
        self.gauge("docker.images.intermediate", (all_images - active_images), tags=tags)

    def _get_and_count_containers(self, instance):
        tags = instance.get("tags", [])

        with_size = instance.get('collect_container_size', False)
        try:
            containers = self._get_containers(instance, with_size=with_size)
        except (socket.timeout, urllib2.URLError), e:
            raise Exception("Container collection timed out. Exception: {0}".format(e))

        stopped_containers_count = len(self._get_containers(instance, get_all=True)) - len(containers)
        self.gauge("docker.containers.running", len(containers), tags=tags)
        self.gauge("docker.containers.stopped", stopped_containers_count, tags=tags)

        return containers


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


    def _get_containers(self, instance, with_size=False, get_all=False):
        """Gets the list of running/all containers in Docker."""
        return self._get_json("%(url)s/containers/json" % instance, params={'size': with_size, 'all': get_all})

    def _get_images(self, instance, with_size=True, get_all=False):
        """Gets the list of images in Docker."""
        return self._get_json("%(url)s/images/json" % instance, params={'all': get_all})

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

        service_check_name = 'docker.service_up'
        service_check_tags = ['host:%s' % self.hostname]

        try:
            request = self.url_opener.open(req)
        except urllib2.URLError, e:
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=service_check_tags)
            if "Errno 13" in str(e):
                raise Exception("Unable to connect to socket. dd-agent user must be part of the 'docker' group")
            raise

        self.service_check(service_check_name, AgentCheck.OK, tags=service_check_tags)

        response = request.read()
        if multi and "}{" in response: # docker api sometimes returns juxtaposed json dictionaries
            response = "[{0}]".format(response.replace("}{", "},{"))

        if not response:
            return []

        return json.loads(response)

    def _find_cgroup(self, hierarchy, docker_root):
        """Finds the mount point for a specified cgroup hierarchy. Works with
        old style and new style mounts."""
        try:
            fp = open(os.path.join(docker_root, "/proc/mounts"))
            mounts = map(lambda x: x.split(), fp.read().splitlines())
        finally:
            fp.close()
        cgroup_mounts = filter(lambda x: x[2] == "cgroup", mounts)
        if len(cgroup_mounts) == 0:
            raise Exception("Can't find mounted cgroups. If you run the Agent inside a container,"
                " please refer to the documentation.")
        # Old cgroup style
        if len(cgroup_mounts) == 1:
            return os.path.join(docker_root, cgroup_mounts[0][1])
        for _, mountpoint, _, opts, _, _ in cgroup_mounts:
            if hierarchy in opts:
                return os.path.join(docker_root, mountpoint)

    def _parse_cgroup_file(self, stat_file):
        """Parses a cgroup pseudo file for key/values."""
        fp = None
        self.log.debug("Opening file: %s" % stat_file)
        try:
            fp = open(stat_file)
            return dict(map(lambda x: x.split(), fp.read().splitlines()))
        except IOError:
            # Can be because the container got stopped
            self.log.info("Can't open %s. Metrics for this container are skipped." % stat_file)
        finally:
            if fp is not None:
                fp.close()
