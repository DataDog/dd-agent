# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os
import re
import requests
import socket
import urllib2
from collections import defaultdict, Counter, deque
from math import ceil

# project
from checks import AgentCheck
from config import _is_affirmative
from utils.dockerutil import DockerUtil, MountException
from utils.kubeutil import KubeUtil
from utils.platform import Platform
from utils.service_discovery.sd_backend import get_sd_backend


EVENT_TYPE = 'docker'
SERVICE_CHECK_NAME = 'docker.service_up'
SIZE_REFRESH_RATE = 5  # Collect container sizes every 5 iterations of the check
MAX_CGROUP_LISTING_RETRIES = 3
CONTAINER_ID_RE = re.compile('[0-9a-f]{64}')

GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate
HISTORATE = AgentCheck.generate_historate_func(["container_name"])
HISTO = AgentCheck.generate_histogram_func(["container_name"])
FUNC_MAP = {
    GAUGE: {True: HISTO, False: GAUGE},
    RATE: {True: HISTORATE, False: RATE}
}

UNIT_MAP = {
    'kb': 1000,
    'mb': 1000000,
    'gb': 1000000000,
    'tb': 1000000000000
}

CGROUP_METRICS = [
    {
        "cgroup": "memory",
        "file": "memory.stat",
        "metrics": {
            "cache": ("docker.mem.cache", GAUGE),
            "rss": ("docker.mem.rss", GAUGE),
            "swap": ("docker.mem.swap", GAUGE),
        },
        "to_compute": {
            # We only get these metrics if they are properly set, i.e. they are a "reasonable" value
            "docker.mem.limit": (["hierarchical_memory_limit"], lambda x: float(x) if float(x) < 2 ** 60 else None, GAUGE),
            "docker.mem.sw_limit": (["hierarchical_memsw_limit"], lambda x: float(x) if float(x) < 2 ** 60 else None, GAUGE),
            "docker.mem.in_use": (["rss", "hierarchical_memory_limit"], lambda x,y: float(x)/float(y) if float(y) < 2 ** 60 else None, GAUGE),
            "docker.mem.sw_in_use": (["swap", "rss", "hierarchical_memsw_limit"], lambda x,y,z: float(x + y)/float(z) if float(z) < 2 ** 60 else None, GAUGE)

        }
    },
    {
        "cgroup": "cpuacct",
        "file": "cpuacct.stat",
        "metrics": {
            "user": ("docker.cpu.user", RATE),
            "system": ("docker.cpu.system", RATE),
        },
    },
    {
        "cgroup": "blkio",
        "file": 'blkio.throttle.io_service_bytes',
        "metrics": {
            "io_read": ("docker.io.read_bytes", RATE),
            "io_write": ("docker.io.write_bytes", RATE),
        },
    },
]

DEFAULT_CONTAINER_TAGS = [
    "docker_image",
    "image_name",
    "image_tag",
]

DEFAULT_PERFORMANCE_TAGS = [
    "container_name",
    "docker_image",
    "image_name",
    "image_tag",
]

DEFAULT_IMAGE_TAGS = [
    'image_name',
    'image_tag'
]


TAG_EXTRACTORS = {
    "docker_image": lambda c: [c["Image"]],
    "image_name": lambda c: DockerUtil.image_tag_extractor(c, 0),
    "image_tag": lambda c: DockerUtil.image_tag_extractor(c, 1),
    "container_command": lambda c: [c["Command"]],
    "container_name": DockerUtil.container_name_extractor,
    "container_id": lambda c: [c["Id"]],
}

CONTAINER = "container"
PERFORMANCE = "performance"
FILTERED = "filtered"
IMAGE = "image"


def get_filters(include, exclude):
    # The reasoning is to check exclude first, so we can skip if there is no exclude
    if not exclude:
        return

    filtered_tag_names = []
    exclude_patterns = []
    include_patterns = []

    # Compile regex
    for rule in exclude:
        exclude_patterns.append(re.compile(rule))
        filtered_tag_names.append(rule.split(':')[0])
    for rule in include:
        include_patterns.append(re.compile(rule))
        filtered_tag_names.append(rule.split(':')[0])

    return set(exclude_patterns), set(include_patterns), set(filtered_tag_names)


