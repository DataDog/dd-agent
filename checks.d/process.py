from checks import AgentCheck
from util import Platform
import time

class ProcessCheck(AgentCheck):

    PROCESS_GAUGE = (
        'system.processes.threads',
        'system.processes.cpu.pct',
        'system.processes.mem.rss',
        'system.processes.mem.vms',
        'system.processes.mem.real',
        'system.processes.open_file_decorators',
        'system.processes.ioread_count',
        'system.processes.iowrite_count',
        'system.processes.ioread_bytes',
        'system.processes.iowrite_bytes',
        'system.processes.voluntary_ctx_switches',
        'system.processes.involuntary_ctx_switches',
        )

    def is_psutil_version_later_than(self, v):
        try:
            import psutil
            vers = psutil.version_info
            return vers >= v
        except Exception:
            return False

    def find_pids(self, search_string, psutil, exact_match=True):
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
                        if proc.name == string:
                            found = True
                    except psutil.NoSuchProcess:
                        self.log.warning('Process disappeared while scanning')
                        pass
                    except psutil.AccessDenied, e:
                        self.log.error('Access denied to %s process' % string)
                        self.log.error('Error: %s' % e)
                        raise
                else:
                    if not found:
                        try:
                            if string in ' '.join(proc.cmdline):
                                found = True
                        except psutil.NoSuchProcess:
                            self.warning('Process disappeared while scanning')
                            pass
                        except psutil.AccessDenied, e:
                            self.log.error('Access denied to %s process' % string)
                            self.log.error('Error: %s' % e)
                            raise

                if found or string == 'All':
                    found_process_list.append(proc.pid)

        return set(found_process_list)

    def get_process_metrics(self, pids, psutil, cpu_check_interval):

        # initialize process metrics
        # process metrics available for all versions of psutil
        rss = 0
        vms = 0
        cpu = 0
        thr = 0

        # process metrics available for psutil versions 0.6.0 and later
        extended_metrics_0_6_0 = self.is_psutil_version_later_than((0, 6, 0)) and \
            not Platform.is_win32()
        # On Windows get_ext_memory_info returns different metrics
        if extended_metrics_0_6_0:
            real = 0
            voluntary_ctx_switches = 0
            involuntary_ctx_switches = 0
        else:
            real = None
            voluntary_ctx_switches = None
            involuntary_ctx_switches = None

        # process metrics available for psutil versions 0.5.0 and later on UNIX
        extended_metrics_0_5_0_unix = self.is_psutil_version_later_than((0, 5, 0)) and \
                                Platform.is_unix()
        if extended_metrics_0_5_0_unix:
            open_file_descriptors = 0
        else:
            open_file_descriptors = None

        # process I/O counters (agent might not have permission to access)
        read_count = 0
        write_count = 0
        read_bytes = 0
        write_bytes = 0

        got_denied = False

        for pid in set(pids):
            try:
                p = psutil.Process(pid)
                if extended_metrics_0_6_0:
                    mem = p.get_ext_memory_info()
                    real += mem.rss - mem.shared
                    ctx_switches = p.get_num_ctx_switches()
                    voluntary_ctx_switches += ctx_switches.voluntary
                    involuntary_ctx_switches += ctx_switches.involuntary
                else:
                    mem = p.get_memory_info()

                if extended_metrics_0_5_0_unix:
                    try:
                        open_file_descriptors += p.get_num_fds()
                    except psutil.AccessDenied:
                        got_denied = True

                rss += mem.rss
                vms += mem.vms
                thr += p.get_num_threads()
                cpu += p.get_cpu_percent(cpu_check_interval)

                # user agent might not have permission to call get_io_counters()
                # user agent might have access to io counters for some processes and not others
                if read_count is not None:
                    try:
                        io_counters = p.get_io_counters()
                        read_count += io_counters.read_count
                        write_count += io_counters.write_count
                        read_bytes += io_counters.read_bytes
                        write_bytes += io_counters.write_bytes
                    except psutil.AccessDenied:
                        self.log.info('DD user agent does not have access \
                            to I/O counters for process %d: %s' % (pid, p.name))
                        read_count = None
                        write_count = None
                        read_bytes = None
                        write_bytes = None

            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                self.warning('Process %s disappeared while scanning' % pid)
                pass

        if got_denied:
            self.warning("The Datadog Agent got denied access when trying to get the number of file descriptors")

        #Memory values are in Byte
        return (thr, cpu, rss, vms, real, open_file_descriptors,
            read_count, write_count, read_bytes, write_bytes, voluntary_ctx_switches, involuntary_ctx_switches)

    def check(self, instance):
        try:
            import psutil
        except ImportError:
            raise Exception('You need the "psutil" package to run this check')

        name = instance.get('name', None)
        exact_match = instance.get('exact_match', True)
        search_string = instance.get('search_string', None)
        cpu_check_interval = instance.get('cpu_check_interval', 0.1)

        if name is None:
            raise KeyError('The "name" of process groups is mandatory')

        if search_string is None:
            raise KeyError('The "search_string" is mandatory')

        if not isinstance(cpu_check_interval, (int, long, float)):
            self.warning("cpu_check_interval must be a number. Defaulting to 0.1")
            cpu_check_interval = 0.1

        pids = self.find_pids(search_string, psutil, exact_match=exact_match)
        tags = ['process_name:%s' % name, name]

        self.log.debug('ProcessCheck: process %s analysed' % name)

        self.gauge('system.processes.number', len(pids), tags=tags)

        metrics = dict(zip(ProcessCheck.PROCESS_GAUGE, self.get_process_metrics(pids,
            psutil, cpu_check_interval)))

        for metric, value in metrics.iteritems():
            if value is not None:
                self.gauge(metric, value, tags=tags)

