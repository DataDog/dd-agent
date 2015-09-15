import docker

from tests.checks.common import AgentCheckTest


class TestDockerDaemon(AgentCheckTest):
    CHECK_NAME = 'docker_daemon'

    CONTAINER_METRICS = [
        'docker.mem.cache',
        'docker.mem.cache',
        'docker.containers.running',
        'docker.containers.running',
        'docker.mem.rss',
        'docker.mem.rss',
    ]

    IMAGE_METRICS = [
        'docker.image.virtual_size',
        'docker.image.virtual_size',
        'docker.image.size',
        'docker.image.size',
        'docker.images.available',
        'docker.images.intermediate',
    ]

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.metrics_config = {
            'collect_container_size': True,
            'collect_events': True,
            'collect_image_size': True,
            'url': 'unix://var/run/docker.sock'
        }
        self.events_config = {
            'collect_events': True,
            'url': 'unix://var/run/docker.sock'
        }
        self.tag_config = {
            'collect_container_size': True,
            'collect_events': True,
            'collect_image_size': True,
            'container_tags': ['image_name'],
            'performance_tags': ['image_name', 'container_name'],
            'tags': ['test_tags'],
            'url': 'unix://var/run/docker.sock'
        }
        self.bad_configs = {'url': 'http://10.0.0.1'}

    def test_metric_collection(self):
        """Test the presence of all the metrics (container & image)."""
        self.coverage_report()

    def test_events(self):
        """Test the retrieval of events."""
        self.coverage_report()

    def test_tagging_system(self):
        """Test the available tagging features."""
        # TODO: create named containers to use the tagging per container
        self.coverage_report()

    def test_container_exclusion_logic(self):
        """Test the exclusion and inclusion logic for containers."""
        self.coverage_report()

    def test_bad_config(self):
        """Assert the failure of a bad config."""
        self.coverage_report()