class DockerDaemon(AgentCheck):
    """Collect metrics and events from Docker API and cgroups."""

    def __init__(self, name, init_config, agentConfig, instances=None):
        if instances is not None and len(instances) > 1:
            raise Exception("Docker check only supports one configured instance.")
        AgentCheck.__init__(self, name, init_config,
                            agentConfig, instances=instances)

        self.init_success = False
        self.init()
        self._service_discovery = agentConfig.get('service_discovery') and \
            agentConfig.get('service_discovery_backend') == 'docker'

    def is_k8s(self):
        return 'KUBERNETES_PORT' in os.environ

    def init(self):
        try:
            instance = self.instances[0]

            # We configure the check with the right cgroup settings for this host
            # Just needs to be done once
            self.docker_util = DockerUtil()
            self.docker_client = self.docker_util.client
            if self.is_k8s():
                self.kubeutil = KubeUtil()
            self._mountpoints = self.docker_util.get_mountpoints(CGROUP_METRICS)
            self.cgroup_listing_retries = 0
            self._latest_size_query = 0
            self._filtered_containers = set()
            self._disable_net_metrics = False

            # Set tagging options
            self.custom_tags = instance.get("tags", [])
            self.collect_labels_as_tags = instance.get("collect_labels_as_tags", [])
            self.kube_labels = {}

            self.use_histogram = _is_affirmative(instance.get('use_histogram', False))
            performance_tags = instance.get("performance_tags", DEFAULT_PERFORMANCE_TAGS)

            self.tag_names = {
                CONTAINER: instance.get("container_tags", DEFAULT_CONTAINER_TAGS),
                PERFORMANCE: performance_tags,
                IMAGE: instance.get('image_tags', DEFAULT_IMAGE_TAGS)
            }

            # Set filtering settings
            if not instance.get("exclude"):
                self._filtering_enabled = False
                if instance.get("include"):
                    self.log.warning("You must specify an exclude section to enable filtering")
            else:
                self._filtering_enabled = True
                include = instance.get("include", [])
                exclude = instance.get("exclude", [])
                self._exclude_patterns, self._include_patterns, _filtered_tag_names = get_filters(include, exclude)
                self.tag_names[FILTERED] = _filtered_tag_names

            # Other options
            self.collect_image_stats = _is_affirmative(instance.get('collect_images_stats', False))
            self.collect_container_size = _is_affirmative(instance.get('collect_container_size', False))
            self.collect_events = _is_affirmative(instance.get('collect_events', True))
            self.collect_image_size = _is_affirmative(instance.get('collect_image_size', False))
            self.collect_disk_stats = _is_affirmative(instance.get('collect_disk_stats', False))
            self.collect_ecs_tags = _is_affirmative(instance.get('ecs_tags', True)) and Platform.is_ecs_instance()

            self.ecs_tags = {}

        except Exception as e:
            self.log.critical(e)
            self.warning("Initialization failed. Will retry at next iteration")
        else:
            self.init_success = True

    def check(self, instance):
        """Run the Docker check for one instance."""
        if not self.init_success:
            # Initialization can fail if cgroups are not ready. So we retry if needed
            # https://github.com/DataDog/dd-agent/issues/1896
            self.init()
            if not self.init_success:
                # Initialization failed, will try later
                return

        # Report image metrics
        if self.collect_image_stats:
            self._count_and_weigh_images()

        if self.collect_ecs_tags:
            self.refresh_ecs_tags()

        if self.is_k8s():
            try:
                self.kube_labels = self.kubeutil.get_kube_labels()
            except Exception as e:
                self.log.warning('Could not retrieve kubernetes labels: %s' % str(e))
                self.kube_labels = {}

        # Get the list of containers and the index of their names
        containers_by_id = self._get_and_count_containers()
        containers_by_id = self._crawl_container_pids(containers_by_id)

        # Send events from Docker API
        if self.collect_events or self._service_discovery:
            self._process_events(containers_by_id)

        # Report performance container metrics (cpu, mem, net, io)
        self._report_performance_metrics(containers_by_id)

        if self.collect_container_size:
            self._report_container_size(containers_by_id)

        # Collect disk stats from Docker info command
        if self.collect_disk_stats:
            self._report_disk_stats()

    def _count_and_weigh_images(self):
        try:
            tags = self._get_tags()
            active_images = self.docker_client.images(all=False)
            active_images_len = len(active_images)
            all_images_len = len(self.docker_client.images(quiet=True, all=True))
            self.gauge("docker.images.available", active_images_len, tags=tags)
            self.gauge("docker.images.intermediate", (all_images_len - active_images_len), tags=tags)

            if self.collect_image_size:
                self._report_image_size(active_images)

        except Exception as e:
            # It's not an important metric, keep going if it fails
            self.warning("Failed to count Docker images. Exception: {0}".format(e))

    def _get_and_count_containers(self):
        """List all the containers from the API, filter and count them."""

        # Querying the size of containers is slow, we don't do it at each run
        must_query_size = self.collect_container_size and self._latest_size_query == 0
        self._latest_size_query = (self._latest_size_query + 1) % SIZE_REFRESH_RATE

        running_containers_count = Counter()
        all_containers_count = Counter()

        try:
            containers = self.docker_client.containers(all=True, size=must_query_size)
        except Exception as e:
            message = "Unable to list Docker containers: {0}".format(e)
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               message=message)
            raise Exception(message)

        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK)

        # Filter containers according to the exclude/include rules
        self._filter_containers(containers)

        containers_by_id = {}

        for container in containers:
            container_name = DockerUtil.container_name_extractor(container)[0]

            container_status_tags = self._get_tags(container, CONTAINER)

            all_containers_count[tuple(sorted(container_status_tags))] += 1
            if self._is_container_running(container):
                running_containers_count[tuple(sorted(container_status_tags))] += 1

            # Check if the container is included/excluded via its tags
            if self._is_container_excluded(container):
                self.log.debug("Container {0} is excluded".format(container_name))
                continue

            containers_by_id[container['Id']] = container

        for tags, count in running_containers_count.iteritems():
            self.gauge("docker.containers.running", count, tags=list(tags))

        for tags, count in all_containers_count.iteritems():
            stopped_count = count - running_containers_count[tags]
            self.gauge("docker.containers.stopped", stopped_count, tags=list(tags))

        return containers_by_id

    def _is_container_running(self, container):
        """Tell if a container is running, according to its status.

        There is no "nice" API field to figure it out. We just look at the "Status" field, knowing how it is generated.
        See: https://github.com/docker/docker/blob/v1.6.2/daemon/state.go#L35
        """
        return container["Status"].startswith("Up") or container["Status"].startswith("Restarting")

    def _get_tags(self, entity=None, tag_type=None):
        """Generate the tags for a given entity (container or image) according to a list of tag names."""
        # Start with custom tags
        tags = list(self.custom_tags)

        # Collect pod names as tags on kubernetes
        if self.is_k8s() and KubeUtil.POD_NAME_LABEL not in self.collect_labels_as_tags:
            self.collect_labels_as_tags.append(KubeUtil.POD_NAME_LABEL)

        if entity is not None:
            pod_name = None

            # Get labels as tags
            labels = entity.get("Labels")
            if labels is not None:
                for k in self.collect_labels_as_tags:
                    if k in labels:
                        v = labels[k]
                        if k == KubeUtil.POD_NAME_LABEL and self.is_k8s():
                            pod_name = v
                            k = "pod_name"
                            if "-" in pod_name:
                                replication_controller = "-".join(pod_name.split("-")[:-1])
                                if "/" in replication_controller: # k8s <= 1.1
                                    namespace, replication_controller = replication_controller.split("/", 1)

                                elif KubeUtil.NAMESPACE_LABEL in labels: # k8s >= 1.2
                                    namespace = labels[KubeUtil.NAMESPACE_LABEL]
                                    pod_name = "{0}/{1}".format(namespace, pod_name)

                                tags.append("kube_namespace:%s" % namespace)
                                tags.append("kube_replication_controller:%s" % replication_controller)
                                tags.append("pod_name:%s" % pod_name)

                        elif not v:
                            tags.append(k)

                        else:
                            tags.append("%s:%s" % (k,v))

                    if k == KubeUtil.POD_NAME_LABEL and self.is_k8s() and k not in labels:
                        tags.append("pod_name:no_pod")

            # Get entity specific tags
            if tag_type is not None:
                tag_names = self.tag_names[tag_type]
                for tag_name in tag_names:
                    tag_value = self._extract_tag_value(entity, tag_name)
                    if tag_value is not None:
                        for t in tag_value:
                            tags.append('%s:%s' % (tag_name, str(t).strip()))

            # Add ECS tags
            if self.collect_ecs_tags:
                entity_id = entity.get("Id")
                if entity_id in self.ecs_tags:
                    ecs_tags = self.ecs_tags[entity_id]
                    tags.extend(ecs_tags)

            # Add kube labels
            if self.is_k8s():
                kube_tags = self.kube_labels.get(pod_name)
                if kube_tags:
                    tags.extend(list(kube_tags))

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
            entity["_tag_values"][tag_name] = TAG_EXTRACTORS[tag_name](entity)

        return entity["_tag_values"][tag_name]

    def refresh_ecs_tags(self):
        ecs_config = self.docker_client.inspect_container('ecs-agent')
        ip = ecs_config.get('NetworkSettings', {}).get('IPAddress')
        ports = ecs_config.get('NetworkSettings', {}).get('Ports')
        port = ports.keys()[0].split('/')[0] if ports else None
        ecs_tags = {}
        if ip and port:
            tasks = requests.get('http://%s:%s/v1/tasks' % (ip, port)).json()
            for task in tasks.get('Tasks', []):
                for container in task.get('Containers', []):
                    tags = ['task_name:%s' % task['Family'], 'task_version:%s' % task['Version']]
                    ecs_tags[container['DockerId']] = tags

        self.ecs_tags = ecs_tags

    def _filter_containers(self, containers):
        if not self._filtering_enabled:
            return

        self._filtered_containers = set()
        for container in containers:
            container_tags = self._get_tags(container, FILTERED)
            if self._are_tags_filtered(container_tags):
                container_name = DockerUtil.container_name_extractor(container)[0]
                self._filtered_containers.add(container_name)
                self.log.debug("Container {0} is filtered".format(container_name))

    def _are_tags_filtered(self, tags):
        if self._tags_match_patterns(tags, self._exclude_patterns):
            if self._tags_match_patterns(tags, self._include_patterns):
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
        container_name = DockerUtil.container_name_extractor(container)[0]
        return container_name in self._filtered_containers

    def _report_container_size(self, containers_by_id):
        for container in containers_by_id.itervalues():
            if self._is_container_excluded(container):
                continue

            tags = self._get_tags(container, PERFORMANCE)
            m_func = FUNC_MAP[GAUGE][self.use_histogram]
            if "SizeRw" in container:

                m_func(self, 'docker.container.size_rw', container['SizeRw'],
                       tags=tags)
            if "SizeRootFs" in container:
                m_func(
                    self, 'docker.container.size_rootfs', container['SizeRootFs'],
                    tags=tags)

    def _report_image_size(self, images):
        for image in images:
            tags = self._get_tags(image, IMAGE)
            if 'VirtualSize' in image:
                self.gauge('docker.image.virtual_size', image['VirtualSize'], tags=tags)
            if 'Size' in image:
                self.gauge('docker.image.size', image['Size'], tags=tags)

    # Performance metrics

    def _report_performance_metrics(self, containers_by_id):

        containers_without_proc_root = []
        for container in containers_by_id.itervalues():
            if self._is_container_excluded(container) or not self._is_container_running(container):
                continue

            tags = self._get_tags(container, PERFORMANCE)
            self._report_cgroup_metrics(container, tags)
            if "_proc_root" not in container:
                containers_without_proc_root.append(DockerUtil.container_name_extractor(container)[0])
                continue
            self._report_net_metrics(container, tags)

        if containers_without_proc_root:
            message = "Couldn't find pid directory for containers: {0}. They'll be missing network metrics".format(
                ", ".join(containers_without_proc_root))
            if not self.is_k8s():
                self.warning(message)
            else:
                # On kubernetes, this is kind of expected. Network metrics will be collected by the kubernetes integration anyway
                self.log.debug(message)

    def _report_cgroup_metrics(self, container, tags):
        try:
            for cgroup in CGROUP_METRICS:
                stat_file = self._get_cgroup_file(cgroup["cgroup"], container['Id'], cgroup['file'])
                stats = self._parse_cgroup_file(stat_file)
                if stats:
                    for key, (dd_key, metric_func) in cgroup['metrics'].iteritems():
                        metric_func = FUNC_MAP[metric_func][self.use_histogram]
                        if key in stats:
                            metric_func(self, dd_key, int(stats[key]), tags=tags)

                    # Computed metrics
                    for mname, (key_list, fct, metric_func) in cgroup.get('to_compute', {}).iteritems():
                        values = [stats[key] for key in key_list if key in stats]
                        if len(values) != len(key_list):
                            self.log.debug("Couldn't compute {0}, some keys were missing.".format(mname))
                            continue
                        value = fct(*values)
                        metric_func = FUNC_MAP[metric_func][self.use_histogram]
                        if value is not None:
                            metric_func(self, mname, value, tags=tags)

        except MountException as ex:
            if self.cgroup_listing_retries > MAX_CGROUP_LISTING_RETRIES:
                raise ex
            else:
                self.warning("Couldn't find the cgroup files. Skipping the CGROUP_METRICS for now."
                             "Will retry {0} times before failing.".format(MAX_CGROUP_LISTING_RETRIES - self.cgroup_listing_retries))
                self.cgroup_listing_retries += 1
        else:
            self.cgroup_listing_retries = 0

    def _report_net_metrics(self, container, tags):
        """Find container network metrics by looking at /proc/$PID/net/dev of the container process."""
        if self._disable_net_metrics:
            self.log.debug("Network metrics are disabled. Skipping")
            return

        proc_net_file = os.path.join(container['_proc_root'], 'net/dev')
        try:
            with open(proc_net_file, 'r') as fp:
                lines = fp.readlines()
                """Two first lines are headers:
                Inter-|   Receive                                                |  Transmit
                 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
                """
                for l in lines[2:]:
                    cols = l.split(':', 1)
                    interface_name = str(cols[0]).strip()
                    if interface_name == 'eth0':
                        x = cols[1].split()
                        m_func = FUNC_MAP[RATE][self.use_histogram]
                        m_func(self, "docker.net.bytes_rcvd", long(x[0]), tags)
                        m_func(self, "docker.net.bytes_sent", long(x[8]), tags)
                        break
        except Exception as e:
            # It is possible that the container got stopped between the API call and now
            self.warning("Failed to report IO metrics from file {0}. Exception: {1}".format(proc_net_file, e))

    def _process_events(self, containers_by_id):
        if self.collect_events is False:
            # Crawl events for service discovery only
            self._get_events()
            return
        try:
            api_events = self._get_events()
            aggregated_events = self._pre_aggregate_events(api_events, containers_by_id)
            events = self._format_events(aggregated_events, containers_by_id)
        except (socket.timeout, urllib2.URLError):
            self.warning('Timeout when collecting events. Events will be missing.')
            return
        except Exception as e:
            self.warning("Unexpected exception when collecting events: {0}. "
                         "Events will be missing".format(e))
            return

        for ev in events:
            self.log.debug("Creating event: %s" % ev['msg_title'])
            self.event(ev)

    def _get_events(self):
        """Get the list of events."""
        events, should_reload_conf = self.docker_util.get_events()
        if should_reload_conf and self._service_discovery:
            get_sd_backend(self.agentConfig).reload_check_configs = True
        return events

    def _pre_aggregate_events(self, api_events, containers_by_id):
        # Aggregate events, one per image. Put newer events first.
        events = defaultdict(deque)
        for event in api_events:
            # Skip events related to filtered containers
            container = containers_by_id.get(event.get('id'))
            if container is not None and self._is_container_excluded(container):
                self.log.debug("Excluded event: container {0} status changed to {1}".format(
                    event['id'], event['status']))
                continue
            # from may be missing (for network events for example)
            if 'from' in event:
                events[event['from']].appendleft(event)
        return events

    def _format_events(self, aggregated_events, containers_by_id):
        events = []
        for image_name, event_group in aggregated_events.iteritems():
            max_timestamp = 0
            status = defaultdict(int)
            status_change = []
            container_tags = set()
            for event in event_group:
                max_timestamp = max(max_timestamp, int(event['time']))
                status[event['status']] += 1
                container_name = event['id'][:11]
                if event['id'] in containers_by_id:
                    cont = containers_by_id[event['id']]
                    container_name = DockerUtil.container_name_extractor(cont)[0]
                    container_tags.update(self._get_tags(cont, PERFORMANCE))
                    container_tags.add('container_name:%s' % container_name)

                status_change.append([container_name, event['status']])

            status_text = ", ".join(["%d %s" % (count, st) for st, count in status.iteritems()])
            msg_title = "%s %s on %s" % (image_name, status_text, self.hostname)
            msg_body = (
                "%%%\n"
                "{image_name} {status} on {hostname}\n"
                "```\n{status_changes}\n```\n"
                "%%%"
            ).format(
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
                'tags': list(container_tags)
            })

        return events

    def _report_disk_stats(self):
        """Report metrics about the volume space usage"""
        stats = {
            'docker.data.used': None,
            'docker.data.total': None,
            'docker.data.free': None,
            'docker.metadata.used': None,
            'docker.metadata.total': None,
            'docker.metadata.free': None
            # these two are calculated by _calc_percent_disk_stats
            # 'docker.data.percent': None,
            # 'docker.metadata.percent': None
        }
        info = self.docker_client.info()
        driver_status = info.get('DriverStatus', [])
        if not driver_status:
            self.log.warning('Disk metrics collection is enabled but docker info did not'
                             ' report any. Your storage driver might not support them, skipping.')
            return
        for metric in driver_status:
            # only consider metrics about disk space
            if len(metric) == 2 and 'Space' in metric[0]:
                # identify Data and Metadata metrics
                mtype = 'data'
                if 'Metadata' in metric[0]:
                    mtype = 'metadata'

                if 'Used' in metric[0]:
                    stats['docker.{0}.used'.format(mtype)] = metric[1]
                elif 'Space Total' in metric[0]:
                    stats['docker.{0}.total'.format(mtype)] = metric[1]
                elif 'Space Available' in metric[0]:
                    stats['docker.{0}.free'.format(mtype)] = metric[1]
        stats = self._format_disk_metrics(stats)
        stats.update(self._calc_percent_disk_stats(stats))
        tags = self._get_tags()
        for name, val in stats.iteritems():
            if val is not None:
                self.gauge(name, val, tags)

    def _format_disk_metrics(self, metrics):
        """Cast the disk stats to float and convert them to bytes"""
        for name, raw_val in metrics.iteritems():
            if raw_val:
                val, unit = raw_val.split(' ')
                # by default some are uppercased others lowercased. That's error prone.
                unit = unit.lower()
                try:
                    val = int(float(val) * UNIT_MAP[unit])
                    metrics[name] = val
                except KeyError:
                    self.log.error('Unrecognized unit %s for disk metric %s. Dropping it.' % (unit, name))
                    metrics[name] = None
        return metrics

    def _calc_percent_disk_stats(self, stats):
        """Calculate a percentage of used disk space for data and metadata"""
        mtypes = ['data', 'metadata']
        percs = {}
        for mtype in mtypes:
            used = stats.get('docker.{0}.used'.format(mtype))
            total = stats.get('docker.{0}.total'.format(mtype))
            free = stats.get('docker.{0}.free'.format(mtype))
            if used and total and free and ceil(total) < free + used:
                self.log.error('used, free, and total disk metrics may be wrong, '
                               'unable to calculate percentage.')
                return {}
            try:
                if isinstance(used, int):
                    percs['docker.{0}.percent'.format(mtype)] = round(100 * float(used) / float(total), 2)
                elif isinstance(free, int):
                    percs['docker.{0}.percent'.format(mtype)] = round(100 * (1.0 - (float(free) / float(total))), 2)
            except ZeroDivisionError:
                self.log.error('docker.{0}.total is 0, calculating docker.{1}.percent'
                               ' is not possible.'.format(mtype, mtype))
        return percs

    # Cgroups

    def _get_cgroup_file(self, cgroup, container_id, filename):
        """Find a specific cgroup file, containing metrics to extract."""
        params = {
            "mountpoint": self._mountpoints[cgroup],
            "id": container_id,
            "file": filename,
        }

        return DockerUtil.find_cgroup_filename_pattern(self._mountpoints, container_id) % (params)

    def _parse_cgroup_file(self, stat_file):
        """Parse a cgroup pseudo file for key/values."""
        self.log.debug("Opening cgroup file: %s" % stat_file)
        try:
            with open(stat_file, 'r') as fp:
                if 'blkio' in stat_file:
                    return self._parse_blkio_metrics(fp.read().splitlines())
                else:
                    return dict(map(lambda x: x.split(' ', 1), fp.read().splitlines()))
        except IOError:
            # It is possible that the container got stopped between the API call and now
            self.log.info("Can't open %s. Metrics for this container are skipped." % stat_file)

    def _parse_blkio_metrics(self, stats):
        """Parse the blkio metrics."""
        metrics = {
            'io_read': 0,
            'io_write': 0,
        }
        for line in stats:
            if 'Read' in line:
                metrics['io_read'] += int(line.split()[2])
            if 'Write' in line:
                metrics['io_write'] += int(line.split()[2])
        return metrics

    # proc files
    def _crawl_container_pids(self, container_dict):
        """Crawl `/proc` to find container PIDs and add them to `containers_by_id`."""
        proc_path = os.path.join(self.docker_util._docker_root, 'proc')
        pid_dirs = [_dir for _dir in os.listdir(proc_path) if _dir.isdigit()]

        if len(pid_dirs) == 0:
            self.warning("Unable to find any pid directory in {0}. "
                "If you are running the agent in a container, make sure to "
                'share the volume properly: "/proc:/host/proc:ro". '
                "See https://github.com/DataDog/docker-dd-agent/blob/master/README.md for more information. "
                "Network metrics will be missing".format(proc_path))
            self._disable_net_metrics = True
            return container_dict

        self._disable_net_metrics = False

        for folder in pid_dirs:

            try:
                path = os.path.join(proc_path, folder, 'cgroup')
                with open(path, 'r') as f:
                    content = [line.strip().split(':') for line in f.readlines()]
            except IOError as e:
                #  Issue #2074
                self.log.debug("Cannot read %s, "
                               "process likely raced to finish : %s" %
                               (path, str(e)))
            except Exception as e:
                self.warning("Cannot read %s : %s" % (path, str(e)))
                continue

            try:
                for line in content:
                    if line[1] in ('cpu,cpuacct', 'cpuacct,cpu', 'cpuacct') and 'docker' in line[2]:
                        cpuacct = line[2]
                        break
                else:
                    continue

                matches = re.findall(CONTAINER_ID_RE, cpuacct)
                if matches:
                    container_id = matches[-1]
                    if container_id not in container_dict:
                        self.log.debug("Container %s not in container_dict, it's likely excluded", container_id)
                        continue
                    container_dict[container_id]['_pid'] = folder
                    container_dict[container_id]['_proc_root'] = os.path.join(proc_path, folder)
            except Exception as e:
                self.warning("Cannot parse %s content: %s" % (path, str(e)))
                continue
        return container_dict
