import psutil
from checks import AgentCheck

class ProcessCheck(AgentCheck):
    
    def find_pids(self, processes, search_string, exact_match=True):
        """
        Create a set of pids of selected processes.
        Search for search_string 
        """
        found_process_list = []
        for proc in processes:
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
                            self.log.warning('Process disappeared while scanning')
                            pass
                        except psutil.AccessDenied, e:
                            self.log.error('Access denied to %s process' % string)
                            self.log.error('Error: %s' % e)
                            raise
 
                if found or string == 'All':
                    found_process_list.append(proc.pid)
            
        return set(found_process_list)
        
    def get_process_memory_size(self, pids):
        rss = vms = real = 0
        for pid in set(pids):
            try:
                mem = psutil.Process(pid).get_ext_memory_info()
                rss += mem.rss
                vms += mem.vms
                real += mem.rss - mem.shared
            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                self.log.warning('Process %s disappeared while scanning' % pid)
                pass
        #Return value in Byte
        return (rss, vms, real)
        
    def check(self, instance):
        name = instance.get('name', False)
        if not name:
            raise KeyError('The "name" of process groups is mandatory')
        exact_match = instance.get('exact_match', True)
        search_string = instance.get('search_string', False)
        if not search_string:
            raise KeyError('The "search_string" is mandatory')
        
        processes = psutil.process_iter()
        pids = self.find_pids(processes, search_string, exact_match)
        self.log.debug('ProcessCheck: process %s analysed' % name)
        self.gauge('system.processes.number', len(pids), tags=[name])
        rss, vms, real = self.get_process_memory_size(pids)
        self.gauge('system.processes.mem.rss', rss, tags=[name])
        self.gauge('system.processes.mem.vms', vms, tags=[name])
        self.gauge('system.processes.mem.real', real, tags=[name])


if __name__ == '__main__':
    from pprint import pprint as pp
    check, instances = ProcessCheck.from_yaml('../conf.d/process.yaml.example')
    for instance in instances:
        check.check(instance)
    print 'Metrics:'
    pp(check.get_metrics())
