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


class UnixHTTPConnection(httplib.HTTPConnection):
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
    """Collect metrics and events from Docker API and cgroups"""

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        # Initialize a HTTP opener with Unix socket support
        socket_timeout = int(init_config.get('socket_timeout', 0)) or DEFAULT_SOCKET_TIMEOUT
        UnixHTTPConnection.socket_timeout = socket_timeout
        self.url_opener = urllib2.build_opener(UnixSocketHandler())

        # Locate cgroups directories
        self._mountpoints = {}
        self._cgroup_filename_pattern = None
        docker_root = init_config.get('docker_root', '/')
        for metric in CGROUP_METRICS:
            self._mountpoints[metric["cgroup"]] = self._find_cgroup(metric["cgroup"], docker_root)

        self._last_event_collection_ts = defaultdict(lambda: None)

    def check(self, instance):
        # Report image metrics
        self._count_images(instance)

        # Get the list of containers and the index of their names
        containers, ids_to_names = self._get_and_count_containers(instance)

        # Report container metrics from cgroups
        self._report_containers_metrics(containers, instance)

        # Send events from Docker API
        if instance.get('collect_events', True):
            self._process_events(instance, ids_to_names)


    # Containers

    def _count_images(self, instance):
        # It's not an important metric, keep going if it fails
        try:
            tags = instance.get("tags", [])
            active_images = len(self._get_images(instance, get_all=False))
            all_images = len(self._get_images(instance, get_all=True))

            self.gauge("docker.images.available", active_images, tags=tags)
            self.gauge("docker.images.intermediate", (all_images - active_images), tags=tags)
        except Exception, e:
            self.warning("Failed to count Docker images. Exception: {0}".format(e))

    def _get_and_count_containers(self, instance):
        tags = instance.get("tags", [])
        with_size = instance.get('collect_container_size', False)

        service_check_name = 'docker.service_up'
        try:
            containers = self._get_containers(instance, with_size=with_size)
        except (socket.timeout, urllib2.URLError), e:
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=tags)
            raise Exception("Failed to collect the list of containers. Exception: {0}".format(e))
        self.service_check(service_check_name, AgentCheck.OK, tags=tags)

        container_count_by_image = defaultdict(int)
        for container in containers:
            container_count_by_image[container['Image']] += 1

        for image, count in container_count_by_image.iteritems():
            self.gauge("docker.containers.running", count, tags=(tags + ['image:%s' % image]))

        all_containers = self._get_containers(instance, get_all=True)
        stopped_containers_count = len(all_containers) - len(containers)
        self.gauge("docker.containers.stopped", stopped_containers_count, tags=tags)

        ids_to_names = {}
        for container in all_containers:
            ids_to_names[container['Id']] = container['Names'][0].lstrip("/")

        return containers, ids_to_names

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

    def _report_containers_metrics(self, containers, instance):
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
                        if key in stats:
                            getattr(self, metric_type)(dd_key, int(stats[key]), tags=container_tags)

    def _make_tag(self, key, value):
        return "%s:%s" % (key.lower(), value.strip())


    # Events

    def _process_events(self, instance, ids_to_names):
        try:
            api_events = self._get_events(instance)
            aggregated_events = self._pre_aggregate_events(api_events)
            events = self._format_events(aggregated_events, ids_to_names)
            self._report_events(events)
        except (socket.timeout, urllib2.URLError):
            self.warning('Timeout during socket connection. Events will be missing.')

    def _pre_aggregate_events(self, api_events):
        # Aggregate events, one per image. Put newer events first.
        events = defaultdict(list)
        for event in api_events:
            # Known bug: from may be missing
            if 'from' in event:
                events[event['from']].insert(0, event)

        return events

    def _format_events(self, aggregated_events, ids_to_names):
        events = []
        for image_name, event_group in aggregated_events.iteritems():
            max_timestamp = 0
            status = defaultdict(int)
            status_change = []
            for event in event_group:
                max_timestamp = max(max_timestamp, int(event['time']))
                status[event['status']] += 1
                container_name = event['id'][:12]
                if event['id'] in ids_to_names:
                    container_name = "%s %s" % (container_name, ids_to_names[event['id']])
                status_change.append([container_name, event['status']])

            status_text = ", ".join(["%d %s" % (count, st) for st, count in status.iteritems()])
            msg_title = "%s %s on %s" % (image_name, status_text, self.hostname)
            msg_body = ("%%%\n"
                "{image_name} {status} on {hostname}\n"
                "```\n{status_changes}\n```\n"
                "%%%").format(
                    image_name=image_name,
                    status=status_text,
                    hostname=self.hostname,
                    status_changes="\n".join(
                        ["%s \t%s" % (change[1].upper(), change[0]) for change in status_change])
            )
            events.append({
                'timestamp': max_timestamp,
                'host': self.hostname,
                'event_type': EVENT_TYPE,
                'msg_title': msg_title,
                'msg_text': msg_body,
                'source_type_name': EVENT_TYPE,
                'event_object': 'docker:%s' % image_name,
            })

        return events

    def _report_events(self, events):
        for ev in events:
            self.log.debug("Creating event: %s" % ev['msg_title'])
            self.event(ev)


    # Docker API

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
        self.log.debug("Connecting to Docker API at: %s" % uri)
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


    # Cgroups

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
        # This can't be initialized at startup because cgroups may not be mounted yet
        if not self._cgroup_filename_pattern:
            self._cgroup_filename_pattern = self._find_cgroup_filename_pattern()

        return self._cgroup_filename_pattern % (dict(
                    mountpoint=self._mountpoints[cgroup],
                    id=container_id,
                    file=filename,
                ))

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
        self.log.debug("Opening cgroup file: %s" % stat_file)
        try:
            fp = open(stat_file)
            return dict(map(lambda x: x.split(), fp.read().splitlines()))
        except IOError:
            # It is possible that the container got stopped between the API call and now
            self.log.info("Can't open %s. Metrics for this container are skipped." % stat_file)
        finally:
            if fp is not None:
                fp.close()
