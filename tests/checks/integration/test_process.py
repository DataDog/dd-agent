""" Put in integration/
because it requires psutil to function properly
"""

# stdlib
import os

# 3p
from mock import patch
import psutil

# project
from tests.checks.common import AgentCheckTest


# cross-platform switches
_PSUTIL_IO_COUNTERS = True
try:
    p = psutil.Process(os.getpid())
    p.io_counters()
except Exception:
    _PSUTIL_IO_COUNTERS = False

_PSUTIL_MEM_SHARED = True
try:
    p = psutil.Process(os.getpid())
    p.memory_info_ex().shared
except Exception:
    _PSUTIL_MEM_SHARED = False



class ProcessCheckTest(AgentCheckTest):
    CHECK_NAME = 'process'

    CONFIG_STUBS = [
        {
            'config': {
                'name': 'test_0',
                'search_string': ['test_0'],  # index in the array for our find_pids mock
                'thresholds': {
                    'critical': [2, 4],
                    'warning': [1, 5]
                }
            },
            'mocked_processes': 0
        },
        {
            'config': {
                'name': 'test_1',
                'search_string': ['test_1'],  # index in the array for our find_pids mock
                'thresholds': {
                    'critical': [1, 5],
                    'warning': [2, 4]
                }
            },
            'mocked_processes': 1
        },
        {
            'config': {
                'name': 'test_2',
                'search_string': ['test_2'],  # index in the array for our find_pids mock
                'thresholds': {
                    'critical': [2, 5],
                    'warning': [1, 4]
                }
            },
            'mocked_processes': 3
        },
        {
            'config': {
                'name': 'test_3',
                'search_string': ['test_3'],  # index in the array for our find_pids mock
                'thresholds': {
                    'critical': [1, 4],
                    'warning': [2, 5]
                }
            },
            'mocked_processes': 5
        },
        {
            'config': {
                'name': 'test_4',
                'search_string': ['test_4'],  # index in the array for our find_pids mock
                'thresholds': {
                    'critical': [1, 4],
                    'warning': [2, 5]
                }
            },
            'mocked_processes': 6
        },
        {
            'config': {
                'name': 'test_tags',
                'search_string': ['test_5'],  # index in the array for our find_pids mock
                'tags': ['onetag', 'env:prod']
            },
            'mocked_processes': 1
        },
        {
            'config': {
                'name': 'test_badthresholds',
                'search_string': ['test_6'],  # index in the array for our find_pids mock
                'thresholds': {
                    'test': 'test'
                }
            },
            'mocked_processes': 1
        },
    ]

    PROCESS_METRIC = [
        'system.processes.cpu.pct',
        'system.processes.involuntary_ctx_switches',
        'system.processes.ioread_bytes',
        'system.processes.ioread_count',
        'system.processes.iowrite_bytes',
        'system.processes.iowrite_count',
        'system.processes.mem.real',
        'system.processes.mem.rss',
        'system.processes.mem.vms',
        'system.processes.number',
        'system.processes.open_file_descriptors',
        'system.processes.threads',
        'system.processes.voluntary_ctx_switches'
    ]

    def get_psutil_proc(self):
        return psutil.Process(os.getpid())

    def test_psutil_wrapper_simple(self):
        # Load check with empty config
        self.run_check({})
        name = self.check.psutil_wrapper(
            self.get_psutil_proc(),
            'name',
            None
        )

        self.assertNotEquals(name, None)

    def test_psutil_wrapper_simple_fail(self):
        # Load check with empty config
        self.run_check({})
        name = self.check.psutil_wrapper(
            self.get_psutil_proc(),
            'blah',
            None
        )

        self.assertEquals(name, None)

    def test_psutil_wrapper_accessors(self):
        # Load check with empty config
        self.run_check({})
        meminfo = self.check.psutil_wrapper(
            self.get_psutil_proc(),
            'memory_info',
            ['rss', 'vms', 'foo']
        )

        self.assertIn('rss', meminfo)
        self.assertIn('vms', meminfo)
        self.assertNotIn('foo', meminfo)

    def test_psutil_wrapper_accessors_fail(self):
        # Load check with empty config
        self.run_check({})
        meminfo = self.check.psutil_wrapper(
            self.get_psutil_proc(),
            'memory_infoo',
            ['rss', 'vms']
        )

        self.assertNotIn('rss', meminfo)
        self.assertNotIn('vms', meminfo)

    def test_ad_cache(self):
        config = {
            'instances': [{
                'name': 'python',
                'search_string': ['python'],
                'ignore_denied_access': 'false'
            }]
        }

        def deny_cmdline(obj):
            raise psutil.AccessDenied()

        try:
            with patch.object(psutil.Process, 'name', deny_cmdline):
                self.run_check(config)
        except psutil.AccessDenied:
            pass

        self.assertTrue(len(self.check.ad_cache) > 0)
        # The next run shoudn't throw an exception
        self.run_check(config)

        # Reset the cache now
        self.check.last_ad_cache_ts = 0
        self.assertRaises(Exception, lambda: self.run_check, config)

    def mock_find_pids(self, search_string, exact_match=True, ignore_ad=True,
                       refresh_ad_cache=True):
        idx = search_string[0].split('_')[1]
        # Use a real PID to get real metrics!
        return [os.getpid()] * self.CONFIG_STUBS[int(idx)]['mocked_processes']

    def test_check(self):
        mocks = {
            'find_pids': self.mock_find_pids
        }

        config = {
            'instances': [stub['config'] for stub in self.CONFIG_STUBS]
        }
        self.run_check(config, mocks=mocks)

        for stub in self.CONFIG_STUBS:
            mocked_processes = stub['mocked_processes']

            # Assert metrics
            for mname in self.PROCESS_METRIC:
                proc_name = stub['config']['name']
                expected_tags = [proc_name, "process_name:{0}".format(proc_name)]

                # If a list of tags is already there, the check extends it
                if 'tags' in stub['config']:
                    expected_tags += stub['config']['tags']

                expected_value = None
                # cases where we don't actually expect some metrics
                #  - if no processes are matched we don't send metrics except number
                #  - if io_counters() is not available skip the metrics
                #  - if memory_info_ex() is not available skip the metrics
                if (mocked_processes == 0 and mname != 'system.processes.number')\
                    or (not _PSUTIL_IO_COUNTERS and '.io' in mname)\
                    or (not _PSUTIL_MEM_SHARED and 'mem.real' in mname):
                    continue

                if mname == 'system.processes.number':
                    expected_value = mocked_processes

                self.assertMetric(
                    mname, count=1,
                    tags=expected_tags,
                    value=expected_value
                )

            # Assert service checks
            expected_tags = ['process:{0}'.format(stub['config']['name'])]
            critical = stub['config'].get('thresholds', {}).get('critical')
            warning = stub['config'].get('thresholds', {}).get('warning')
            procs = stub['mocked_processes']

            if critical is not None and (procs < critical[0] or procs > critical[1]):
                self.assertServiceCheckCritical('process.up', count=1, tags=expected_tags)
            elif warning is not None and (procs < warning[0] or procs > warning[1]):
                self.assertServiceCheckWarning('process.up', count=1, tags=expected_tags)
            else:
                self.assertServiceCheckOK('process.up', count=1, tags=expected_tags)

        # Raises when COVERAGE=true and coverage < 100%
        self.coverage_report()

    def test_check_real_process(self):
        "Check that we detect python running (at least this process)"
        config = {
            'instances': [{
                'name': 'py',
                'search_string': ['python'],
                'exact_match': False,
                'ignored_denied_access': True,
                'thresholds': {'warning': [1, 10], 'critical': [1, 100]},
            }]
        }

        self.run_check(config)

        expected_tags = ['py', 'process_name:py']
        for mname in self.PROCESS_METRIC:
            # See same tests comment in the function `test_check`
            if (not _PSUTIL_IO_COUNTERS and '.io' in mname)\
                or (not _PSUTIL_MEM_SHARED and 'mem.real' in mname):
                continue
            self.assertMetric(mname, at_least=1, tags=expected_tags)

        self.assertServiceCheckOK('process.up', count=1, tags=['process:py'])

        self.coverage_report()
