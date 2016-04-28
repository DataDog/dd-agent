# stdlib
import mock

# project
from tests.checks.common import AgentCheckTest

MOCK_CONFIG = {
    "init_config": {},
    "instances": [{
        "url": "unix://var/run/docker.sock",
        "collect_disk_stats": True,
    }]
}


class TestCheckDockerDaemon(AgentCheckTest):
    CHECK_NAME = 'docker_daemon'

    def mock_normal_get_info(self):
        return {
            'DriverStatus': [
                ['Data Space Used', '1 GB'],
                ['Data Space Available', '9 GB'],
                ['Data Space Total', '10 GB'],
                ['Metadata Space Used', '1 MB'],
                ['Metadata Space Available', '9 MB'],
                ['Metadata Space Total', '10 MB'],
            ]
        }

    def mock_get_info_no_used(self):
        return {
            'DriverStatus': [
                ['Data Space Available', '9 GB'],
                ['Data Space Total', '10 GB'],
                ['Metadata Space Available', '9 MB'],
                ['Metadata Space Total', '10 MB'],
            ]
        }

    def mock_get_info_no_data(self):
        return {
            'DriverStatus': [
                ['Metadata Space Available', '9 MB'],
                ['Metadata Space Total', '10 MB'],
                ['Metadata Space Used', '1 MB'],
            ]
        }

    def mock_get_info_invalid_values(self):
        return {
            'DriverStatus': [
                ['Metadata Space Available', '9 MB'],
                ['Metadata Space Total', '10 MB'],
                ['Metadata Space Used', '11 MB'],
            ]
        }

    def mock_get_info_all_zeros(self):
        return {
            'DriverStatus': [
                ['Data Space Available', '0 MB'],
                ['Data Space Total', '0 GB'],
                ['Data Space Used', '0 KB'],
            ]
        }

    @mock.patch('docker.Client.info')
    def test_devicemapper_disk_metrics(self, mock_info):
        mock_info.return_value = self.mock_normal_get_info()

        self.run_check(MOCK_CONFIG, force_reload=True)
        self.assertMetric('docker.data.free', value=9e9)
        self.assertMetric('docker.data.used', value=1e9)
        self.assertMetric('docker.data.total', value=10e9)
        self.assertMetric('docker.data.percent', value=10.0)
        self.assertMetric('docker.metadata.free', value=9e6)
        self.assertMetric('docker.metadata.used', value=1e6)
        self.assertMetric('docker.metadata.total', value=10e6)
        self.assertMetric('docker.metadata.percent', value=10.0)

    @mock.patch('docker.Client.info')
    def test_devicemapper_no_used_info(self, mock_info):
        """Disk metrics collection should still work and `percent` can be calculated"""
        mock_info.return_value = self.mock_get_info_no_used()

        self.run_check(MOCK_CONFIG, force_reload=True)
        self.assertMetric('docker.data.free', value=9e9)
        self.assertMetric('docker.data.total', value=10e9)
        self.assertMetric('docker.data.percent', value=10.0)
        self.assertMetric('docker.metadata.free', value=9e6)
        self.assertMetric('docker.metadata.total', value=10e6)
        self.assertMetric('docker.metadata.percent', value=10.0)

    @mock.patch('docker.Client.info')
    def test_devicemapper_no_data_info(self, mock_info):
        """Disk metrics collection should still partially work for metadata"""
        mock_info.return_value = self.mock_get_info_no_data()

        self.run_check(MOCK_CONFIG, force_reload=True)
        self.assertMetric('docker.metadata.free', value=9e6)
        self.assertMetric('docker.metadata.total', value=10e6)
        self.assertMetric('docker.metadata.percent', value=10.0)

    @mock.patch('docker.Client.info')
    def test_devicemapper_invalid_values(self, mock_info):
        """Invalid values are detected in _calc_percent_disk_stats, so percent should be missing"""
        mock_info.return_value = self.mock_get_info_invalid_values()

        self.run_check(MOCK_CONFIG, force_reload=True)
        metric_names = [metric[0] for metric in self.metrics]
        self.assertMetric('docker.metadata.free', value=9e6)
        self.assertMetric('docker.metadata.used', value=11e6)
        self.assertMetric('docker.metadata.total', value=10e6)
        self.assertNotIn('docker.metadata.percent', metric_names)

    @mock.patch('docker.Client.info')
    def test_devicemapper_all_zeros(self, mock_info):
        """Percentage should not be calculated, other metrics should be collected correctly"""
        mock_info.return_value = self.mock_get_info_all_zeros()

        self.run_check(MOCK_CONFIG, force_reload=True)
        metric_names = [metric[0] for metric in self.metrics]
        self.assertMetric('docker.data.free', value=0)
        self.assertMetric('docker.data.used', value=0)
        self.assertMetric('docker.data.total', value=0)
        self.assertNotIn('docker.data.percent', metric_names)
