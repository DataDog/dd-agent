from tests.checks.common import AgentCheckTest
MOCK_CONFIG = {
    "init_config": {},
    "instances": [{
        "url": "unix://var/run/docker.sock",
        "collect_daemon_stats": True,
    },
    ],
}

class TestCheckDockerDaemon(AgentCheckTest):
    CHECK_NAME = 'docker_daemon'

    def mock_get_daemon_info(self):
        return {
            'DriverStatus': [
                ['Data Space Used', '1 GB'],
                ['Data Space Available', '9 GB'],
                ['Data Space Total', '10 GB'],
                ['Metadata Space Used', '1 MB'],
                ['Metadata Space Available', '9 MB'],
                ['Metadata Space Total', '10 MB'],
            ],
        }

    def test_devicemapper_storage_driver(self):
        mocks = {
            '_get_daemon_info': self.mock_get_daemon_info,
        }
        self.run_check(MOCK_CONFIG, mocks=mocks)
        self.assertMetric('docker.info.data.free', value=9e9)
        self.assertMetric('docker.info.data.used', value=1e9)
        self.assertMetric('docker.info.data.total', value=10e9)
        self.assertMetric('docker.info.data.in_use', value=0.1)
        self.assertMetric('docker.info.metadata.free', value=9e6)
        self.assertMetric('docker.info.metadata.used', value=1e6)
        self.assertMetric('docker.info.metadata.total', value=10e6)
        self.assertMetric('docker.info.metadata.in_use', value=0.1)
