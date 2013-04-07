import psutil
from checks import AgentCheck

class ProcessCheck(AgentCheck):
    
    def find_pids(self, processes, search_string, exact_match=True):
        """
        Create a set of pids of selected processe.
        Search for search_string 
        """
        found_process_list = []
        for proc in processes:
            found = False
            for string in search_string:
                if exact_match:
                     if proc.name == string:
                        found = True
                else:
                    if not found:
                        if string in ' '.join(proc.cmdline):
                            found = True
                if found or string == 'All':
                    found_process_list.append(proc.pid)
            
        return set(found_process_list)
        
    def get_process_memory_size(self, pids):
        rss = 0
        vms = 0
        for pid in set(pids):
            try:
                memory_info = psutil.Process(pid).get_ext_memory_info()
                rss += memory_info[0]
                vms += memory_info[1]
            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                pass
        #Return value in Byte
        return (rss, vms)
        
    def check(self, instance):
        name = instance.get('name', '')
        exact_match = instance.get('exact_match', True)
        search_string = instance.get('search_string')
        processes = psutil.process_iter()
        pids = self.find_pids(processes, search_string, exact_match)
        self.log.debug('ProcessCheck: process %s analysed' % name)
        self.gauge('system.processes.number', len(pids), tags=[name])
        rss, vms = self.get_process_memory_size(pids)
        self.gauge('system.processes.mem.rss', rss, tags=[name])
        self.gauge('system.processes.mem.vms', vms, tags=[name])


if __name__ == '__main__':
    from pprint import pprint as pp
    check, instances = ProcessCheck.from_yaml('../conf.d/process.yaml.example')
    for instance in instances:
        check.check(instance)
    print 'Metrics:'
    pp(check.get_metrics())
