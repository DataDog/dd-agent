# stdlib
import os
import re
# import time
# from collections import defaultdict

# project
from checks import AgentCheck
from config import _is_affirmative

# 3rd party
from docker import Client

EVENT_TYPE = 'docker'

CGROUP_METRICS = [
    {
        "cgroup": "memory",
        "file": "memory.stat",
        "metrics": {
            "cache": ("docker.mem.cache", "gauge"),
            "rss": ("docker.mem.rss", "gauge"),
            "swap": ("docker.mem.swap", "gauge"),
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
    {
        "cgroup": "blkio",
        "file": 'blkio.throttle.io_service_bytes',
        "metrics": {
            "io_read": ("docker.io.read_bytes", "monotonic_count"),
            "io_write": ("docker.io.write_bytes", "monotonic_count"),
        },
    },
]

TAG_EXTRACTORS = {
    "docker_image": lambda c: c["Image"],
    "image_name": lambda c: c["Image"].split(':', 1)[0],
    "image_tag": lambda c: c["Image"].split(':', 1)[1],
    "container_command": lambda c: c["Command"],
    "container_name": lambda c: c['Names'][0].lstrip("/") if c["Names"] else c['Id'][:11],
}


"""WIP for a new docker check

TODO:
 - All the "TODO" in the code
 - Support a global "extra_tags" configuration, adding tags to all the metrics/events
 - Figure out the need to have "per-container" custom tags (often requested)
 - Figure out what to do with extra cgroups/proc available metrics
 - Support alternative root / - /rootfs to make it work with docker-dd-agent
 - Write tests
 - Test on all the platforms
"""


class MountException(Exception):
    pass


class DockerDaemon(AgentCheck):
    """Collect metrics and events from Docker API and cgroups"""

    DEFAULT_SOCKET_TIMEOUT = 5

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        self._cgroup_filename_pattern = None
        self._mountpoints = {}
        self.docker_root = init_config.get('docker_root', '/')
        self.cgroup_listing_retries = 0

    def check(self, instance):
        """Run the Docker check for one instance."""

        # Connect to the Docker daemon
        self._connect_api(instance)

        # Report image metrics
        if _is_affirmative(instance.get('collect_images_stats', True)):
            self._count_images(instance)

        # Get the list of containers and the index of their names
        containers_by_id = self._get_and_count_containers(instance)

        # Report performance container metrics (cpu, mem, net, io)
        self._report_performance_metrics(instance, containers_by_id)

        # TODO: report container sizes (and image sizes?)
        # if _is_affirmative(instance.get('collect_container_size', True)):
        #     self._report_container_size(instance, containers_by_id)

        # TODO: bring events back
        # Send events from Docker API
        # if _is_affirmative(instance.get('collect_events', True)):
        #     self._process_events(instance, containers_by_id)

    def _connect_api(self, instance):
        base_url = instance.get('url')
        if not base_url:
            raise Exception('Invalid configuration, missing "url" parameter')
        tls = _is_affirmative(instance.get('tls', False))
        # TODO: figure out an API version to stick to
        # TODO: configurable timeout
        self.client = Client(base_url=base_url, tls=tls, timeout=self.DEFAULT_SOCKET_TIMEOUT)

    # Containers

    def _count_images(self, instance):
        try:
            active_images = len(self.client.images(quiet=True, all=False))
            all_images = len(self.client.images(quiet=True, all=True))

            self.gauge("docker.images.available", active_images)
            self.gauge("docker.images.intermediate", (all_images - active_images))
        except Exception, e:
            self.warning("Failed to count Docker images. Exception: {0}".format(e))

    def _get_and_count_containers(self, instance):
        """List all the containers from the API, filter and count them"""

        service_check_name = 'docker.service_up'
        try:
            containers = self.client.containers(all=True)
        except Exception, e:
            self.service_check(service_check_name, AgentCheck.CRITICAL,
                               message="Unable to list Docker containers: {0}".format(e))
            raise Exception("Failed to collect the list of containers. Exception: {0}".format(e))
        else:
            self.service_check(service_check_name, AgentCheck.OK)

        # Filter containers according to the exclude/include rules
        self._filter_containers(instance, containers)

        containers_by_id = {}
        for container in containers:
            tag_names = instance.get("container_tags", ["image_name"])
            container_tags = self._get_tags(container, tag_names)

            # Check if the container is included/excluded via its tags
            if self._is_container_excluded(container):
                continue

            if self._is_container_running(container):
                self.set("docker.containers.running", container['Id'], tags=container_tags)
            else:
                self.set("docker.containers.stopped", container['Id'], tags=container_tags)

            containers_by_id[container['Id']] = container

        return containers_by_id

    def _is_container_running(self, container):
        """Tells if a container is running, according to its status

        There is no "nice" API field to figure it out. We just look at the "Status" field, knowing how it is generated.
        See: https://github.com/docker/docker/blob/v1.6.2/daemon/state.go#L35
        """
        return container["Status"].startswith("Up") or container["Status"].startswith("Restarting")

    def _get_tags(self, entity, tag_names):
        """Generate the tags for a given entity (container or image) according to a list of tag names"""
        tags = []
        for tag_name in tag_names:
            tags.append('%s:%s' % (tag_name, self._extract_tag_value(entity, tag_name)))

        return tags

    def _extract_tag_value(self, entity, tag_name):
        """Extra tag information from the API result (containers or images).

        Cache extracted tags inside the entity object.
        """
        if tag_name not in TAG_EXTRACTORS:
            self.warning("{0} isn't a supported tag".format(tag_name))
            return
        # Check for already extracted tags
        if "_tag_values" not in entity:
            entity["_tag_values"] = {}
        if tag_name not in entity["_tag_values"]:
            entity["_tag_values"][tag_name] = TAG_EXTRACTORS[tag_name](entity).strip()

        return entity["_tag_values"][tag_name]

    def _filter_containers(self, instance, containers):
        # The reasoning is to check exclude first, so we can skip if there is no exclude
        if not instance.get("exclude"):
            instance["filtering_enabled"] = False
            return

        filtered_tag_names = set()
        instance["exclude_patterns"] = []
        instance["include_patterns"] = []
        # Compile regex
        for rule in instance.get("exclude", []):
            instance["exclude_patterns"].append(re.compile(rule))
            filtered_tag_names.append(rule.split(':')[0])
        for rule in instance.get("include", []):
            instance["include_patterns"].append(re.compile(rule))
            filtered_tag_names.append(rule.split(':')[0])

        for container in containers:
            container['_is_filtered'] = self._are_tags_filtered(self._get_tags(container, filtered_tag_names))
            # Log.debug it

    def _are_tags_filtered(self, instance, tags):
        if self._tags_match_patterns(tags, instance.get("exclude_patterns")):
            if self._tags_match_patterns(tags, instance.get("include_patterns")):
                return False
            return True
        return False

    def _tags_match_patterns(self, tags, filters):
        for rule in filters:
            for tag in tags:
                if re.match(rule, tag):
                    return True
        return False

    def _is_container_excluded(self, container):
        """Check if a container is excluded according to the filter rules.

        Requires _filter_containers to run first.
        """
        return container.get('_is_filtered', False)

    # def _report_container_size(self, instance, containers_by_id):
    #     #TODO: report container size


    # Performance metrics

    def _report_performance_metrics(self, instance, containers_by_id):

        for container in containers_by_id.itervalues():
            if self._is_container_excluded(container) or not self._is_container_running(container):
                continue

            tag_names = instance.get("performance_tags", ["image_name", "container_name"])
            container_tags = self._get_tags(container, tag_names)

            self._report_cgroup_metrics(container, container_tags)
            self._report_net_metrics(container, container_tags)

    def _report_cgroup_metrics(self, container, tags):
        try:
            for cgroup in CGROUP_METRICS:
                stat_file = self._get_cgroup_file(cgroup["cgroup"], container['Id'], cgroup['file'])
                stats = self._parse_cgroup_file(stat_file)
                if stats:
                    for key, (dd_key, metric_type) in cgroup['metrics'].iteritems():
                        if key in stats:
                            getattr(self, metric_type)(dd_key, int(stats[key]), tags=tags)
        except MountException as ex:
            if self.cgroup_listing_retries > 3:
                raise ex
            else:
                self.warning("Couldn't find the cgroup files. Skipping the CGROUP_METRICS for now."
                             "Will retry a few times before failing.")
                self.cgroup_listing_retries += 1

    def _report_net_metrics(self, container, tags):
        """Find container network metrics by looking at /proc/$PID/net/dev of the container process"""
        proc_root = self._get_proc_root(container)
        proc_net_file = os.path.join(proc_root, 'net/dev')

        fp = None
        try:
            fp = open(proc_net_file)
            lines = fp.read().splitlines()

            for l in lines[2:]:
                cols = l.split(':', 1)
                interface_name = cols[0].strip()
                if interface_name == 'eth0':
                    x = cols[1].split()
                    self.rate("docker.net.bytes_rcvd", long(x[0]), tags)
                    self.rate("docker.net.bytes_sent", long(x[8]), tags)
                    break
        except Exception, e:
            # It is possible that the container got stopped between the API call and now
            self.warning("Failed to report IO metrics from file {0}. Exception: {1}".format(proc_net_file, e))
        finally:
            if fp is not None:
                fp.close()

    # Events

    # def _process_events(self, instance, ids_to_names, skipped_container_ids):
    #     try:
    #         api_events = self._get_events(instance)
    #         aggregated_events = self._pre_aggregate_events(api_events, skipped_container_ids)
    #         events = self._format_events(aggregated_events, ids_to_names)
    #         self._report_events(events)
    #     except (socket.timeout, urllib2.URLError):
    #         self.warning('Timeout during socket connection. Events will be missing.')

    # def _pre_aggregate_events(self, api_events, skipped_container_ids):
    #     # Aggregate events, one per image. Put newer events first.
    #     events = defaultdict(list)
    #     for event in api_events:
    #         # Skip events related to filtered containers
    #         if event['id'] in skipped_container_ids:
    #             self.log.debug("Excluded event: container {0} status changed to {1}".format(
    #                 event['id'], event['status']))
    #             continue
    #         # Known bug: from may be missing
    #         if 'from' in event:
    #             events[event['from']].insert(0, event)

    #     return events

    # def _format_events(self, aggregated_events, ids_to_names):
    #     events = []
    #     for image_name, event_group in aggregated_events.iteritems():
    #         max_timestamp = 0
    #         status = defaultdict(int)
    #         status_change = []
    #         for event in event_group:
    #             max_timestamp = max(max_timestamp, int(event['time']))
    #             status[event['status']] += 1
    #             container_name = event['id'][:12]
    #             if event['id'] in ids_to_names:
    #                 container_name = "%s %s" % (container_name, ids_to_names[event['id']])
    #             status_change.append([container_name, event['status']])

    #         status_text = ", ".join(["%d %s" % (count, st) for st, count in status.iteritems()])
    #         msg_title = "%s %s on %s" % (image_name, status_text, self.hostname)
    #         msg_body = (
    #             "%%%\n"
    #             "{image_name} {status} on {hostname}\n"
    #             "```\n{status_changes}\n```\n"
    #             "%%%"
    #         ).format(
    #             image_name=image_name,
    #             status=status_text,
    #             hostname=self.hostname,
    #             status_changes="\n".join(
    #                 ["%s \t%s" % (change[1].upper(), change[0]) for change in status_change])
    #         )
    #         events.append({
    #             'timestamp': max_timestamp,
    #             'host': self.hostname,
    #             'event_type': EVENT_TYPE,
    #             'msg_title': msg_title,
    #             'msg_text': msg_body,
    #             'source_type_name': EVENT_TYPE,
    #             'event_object': 'docker:%s' % image_name,
    #         })

    #     return events

    # def _report_events(self, events):
    #     for ev in events:
    #         self.log.debug("Creating event: %s" % ev['msg_title'])
    #         self.event(ev)

    # def _get_events(self, instance):
    #     """Get the list of events """
    #     now = int(time.time())
    #     result = self._get_json(
    #         "%s/events" % instance["url"],
    #         params={
    #             "until": now,
    #             "since": self._last_event_collection_ts[instance["url"]] or now - 60,
    #         }, multi=True)
    #     self._last_event_collection_ts[instance["url"]] = now
    #     if type(result) == dict:
    #         result = [result]
    #     return result

    # Cgroups

    def _get_cgroup_file(self, cgroup, container_id, filename):
        """Find a specific cgroup file, containing metrics to extract"""
        if not self._cgroup_filename_pattern:
            self._cgroup_filename_pattern = self._find_cgroup_filename_pattern()

        return self._cgroup_filename_pattern % (dict(
            mountpoint=self._mountpoints[cgroup],
            id=container_id,
            file=filename,
        ))

    def _find_cgroup_filename_pattern(self):
        if not self._mountpoints:
            for metric in CGROUP_METRICS:
                self._mountpoints[metric["cgroup"]] = self._find_cgroup(metric["cgroup"])
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

        raise MountException("Cannot find Docker cgroup directory. Be sure your system is supported.")

    def _find_cgroup(self, hierarchy):
        """Finds the mount point for a specified cgroup hierarchy. Works with
        old style and new style mounts."""
        fp = None
        try:
            fp = open(os.path.join(self.docker_root, "/proc/mounts"))
            mounts = map(lambda x: x.split(), fp.read().splitlines())
        finally:
            if fp is not None:
                fp.close()
        cgroup_mounts = filter(lambda x: x[2] == "cgroup", mounts)
        if len(cgroup_mounts) == 0:
            raise Exception(
                "Can't find mounted cgroups. If you run the Agent inside a container,"
                " please refer to the documentation.")
        # Old cgroup style
        if len(cgroup_mounts) == 1:
            return os.path.join(self.docker_root, cgroup_mounts[0][1])
        for _, mountpoint, _, opts, _, _ in cgroup_mounts:
            if hierarchy in opts:
                return os.path.join(self.docker_root, mountpoint)

    def _parse_cgroup_file(self, stat_file):
        """Parses a cgroup pseudo file for key/values."""
        fp = None
        self.log.debug("Opening cgroup file: %s" % stat_file)
        try:
            fp = open(stat_file)
            if 'blkio' in stat_file:
                return self._parse_blkio_metrics(fp.read().splitlines())
            else:
                return dict(map(lambda x: x.split(' ', 1), fp.read().splitlines()))
        except IOError:
            # It is possible that the container got stopped between the API call and now
            self.log.info("Can't open %s. Metrics for this container are skipped." % stat_file)
        finally:
            if fp is not None:
                fp.close()

    def _parse_blkio_metrics(self, stats):
        """Parse the blkio metrics."""
        metrics = {
            'io_read': 0,
            'io_write': 0,
        }
        for line in stats:
            if 'Read' in line:
                metrics['io_read'] += int(line[2])
            if 'Write' in line:
                metrics['io_write'] += int(line[2])
        return metrics

    # proc files

    def _get_proc_root(self, container):
        """Find PID then proc directory of a container

        Does it with docker inspect. That's for the POC, should use something smarter (such as walking /proc and
        looking at /proc/$PID/cgroup to make it matches to a container.
        """
        if not container.get('_pid'):
            inspection = self.client.inspect_container(container["Id"])
            pid = inspection.get("State", {}).get("Pid")
            # TODO: catch exceptions
            container["_pid"] = pid

        return '/proc/%s/' % container["_pid"]
