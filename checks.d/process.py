# stdlib
from collections import defaultdict
import time

# 3p
import psutil

# project
from checks import AgentCheck
from config import _is_affirmative
from utils.platform import Platform


DEFAULT_AD_CACHE_DURATION = 120
DEFAULT_PID_CACHE_DURATION = 120


ATTR_TO_METRIC = {
    'thr':              'threads',
    'cpu':              'cpu.pct',
    'rss':              'mem.rss',
    'vms':              'mem.vms',
    'real':             'mem.real',
    'open_fd':          'open_file_descriptors',
    'r_count':          'ioread_count',  # FIXME: namespace me correctly (6.x), io.r_count
    'w_count':          'iowrite_count',  # FIXME: namespace me correctly (6.x) io.r_bytes
    'r_bytes':          'ioread_bytes',  # FIXME: namespace me correctly (6.x) io.w_count
    'w_bytes':          'iowrite_bytes',  # FIXME: namespace me correctly (6.x) io.w_bytes
    'ctx_swtch_vol':    'voluntary_ctx_switches',  # FIXME: namespace me correctly (6.x), ctx_swt.voluntary
    'ctx_swtch_invol':  'involuntary_ctx_switches',  # FIXME: namespace me correctly (6.x), ctx_swt.involuntary
}


class ProcessCheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # ad stands for access denied
        # We cache the PIDs getting this error and don't iterate on them
        # more often than `access_denied_cache_duration`
        # This cache is for all PIDs so it's global
        self.last_ad_cache_ts = 0
        self.ad_cache = set()
        self.access_denied_cache_duration = int(
            init_config.get(
                'access_denied_cache_duration',
                DEFAULT_AD_CACHE_DURATION
            )
        )

        # By default cache the PID list for a while
        # Sometimes it's not wanted b/c it can mess with no-data monitoring
        # This cache is indexed per instance
        self.last_pid_cache_ts = {}
        self.pid_cache = {}
        self.pid_cache_duration = int(
            init_config.get(
                'pid_cache_duration',
                DEFAULT_PID_CACHE_DURATION
            )
        )

    def should_refresh_ad_cache(self):
        now = time.time()
        return now - self.last_ad_cache_ts > self.access_denied_cache_duration

    def should_refresh_pid_cache(self, name):
        now = time.time()
        return now - self.last_pid_cache_ts.get(name, 0) > self.pid_cache_duration

    def find_pids(self, name, search_string, exact_match, ignore_ad=True,
                  refresh_ad_cache=True):
        """
        Create a set of pids of selected processes.
        Search for search_string
        """
        if not self.should_refresh_pid_cache(name):
            return self.pid_cache[name]

        ad_error_logger = self.log.debug
        if not ignore_ad:
            ad_error_logger = self.log.error

        refresh_ad_cache = self.should_refresh_ad_cache()

        matching_pids = set()

        for proc in psutil.process_iter():
            # Skip access denied processes
            if not refresh_ad_cache and proc.pid in self.ad_cache:
                continue

            found = False
            for string in search_string:
                try:
                    # FIXME 6.x: All has been deprecated from the doc, should be removed
                    if string == 'All':
                        found = True
                    if exact_match:
                        if proc.name() == string:
                            found = True
                    else:
                        cmdline = proc.cmdline()
                        if string in ' '.join(cmdline):
                            found = True
                except psutil.NoSuchProcess:
                    self.log.warning('Process disappeared while scanning')
                except psutil.AccessDenied, e:
                    ad_error_logger('Access denied to process with PID %s', proc.pid)
                    ad_error_logger('Error: %s', e)
                    if refresh_ad_cache:
                        self.ad_cache.add(proc.pid)
                    if not ignore_ad:
                        raise
                else:
                    if refresh_ad_cache:
                        self.ad_cache.discard(proc.pid)
                    if found:
                        matching_pids.add(proc.pid)
                        break

        self.pid_cache[name] = matching_pids
        self.last_pid_cache_ts[name] = time.time()
        return matching_pids

    def psutil_wrapper(self, process, method, accessors, *args, **kwargs):
        """
        A psutil wrapper that is calling
        * psutil.method(*args, **kwargs) and returns the result
        OR
        * psutil.method(*args, **kwargs).accessor[i] for each accessors given in
        a list, the result being indexed in a dictionary by the accessor name
        """

        if accessors is None:
            result = None
        else:
            result = {}

        # Ban certain method that we know fail
        if method == 'memory_info_ex'\
                and (Platform.is_win32() or Platform.is_solaris()):
            return result
        elif method == 'num_fds' and not Platform.is_unix():
            return result

        try:
            res = getattr(process, method)(*args, **kwargs)
            if accessors is None:
                result = res
            else:
                for acc in accessors:
                    try:
                        result[acc] = getattr(res, acc)
                    except AttributeError:
                        self.log.debug("psutil.%s().%s attribute does not exist", method, acc)
        except (NotImplementedError, AttributeError):
            self.log.debug("psutil method %s not implemented", method)
        except psutil.AccessDenied:
            self.log.debug("psutil was denied acccess for method %s", method)
        except psutil.NoSuchProcess:
            self.warning("Process {0} disappeared while scanning".format(process.pid))

        return result


    def get_process_state(self, name, pids, cpu_check_interval):
        st = defaultdict(list)

        for pid in pids:
            st['pids'].append(pid)

            try:
                p = psutil.Process(pid)
            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                self.warning('Process %s disappeared while scanning' % pid)
                # reset the PID cache now, something chaned
                self.last_pid_cache_ts[name] = 0

            meminfo = self.psutil_wrapper(p, 'memory_info', ['rss', 'vms'])
            st['rss'].append(meminfo.get('rss'))
            st['vms'].append(meminfo.get('vms'))

            # will fail on win32 and solaris
            shared_mem = self.psutil_wrapper(p, 'memory_info_ex', ['shared']).get('shared')
            if shared_mem is not None and meminfo.get('rss') is not None:
                st['real'].append(meminfo['rss'] - shared_mem)
            else:
                st['real'].append(None)

            ctxinfo = self.psutil_wrapper(p, 'num_ctx_switches', ['voluntary', 'involuntary'])
            st['ctx_swtch_vol'].append(ctxinfo.get('voluntary'))
            st['ctx_swtch_invol'].append(ctxinfo.get('involuntary'))

            st['thr'].append(self.psutil_wrapper(p, 'num_threads', None))
            st['cpu'].append(self.psutil_wrapper(p, 'cpu_percent', None, cpu_check_interval))

            st['open_fd'].append(self.psutil_wrapper(p, 'num_fds', None))

            ioinfo = self.psutil_wrapper(p, 'io_counters', ['read_count', 'write_count', 'read_bytes', 'write_bytes'])
            st['r_count'].append(ioinfo.get('read_count'))
            st['w_count'].append(ioinfo.get('write_count'))
            st['r_bytes'].append(ioinfo.get('read_bytes'))
            st['w_bytes'].append(ioinfo.get('write_bytes'))

        return st

    def check(self, instance):
        name = instance.get('name', None)
        tags = instance.get('tags', [])
        exact_match = _is_affirmative(instance.get('exact_match', True))
        search_string = instance.get('search_string', None)
        ignore_ad = _is_affirmative(instance.get('ignore_denied_access', True))
        cpu_check_interval = instance.get('cpu_check_interval', 0.1)

        if not isinstance(search_string, list):
            raise KeyError('"search_string" parameter should be a list')

        # FIXME 6.x remove me
        if "All" in search_string:
            self.warning('Deprecated: Having "All" in your search_string will'
                         'greatly reduce the performance of the check and '
                         'will be removed in a future version of the agent.')

        if name is None:
            raise KeyError('The "name" of process groups is mandatory')

        if search_string is None:
            raise KeyError('The "search_string" is mandatory')

        if not isinstance(cpu_check_interval, (int, long, float)):
            self.warning("cpu_check_interval must be a number. Defaulting to 0.1")
            cpu_check_interval = 0.1

        pids = self.find_pids(
            name,
            search_string,
            exact_match,
            ignore_ad=ignore_ad
        )

        proc_state = self.get_process_state(name, pids, cpu_check_interval)

        # FIXME 6.x remove the `name` tag
        tags.extend(['process_name:%s' % name, name])

        self.log.debug('ProcessCheck: process %s analysed', name)
        self.gauge('system.processes.number', len(pids), tags=tags)

        for attr, mname in ATTR_TO_METRIC.iteritems():
            vals = [x for x in proc_state[attr] if x is not None]
            # skip []
            if vals:
                # FIXME 6.x: change this prefix?
                self.gauge('system.processes.%s' % mname, sum(vals), tags=tags)

        self._process_service_check(name, len(pids), instance.get('thresholds', None))

    def _process_service_check(self, name, nb_procs, bounds):
        '''
        Repport a service check, for each processes in search_string.
        Repport as OK if the process is in the warning thresolds
                   CRITICAL             out of the critical thresolds
                   WARNING              out of the warning thresolds
        '''
        tag = ["process:%s" % name]
        status = AgentCheck.OK
        message_str = "PROCS %s: %s processes found for %s"
        status_str = {
            AgentCheck.OK: "OK",
            AgentCheck.WARNING: "WARNING",
            AgentCheck.CRITICAL: "CRITICAL"
        }

        if not bounds and nb_procs < 1:
            status = AgentCheck.CRITICAL
        elif bounds:
            warning = bounds.get('warning', [1, float('inf')])
            critical = bounds.get('critical', [1, float('inf')])

            if warning[1] < nb_procs or nb_procs < warning[0]:
                status = AgentCheck.WARNING
            if critical[1] < nb_procs or nb_procs < critical[0]:
                status = AgentCheck.CRITICAL

        self.service_check(
            "process.up",
            status,
            tags=tag,
            message=message_str % (status_str[status], nb_procs, name)
        )
