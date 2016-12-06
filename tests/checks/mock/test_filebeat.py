# stdlib
from collections import namedtuple
import os

# 3p
from mock import patch

# project
from tests.checks.common import AgentCheckTest, Fixtures

mocked_file_stats = namedtuple('mocked_file_stats', ['st_size', 'st_ino', 'st_dev'])


# allows mocking `os.stat` only for certain paths; for all others it will call
# the actual function - needed as a number of test helpers do make calls to it
def with_mocked_os_stat(mocked_paths_and_stats):
    vanilla_os_stat = os.stat

    def internal_mock(path):
        if path in mocked_paths_and_stats:
            return mocked_paths_and_stats[path]
        return vanilla_os_stat(path)

    def external_wrapper(function):
        # silly, but this _must_ start with `test_` for nose to pick it up as a
        # test when used below
        def test_wrapper(*args, **kwargs):
            with patch.object(os, 'stat') as patched_os_stat:
                patched_os_stat.side_effect = internal_mock
                return function(*args, **kwargs)
        return test_wrapper

    return external_wrapper


class TestCheckFilebeat(AgentCheckTest):
    CHECK_NAME = 'filebeat'

    def _build_config(self, name):
        return {
            'init_config': None,
            'instances': [
                {
                    'registry_file_path': Fixtures.file(name + '_registry.json')
                }
            ]
        }

    @with_mocked_os_stat({'/test_dd_agent/var/log/nginx/access.log': mocked_file_stats(394154, 277025, 51713),
                          '/test_dd_agent/var/log/syslog': mocked_file_stats(1024917, 152172, 51713)})
    def test_happy_path(self):
        self.run_check(self._build_config('happy_path'))

        self.assertMetric('filebeat.registry.unprocessed_bytes', value=2407, tags=['source:/test_dd_agent/var/log/nginx/access.log'])
        self.assertMetric('filebeat.registry.unprocessed_bytes', value=0, tags=['source:/test_dd_agent/var/log/syslog'])

    def test_bad_config(self):
        bad_config = {
            'init_config': None,
            'instances': [{}]
        }

        self.assertRaises(
            Exception,
            lambda: self.run_check(bad_config)
        )

    def test_missing_registry_file(self):
        # tests that it simply silently ignores it
        self.run_check(self._build_config('i_dont_exist'))
        self.assertMetric('filebeat.registry.unprocessed_bytes', count=0)

    def test_missing_source_file(self):
        self.run_check(self._build_config('missing_source_file'))
        self.assertMetric('filebeat.registry.unprocessed_bytes', count=0)

    @with_mocked_os_stat({'/test_dd_agent/var/log/syslog': mocked_file_stats(1024917, 152171, 51713)})
    def test_source_file_inode_has_changed(self):
        self.run_check(self._build_config('single_source'))
        self.assertMetric('filebeat.registry.unprocessed_bytes', count=0)

    @with_mocked_os_stat({'/test_dd_agent/var/log/syslog': mocked_file_stats(1024917, 152172, 51714)})
    def test_source_file_device_has_changed(self):
        self.run_check(self._build_config('single_source'))
        self.assertMetric('filebeat.registry.unprocessed_bytes', count=0)
