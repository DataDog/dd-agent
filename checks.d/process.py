from checks import AgentCheck
from checks.system import Platform
import time

class ProcessCheck(AgentCheck):

    def get_library_versions(self):
        try:
            import psutil
            version = psutil.__version__
        except ImportError:
            version = "Not Found"
        except AttributeError:
            version = "Unknown"

        return {"psutil": version}

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
        rss = 0
        vms = 0
        cpu = 0
        thr = 0
        iorc = 0
        iowc = 0
        iorb = 0
        iowb = 0

        extended_metrics_0_6_0 = self.psutil_v_or_later(psutil, (0, 6, 0))
        extended_metrics_0_5_0_unix = self.psutil_v_or_later(psutil, (0, 5, 0)) and \
                                        Platform.is_unix()
        if extended_metrics_0_6_0:
            real = 0
            cxs = 0
        else:
            real = None
            cxs = None

        if extended_metrics_0_5_0_unix:
            fds = 0
        else:
            fds = None

        for pid in set(pids):
            try:
                p = psutil.Process(pid)
                if extended_metrics_0_6_0:
                    mem = p.get_ext_memory_info()
                    real += mem.rss - mem.shared
                    cxs += p.get_num_ctx_switches()
                else:
                    mem = p.get_memory_info()

                if extended_metrics_0_5_0_unix:
                    fds += p.get_num_fds()

                rss += mem.rss
                vms += mem.vms
                thr += p.get_num_threads()
                cpu += p.get_cpu_percent(cpu_check_interval)

                # user agent might not have permission to access get_io_counters()
                # is it possible for the agent to have access for some processes and not others?
                # if partial access is possible, would an io read_count still be useful?
                if iorc is not None:
                    try:
                        ioc = p.get_io_counters()
                        iorc += ioc.read_count
                        iowc += ioc.write_count
                        iorb += ioc.read_bytes
                        iowb += ioc.write_bytes
                    except psutil.AccessDenied:
                        self.warning('DD user agent does not have access to process io counters')
                        iorc = None

            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                self.warning('Process %s disappeared while scanning' % pid)
                pass

        #Memory values are in Byte
        return (thr, cpu, rss, vms, real, fds, iorc, iowc, iorb, iowb, cxs)

    def psutil_v_or_later(self, psutil, v):
        vers = psutil.version_info
        return 100 * vers[0] + 10 * vers[1] + vers[2] >= 100 * v[0] + 10 * v[1] + v[2]

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
        thr, cpu, rss, vms, real, fds, iorc, iowc, iorb, iowb, cxs = self.get_process_metrics(pids,
            psutil, cpu_check_interval)

        self.gauge('system.processes.mem.rss', rss, tags=tags)
        self.gauge('system.processes.mem.vms', vms, tags=tags)
        self.gauge('system.processes.cpu.pct', cpu, tags=tags)
        self.gauge('system.processes.threads', thr, tags=tags)
        if real is not None:
            self.gauge('system.processes.mem.real', real, tags=tags)
        if fds is not None:
            self.gauge('system.processes.open_file_descriptors', fds, tags=tags)
        if cxs is not None:
            self.gauge('system.processes.ctx_switches', cxs, tags=tags)
        if iorc:
            self.gauge('system.processes.ioread_count', iorc, tags=tags)
            self.gauge('system.processes.iowrite_count', iowc, tags=tags)
            self.gauge('system.processes.ioread_bytes', iorb, tags=tags)
            self.gauge('system.processes.iowrite_bytes', iowb, tags=tags)

