# stdlib
import time

# project
from checks import AgentCheck
from util import Platform

# 3rd party
import psutil

class ProcessCheck(AgentCheck):

    SOURCE_TYPE_NAME = 'system'

    PROCESS_GAUGE = (
        'system.processes.threads',
        'system.processes.cpu.pct',
        'system.processes.mem.rss',
        'system.processes.mem.vms',
        'system.processes.mem.real',
        'system.processes.open_file_descriptors',
        'system.processes.ioread_count',
        'system.processes.iowrite_count',
        'system.processes.ioread_bytes',
        'system.processes.iowrite_bytes',
        'system.processes.voluntary_ctx_switches',
        'system.processes.involuntary_ctx_switches',
        )

    def find_pids(self, search_string, exact_match, ignore_denied_access):
        """
        Create a set of pids of selected processes.
        Search for search_string
        """
        found_process_list = []
        for proc in psutil.process_iter():
            found = False
            for string in search_string:
                if exact_match:
                    try:
                        if proc.name() == string:
                            found = True
                    except psutil.NoSuchProcess:
                        self.log.warning('Process disappeared while scanning')
                    except psutil.AccessDenied, e:
                        self.log.error('Access denied to %s process' % string)
                        self.log.error('Error: %s' % e)
                        if not ignore_denied_access: raise
                else:
                    if not found:
                        try:
                            cmdline = proc.cmdline()
                            if string in ' '.join(cmdline):
                                found = True
                        except psutil.NoSuchProcess:
                            self.warning('Process disappeared while scanning')
                        except psutil.AccessDenied, e:
                            self.log.error('Access denied to %s process' % string)
                            self.log.error('Error: %s' % e)
                            if not ignore_denied_access: raise

                if found or string == 'All':
                    found_process_list.append(proc.pid)

        return set(found_process_list)

    def get_process_metrics(self, pids, cpu_check_interval, ignore_denied_access=True):

        # initialize process metrics
        # process metrics available for all versions of psutil
        rss = 0
        vms = 0
        cpu = 0
        thr = 0
        voluntary_ctx_switches = 0
        involuntary_ctx_switches = 0

        # process metrics available for psutil versions 0.6.0 and later
        if not Platform.is_win32():
            real = 0
            if Platform.is_unix():
                open_file_descriptors = 0
            else:
                open_file_descriptors = None
        else:
            real = None

        # process I/O counters (agent might not have permission to access)
        read_count = 0
        write_count = 0
        read_bytes = 0
        write_bytes = 0

        got_denied = False

        for pid in set(pids):
            try:
                p = psutil.Process(pid)
                try:
                    if real is not None:
                        mem = p.memory_info_ex()
                        real += mem.rss - mem.shared
                        ctx_switches = p.num_ctx_switches()
                        voluntary_ctx_switches += ctx_switches.voluntary
                        involuntary_ctx_switches += ctx_switches.involuntary
                    else:
                        mem = p.memory_info()

                    rss += mem.rss
                    vms += mem.vms
                    thr += p.num_threads()
                    cpu += p.cpu_percent(cpu_check_interval)

                    if open_file_descriptors is not None:
                        open_file_descriptors += p.num_fds()

                except NotImplementedError:
                    # Handle old Kernels which don't provide this info.
                    voluntary_ctx_switches = None
                    involuntary_ctx_switches = None
                except AttributeError:
                        self.log.debug("process attribute not supported on this platform")
                except psutil.AccessDenied:
                    got_denied = True

                # user agent might not have permission to call io_counters()
                # user agent might have access to io counters for some processes and not others
                if read_count is not None:
                    try:
                        io_counters = p.io_counters()
                        read_count += io_counters.read_count
                        write_count += io_counters.write_count
                        read_bytes += io_counters.read_bytes
                        write_bytes += io_counters.write_bytes
                    except AttributeError:
                        self.log.debug("process attribute not supported on this platform")
                    except psutil.AccessDenied:
                        log_func = self.log.debug if ignore_denied_access else self.log.info
                        log_func('dd-agent user does not have access \
                            to I/O counters for process %d: %s' % (pid, p.name()))
                        read_count = None
                        write_count = None
                        read_bytes = None
                        write_bytes = None

            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                self.warning('Process %s disappeared while scanning' % pid)

        if got_denied and not ignore_denied_access:
            self.warning("The Datadog Agent was denied access when trying to get the number of file descriptors")

        #Memory values are in Byte
        return (thr, cpu, rss, vms, real, open_file_descriptors,
            read_count, write_count, read_bytes, write_bytes, voluntary_ctx_switches, involuntary_ctx_switches)

    def check(self, instance):
        name = instance.get('name', None)
        exact_match = instance.get('exact_match', True)
        search_string = instance.get('search_string', None)
        ignore_denied_access = instance.get('ignore_denied_access', True)
        cpu_check_interval = instance.get('cpu_check_interval', 0.1)

        if not isinstance(search_string, list):
            raise KeyError('"search_string" parameter should be a list')

        if "All" in search_string:
            self.warning('Deprecated: Having "All" in your search_string will\
             greatly reduce the performance of the check and will be removed in a future version of the agent. ')

        if name is None:
            raise KeyError('The "name" of process groups is mandatory')

        if search_string is None:
            raise KeyError('The "search_string" is mandatory')

        if not isinstance(cpu_check_interval, (int, long, float)):
            self.warning("cpu_check_interval must be a number. Defaulting to 0.1")
            cpu_check_interval = 0.1

        pids = self.find_pids(search_string,
                              exact_match,
                              ignore_denied_access)
        tags = ['process_name:%s' % name, name]

        self.log.debug('ProcessCheck: process %s analysed' % name)

        self.gauge('system.processes.number', len(pids), tags=tags)

        metrics = dict(zip(ProcessCheck.PROCESS_GAUGE, self.get_process_metrics(pids,
            cpu_check_interval, ignore_denied_access)))

        for metric, value in metrics.iteritems():
            if value is not None:
                self.gauge(metric, value, tags=tags)

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
