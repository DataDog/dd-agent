""" Put in integration/
because it requires psutil to function properly
"""

# stdlib
import contextlib
import os

# 3p
from mock import patch, MagicMock
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


class MockProcess(object):
    def is_running(self):
        return True

def noop_get_pagefault_stats(pid):
    return None

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
            'mocked_processes': set()
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
            'mocked_processes': set([1])
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
            'mocked_processes': set([22, 35])
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
            'mocked_processes': set([1, 5, 44, 901, 34])
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
            'mocked_processes': set([3, 7, 2, 9, 34, 72])
        },
        {
            'config': {
                'name': 'test_tags',
                'search_string': ['test_5'],  # index in the array for our find_pids mock
                'tags': ['onetag', 'env:prod']
            },
            'mocked_processes': set([2])
        },
        {
            'config': {
                'name': 'test_badthresholds',
                'search_string': ['test_6'],  # index in the array for our find_pids mock
                'thresholds': {
                    'test': 'test'
                }
            },
            'mocked_processes': set([89])
        },
        {
            'config': {
                'name': 'test_7',
                'search_string': ['test_7'],  # index in the array for our find_pids mock
                'thresholds': {
                    'critical': [2, 4],
                    'warning': [1, 5]
                }
            },
            'mocked_processes': set([1])
        }
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

    PAGEFAULT_STAT = [
        'minor_faults',
        'children_minor_faults',
        'major_faults',
        'children_major_faults'
    ]

    def get_psutil_proc(self):
        return psutil.Process(os.getpid())

    def test_psutil_wrapper_simple(self):
        # Load check with empty config
        self.run_check({}, mocks={'get_pagefault_stats': noop_get_pagefault_stats})
        name = self.check.psutil_wrapper(
            self.get_psutil_proc(),
            'name',
            None
        )

        self.assertNotEquals(name, None)

    def test_psutil_wrapper_simple_fail(self):
        # Load check with empty config
        self.run_check({}, mocks={'get_pagefault_stats': noop_get_pagefault_stats})
        name = self.check.psutil_wrapper(
            self.get_psutil_proc(),
            'blah',
            None
        )

        self.assertEquals(name, None)

    def test_psutil_wrapper_accessors(self):
        # Load check with empty config
        self.run_check({}, mocks={'get_pagefault_stats': noop_get_pagefault_stats})
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
        self.run_check({}, mocks={'get_pagefault_stats': noop_get_pagefault_stats})
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

        def deny_name(obj):
            raise psutil.AccessDenied()

        with patch.object(psutil.Process, 'name', deny_name):
            self.assertRaises(psutil.AccessDenied, self.run_check, config)

        self.assertTrue(len(self.check.ad_cache) > 0)

        # The next run shoudn't throw an exception
        self.run_check(config, mocks={'get_pagefault_stats': noop_get_pagefault_stats})
        # The ad cache should still be valid
        self.assertFalse(self.check.should_refresh_ad_cache('python'))

        # Reset caches
        self.check.last_ad_cache_ts = {}
        self.check.last_pid_cache_ts = {}
        # Shouldn't throw an exception
        self.run_check(config, mocks={'get_pagefault_stats': noop_get_pagefault_stats})

    def mock_find_pids(self, name, search_string, exact_match=True, ignore_ad=True,
                       refresh_ad_cache=True):
        idx = search_string[0].split('_')[1]
        return self.CONFIG_STUBS[int(idx)]['mocked_processes']

    def mock_psutil_wrapper(self, process, method, accessors, *args, **kwargs):
        if method == 'num_handles':  # remove num_handles as it's win32 only
            return None

        if accessors is None:
            result = 0
        else:
            result = dict([(accessor, 0) for accessor in accessors])

        return result

    def generate_expected_tags(self, instance_config):
        proc_name = instance_config['name']
        expected_tags = [proc_name, "process_name:{0}".format(proc_name)]
        if 'tags' in instance_config:
            expected_tags += instance_config['tags']
        return expected_tags

    @patch('psutil.Process', return_value=MockProcess())
    def test_check(self, mock_process):
        (minflt, cminflt, majflt, cmajflt) = [1, 2, 3, 4]

        def mock_get_pagefault_stats(pid):
            return [minflt, cminflt, majflt, cmajflt]

        mocks = {
            'find_pids': self.mock_find_pids,
            'psutil_wrapper': self.mock_psutil_wrapper,
            'get_pagefault_stats': mock_get_pagefault_stats,
        }

        config = {
            'instances': [stub['config'] for stub in self.CONFIG_STUBS]
        }

        self.run_check_twice(config, mocks=mocks)

        instance_config = config['instances'][-1]
        for stat_name in self.PAGEFAULT_STAT:
            self.assertMetric('system.processes.mem.page_faults.' + stat_name,
                tags=self.generate_expected_tags(instance_config),
                value=0)

        for stub in self.CONFIG_STUBS:
            mocked_processes = stub['mocked_processes']
            # Assert metrics
            for mname in self.PROCESS_METRIC:
                expected_tags = self.generate_expected_tags(stub['config'])
                expected_value = None
                # - if no processes are matched we don't send metrics except number
                # - it's the first time the check runs so don't send cpu.pct
                if (len(mocked_processes) == 0 and mname != 'system.processes.number'):
                    continue

                if mname == 'system.processes.number':
                    expected_value = len(mocked_processes)

                self.assertMetric(
                    mname, count=1,
                    tags=expected_tags,
                    value=expected_value
                )

            # these are just here to ensure it passes the coverage report.
            # they don't really "test" for anything.
            for stat_name in self.PAGEFAULT_STAT:
                self.assertMetric('system.processes.mem.page_faults.' + stat_name, at_least=0,
                    tags=self.generate_expected_tags(stub['config']))

            # Assert service checks
            expected_tags = ['process:{0}'.format(stub['config']['name'])]
            critical = stub['config'].get('thresholds', {}).get('critical')
            warning = stub['config'].get('thresholds', {}).get('warning')
            procs = len(stub['mocked_processes'])

            if critical is not None and (procs < critical[0] or procs > critical[1]):
                self.assertServiceCheckCritical('process.up', count=1, tags=expected_tags)
            elif warning is not None and (procs < warning[0] or procs > warning[1]):
                self.assertServiceCheckWarning('process.up', count=1, tags=expected_tags)
            else:
                self.assertServiceCheckOK('process.up', count=1, tags=expected_tags)


        # Raises when coverage < 100%
        self.coverage_report()

        # Run the check a second time and check that `cpu_pct` is there
        self.run_check(config, mocks=mocks)
        for stub in self.CONFIG_STUBS:
            expected_tags = self.generate_expected_tags(stub['config'])

            if len(stub['mocked_processes']) == 0:
                continue

            self.assertMetric('system.processes.cpu.pct', count=1, tags=expected_tags)

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

        self.run_check(config, mocks={'get_pagefault_stats': noop_get_pagefault_stats})

        expected_tags = self.generate_expected_tags(config['instances'][0])
        for mname in self.PROCESS_METRIC:
            # cases where we don't actually expect some metrics here:
            #  - if io_counters() is not available
            #  - if memory_info_ex() is not available
            #  - first run so no `cpu.pct`
            if (not _PSUTIL_IO_COUNTERS and '.io' in mname)\
                    or (not _PSUTIL_MEM_SHARED and 'mem.real' in mname)\
                    or mname == 'system.processes.cpu.pct':
                continue
            self.assertMetric(mname, at_least=1, tags=expected_tags)

        self.assertServiceCheckOK('process.up', count=1, tags=['process:py'])

        self.coverage_report()

        # Run the check a second time and check that `cpu_pct` is there
        self.run_check(config, mocks={'get_pagefault_stats': noop_get_pagefault_stats})
        self.assertMetric('system.processes.cpu.pct', count=1, tags=expected_tags)

    def test_relocated_procfs(self):
        from utils.platform import Platform
        import tempfile
        import shutil
        import uuid

        already_linux = Platform.is_linux()
        unique_process_name = str(uuid.uuid4())
        my_procfs = tempfile.mkdtemp()

        def _fake_procfs(arg, root=my_procfs):
            for key, val in arg.iteritems():
                path = os.path.join(root, key)
                if isinstance(val, dict):
                    os.mkdir(path)
                    _fake_procfs(val, path)
                else:
                    with open(path, "w") as f:
                        f.write(str(val))
        _fake_procfs({
            '1': {
                'status': (
                    "Name:\t%s\n"
                ) % unique_process_name,
                'stat': ('1 (%s) S 0 1 1 ' + ' 0' * 46) % unique_process_name,
                'cmdline': unique_process_name,

            },
            'stat': (
                "cpu  13034 0 18596 380856797 2013 2 2962 0 0 0\n"
                "btime 1448632481\n"
            ),
        })

        config = {
            'init_config': {
                'procfs_path': my_procfs
            },
            'instances': [{
                'name': 'moved_procfs',
                'search_string': [unique_process_name],
                'exact_match': False,
                'ignored_denied_access': True,
                'thresholds': {'warning': [1, 10], 'critical': [1, 100]},
            }]
        }

        version = int(psutil.__version__.replace(".", ""))
        try:
            def import_mock(name, i_globals={}, i_locals={}, fromlist=[], level=-1, orig_import=__import__):
                # _psutil_linux and _psutil_posix are the C bindings; use a mock for those
                if name in ('_psutil_linux', '_psutil_posix') or level >= 1 and ('_psutil_linux' in fromlist or '_psutil_posix' in fromlist):
                    m = MagicMock()
                    # the import system will ask us for our own name
                    m._psutil_linux = m
                    m._psutil_posix = m
                    # there's a version safety check in psutil/__init__.py; this skips it
                    m.version = version
                    return m
                return orig_import(name, i_globals, i_locals, fromlist, level)

            orig_open = open

            def open_mock(name, *args):
                from mock import MagicMock

                # Work around issue addressed here: https://github.com/giampaolo/psutil/pull/715
                # TODO: Remove open_mock if the patch lands
                # We can't use patch here because 1) we're reloading psutil, and 2) the problem is happening during the import.
                # NB: The values generated here are mostly ignored, and will correctly be overwritten once we set PROCFS_PATH
                if name == '/proc/stat':
                    handle = MagicMock(spec=file)
                    handle.write.return_value = None
                    handle.__enter__.return_value = handle
                    handle.readline.return_value = 'cpu  13002 0 18504 377363817 1986 2 2960 0 0 0'
                    return handle
                return orig_open(name, *args)

            # contextlib.nested is deprecated in favor of with MGR1, MGR2, ... etc, but we have too many mocks to fit on one line and apparently \ line
            # continuation is not flake8 compliant, even when semantically required (as here). Patch is unlikely to throw errors that are suppressed, so
            # the main downside of contextlib is avoided.
            with contextlib.nested(patch('sys.platform', 'linux'),
                                   patch('socket.AF_PACKET', create=True),
                                   patch('__builtin__.__import__', side_effect=import_mock),
                                   patch('__builtin__.open', side_effect=open_mock)):
                if not already_linux:
                    # Reloading psutil fails on linux, but we only need to do so if we didn't start out on a linux platform
                    reload(psutil)
                assert Platform.is_linux()

                self.run_check(config, mocks={'get_pagefault_stats': noop_get_pagefault_stats})
        finally:
            shutil.rmtree(my_procfs)
            if not already_linux:
                # restore the original psutil that doesn't have our mocks
                reload(psutil)
            else:
                psutil.PROCFS_PATH = '/proc'

        expected_tags = self.generate_expected_tags(config['instances'][0])
        self.assertServiceCheckOK('process.up', count=1, tags=['process:moved_procfs'])

        self.assertMetric('system.processes.number', at_least=1, tags=expected_tags)

        self.coverage_report()
