from checks import AgentCheck
import time

class ProcessCheck(AgentCheck):

<<<<<<< HEAD
    def get_library_versions(self):
=======
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
        'system.processes.ctx_switches',
        )

    def is_psutil_version_later_than(self, v):
>>>>>>> a0113fd... Change process io counter access denied message from warning to info
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

    def get_process_metrics(self, pids, psutil, cpu_check_interval, extended_metrics=False):
        rss = 0
        vms = 0
        cpu = 0
        thr = 0
        if extended_metrics:
            real = 0
        else:
            real = None
        for pid in set(pids):
            try:
                p = psutil.Process(pid)
                if extended_metrics:
                    mem = p.get_ext_memory_info()
                    real += mem.rss - mem.shared
                else:
                    mem = p.get_memory_info()

                rss += mem.rss
                vms += mem.vms
                thr += p.get_num_threads()
                cpu += p.get_cpu_percent(cpu_check_interval)

<<<<<<< HEAD
=======
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

>>>>>>> a0113fd... Change process io counter access denied message from warning to info
            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                self.warning('Process %s disappeared while scanning' % pid)
                pass

        #Memory values are in Byte
        return (thr, cpu, rss, vms, real)

    def psutil_older_than_0_6_0(self, psutil):
        return psutil.version_info[1] >= 6

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
        thr, cpu, rss, vms, real = self.get_process_metrics(pids, psutil, cpu_check_interval,
            extended_metrics=self.psutil_older_than_0_6_0(psutil))
        self.gauge('system.processes.mem.rss', rss, tags=tags)
        self.gauge('system.processes.mem.vms', vms, tags=tags)
        self.gauge('system.processes.cpu.pct', cpu, tags=tags)
        self.gauge('system.processes.threads', thr, tags=tags)
        if real is not None:
            self.gauge('system.processes.mem.real', real, tags=tags)
