# stdlib
import logging

# project
from tests.checks.common import AgentCheckTest
from utils.dockerutil import get_client, set_docker_settings, get_docker_settings, reset_docker_settings, \
    image_tag_extractor, container_name_extractor

# 3rd party
from nose.plugins.attrib import attr

log = logging.getLogger('tests')

CONTAINERS_TO_RUN = [
    "nginx",
    "redis:latest",

]

POD_NAME_LABEL = "io.kubernetes.pod.name"


@attr(requires='docker_daemon')
class TestCheckDockerDaemon(AgentCheckTest):
    CHECK_NAME = 'docker_daemon'

    def setUp(self):
        self.docker_client = get_client()
        for c in CONTAINERS_TO_RUN:
            images = [i["RepoTags"][0] for i in self.docker_client.images(c.split(":")[0]) if i["RepoTags"][0].startswith(c)]
            if len(images) == 0:
                for line in self.docker_client.pull(c, stream=True):
                    print line

        self.containers = []
        for c in CONTAINERS_TO_RUN:
            name = "test-new-{0}".format(c.replace(":", "-"))
            host_config = None
            labels = None
            if c == "nginx":
                host_config = {"Memory": 137438953472}
                labels = {"label1": "nginx", "foo": "bar"}

            cont = self.docker_client.create_container(
                c, detach=True, name=name, host_config=host_config, labels=labels)
            self.containers.append(cont)

        for c in self.containers:
            log.info("Starting container: {0}".format(c))
            self.docker_client.start(c)

    def tearDown(self):
        for c in self.containers:
            log.info("Stopping container: {0}".format(c))
            self.docker_client.remove_container(c, force=True)

    def test_basic_config_single(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1', 'image_tag:1.9', 'image_tag:1.9.6', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1', 'image_tag:1.9', 'image_tag:1.9.6', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.mem.cache', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.limit', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.in_use', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
        ]

        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_image_size": True,
                "collect_images_stats": True,
            },
            ],
        }

        self.run_check(config, force_reload=True)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

    def test_basic_config_twice(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.cpu.system', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.cpu.system', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.cpu.user', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.cpu.user', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.io.read_bytes', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.io.read_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.io.write_bytes', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.io.write_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.cache', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.limit' ,['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.in_use' ,['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.net.bytes_rcvd', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.net.bytes_rcvd', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.net.bytes_sent', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.net.bytes_sent', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx'])

        ]

        custom_tags = ["extra_tag", "env:testing"]
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "tags": custom_tags,
                "collect_images_stats": True,
            },
            ],
        }

        self.run_check_twice(config, force_reload=True)
        for mname, tags in expected_metrics:
            expected_tags = list(custom_tags)
            if tags is not None:
                expected_tags += tags
            self.assertMetric(mname, tags=expected_tags, count=1, at_least=1)

    def test_exclude_filter(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.cpu.system', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.cpu.user', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1', 'image_tag:latest', 'image_tag:1.9', 'image_tag:1.9.6']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1', 'image_tag:latest', 'image_tag:1.9', 'image_tag:1.9.6']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.io.read_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.io.write_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.net.bytes_rcvd', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.net.bytes_sent', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest'])
        ]
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "exclude": ["docker_image:nginx"],
                "collect_images_stats": True,
                "collect_image_size": True,
            },
            ],
        }

        self.run_check_twice(config, force_reload=True)

        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

        perf_metrics = [
            "docker.cpu.system",
            "docker.cpu.user",
            "docker.io.read_bytes",
            "docker.io.write_bytes",
            "docker.mem.cache",
            "docker.mem.rss",
            "docker.net.bytes_rcvd",
            "docker.net.bytes_sent"
        ]

        nginx_tags = ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']
        for mname in perf_metrics:
            self.assertMetric(mname, tags=nginx_tags, count=0)

    def test_include_filter(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.cpu.system', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.cpu.user', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1', 'image_tag:latest', 'image_tag:1.9', 'image_tag:1.9.6']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1', 'image_tag:latest', 'image_tag:1.9', 'image_tag:1.9.6']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.io.read_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.io.write_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.net.bytes_rcvd', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.net.bytes_sent', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest'])
        ]
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "include": ["image_name:redis"],
                "exclude": [".*"],
                "collect_images_stats": True,
                "collect_image_size": True,
            },
            ],
        }

        self.run_check_twice(config, force_reload=True)

        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

        perf_metrics = [
            "docker.cpu.system",
            "docker.cpu.user",
            "docker.io.read_bytes",
            "docker.io.write_bytes",
            "docker.mem.cache",
            "docker.mem.rss",
            "docker.net.bytes_rcvd",
            "docker.net.bytes_sent"
        ]

        nginx_tags = ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']
        for m in perf_metrics:
            self.assertMetric(mname, tags=nginx_tags, count=0)

    def test_tags_options(self):
        expected_metrics = [
            ('docker.containers.running', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.containers.running', ['container_command:/entrypoint.sh redis-server']),
            ('docker.containers.stopped', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.containers.stopped', ['container_command:/entrypoint.sh redis-server']),
            ('docker.cpu.system', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.cpu.system', ['container_command:/entrypoint.sh redis-server']),
            ('docker.cpu.user', ['container_command:/entrypoint.sh redis-server']),
            ('docker.cpu.user', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1', 'image_tag:1.9.6', 'image_tag:1.9', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1', 'image_tag:1.9.6', 'image_tag:1.9', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.io.read_bytes', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.io.read_bytes', ['container_command:/entrypoint.sh redis-server']),
            ('docker.io.write_bytes', ['container_command:/entrypoint.sh redis-server']),
            ('docker.io.write_bytes', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.mem.cache', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.mem.cache', ['container_command:/entrypoint.sh redis-server']),
            ('docker.mem.rss', ['container_command:/entrypoint.sh redis-server']),
            ('docker.mem.rss', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.mem.limit', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.mem.in_use', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.net.bytes_rcvd', ['container_command:/entrypoint.sh redis-server']),
            ('docker.net.bytes_rcvd', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.net.bytes_sent', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.net.bytes_sent', ['container_command:/entrypoint.sh redis-server'])
        ]
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "performance_tags": ["container_command"],
                "container_tags": ["container_command"],
                "collect_images_stats": True,
                "collect_image_size": True,
            },
            ],
        }

        self.run_check_twice(config, force_reload=True)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

    def test_set_docker_settings(self):
        self.assertEqual(get_docker_settings()["version"], "auto")
        cur_loc = __file__
        init_config = {
            "api_version": "foobar",
            "timeout": "42",
            "tls_client_cert": cur_loc,
            "tls_client_key": cur_loc,
            "tls_cacert": cur_loc,
            "tls": True

        }

        instance = {
            "url": "https://foo.bar:42",
        }

        set_docker_settings(init_config, instance)
        client = get_client()
        self.assertEqual(client.verify, cur_loc)
        self.assertEqual(client.cert, (cur_loc, cur_loc))
        reset_docker_settings()

    def test_labels_collection(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx', 'image_name:nginx', 'label1:nginx']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:nginx', 'image_name:nginx', 'label1:nginx']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1', 'image_tag:1.9', 'image_tag:1.9.6', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1', 'image_tag:1.9', 'image_tag:1.9.6', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.mem.cache', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx', 'label1:nginx']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx', 'label1:nginx']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.limit', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx', 'label1:nginx']),
            ('docker.mem.in_use', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx', 'label1:nginx']),
        ]

        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_labels_as_tags": ["label1"],
                "collect_image_size": True,
                "collect_images_stats": True,
            },
            ],
        }

        self.run_check(config, force_reload=True)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

    def test_histogram(self):

        metric_suffix = ["count", "avg", "median", "max", "95percentile"]

        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1', 'image_tag:1.9', 'image_tag:1.9.6', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1', 'image_tag:1.9', 'image_tag:1.9.6', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
        ]

        histo_metrics = [
            ('docker.mem.cache', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.cache', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.rss', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.limit', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.in_use', ['docker_image:nginx', 'image_name:nginx']),
        ]

        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_image_size": True,
                "collect_images_stats": True,
                "use_histogram": True,
            },
            ],
        }

        self.run_check(config, force_reload=True)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

        for mname, tags in histo_metrics:
            for suffix in metric_suffix:
                self.assertMetric(mname + "." + suffix, tags=tags, at_least=1)

    def test_events(self):
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_images_stats": True,
            },
            ],
        }

        self.run_check(config, force_reload=True)
        self.assertEqual(len(self.events), 2)

    def test_container_size(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.containers.stopped', ['docker_image:nginx', 'image_name:nginx']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1', 'image_tag:1.9', 'image_tag:1.9.6', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.1']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7', 'image_tag:1.7.12']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.0']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.7.11']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1', 'image_tag:1.9', 'image_tag:1.9.6', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.2']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:1.9.3']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.mem.cache', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.limit', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ('docker.mem.in_use', ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            # Container size metrics
            ("docker.container.size_rootfs", ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),
            ("docker.container.size_rootfs", ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ("docker.container.size_rw", ['container_name:test-new-nginx', 'docker_image:nginx', 'image_name:nginx']),

        ]

        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_container_size": True,
                "collect_image_size": True,
                "collect_images_stats": True,
            },
            ],
        }

        self.run_check(config, force_reload=True)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

    def test_image_tags_extraction(self):
        entities = [
            # ({'Image': image_name}, [expected_image_name, expected_image_tag])
            ({'Image': 'nginx:latest'}, [['nginx'], ['latest']]),
            ({'Image': 'localhost/nginx:latest'}, [['localhost/nginx'], ['latest']]),
            ({'Image': 'localhost:5000/nginx:latest'}, [['localhost:5000/nginx'], ['latest']]),
            ({'RepoTags': ['redis:latest']}, [['redis'], ['latest']]),
            ({'RepoTags': ['localhost/redis:latest']}, [['localhost/redis'], ['latest']]),
            ({'RepoTags': ['localhost:5000/redis:latest']}, [['localhost:5000/redis'], ['latest']]),
            ({'RepoTags': ['localhost:5000/redis:latest', 'localhost:5000/redis:v1.1']}, [['localhost:5000/redis'], ['latest', 'v1.1']]),
        ]
        for entity in entities:
            self.assertEqual(sorted(image_tag_extractor(entity[0], 0)), sorted(entity[1][0]))
            self.assertEqual(sorted(image_tag_extractor(entity[0], 1)), sorted(entity[1][1]))

    def test_container_name_extraction(self):
        containers = [
            ({'Id': ['deadbeef']}, ['deadbeef']),
            ({'Names': ['/redis'], 'Id': ['deadbeef']}, ['redis']),
            ({'Names': ['/mongo', '/redis/mongo'], 'Id': ['deadbeef']}, ['mongo']),
            ({'Names': ['/redis/mongo', '/mongo'], 'Id': ['deadbeef']}, ['mongo']),
        ]
        for co in containers:
            self.assertEqual(container_name_extractor(co[0]), co[1])
