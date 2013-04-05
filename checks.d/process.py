import sys
import psutil

from checks import AgentCheck
class ProcessCheck(AgentCheck):

    def process_finder(self, exact_match=True, search_string=None):
        """
        Create a set of pids of selected process.
        Search for search_string 
        """
        found_process_list = []
        for proc in psutil.process_iter():
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
        
    def processes_memory(self, pids_list):
        rss = 0
        vms = 0
        for pid in set(pids_list):
            try:
                rss += psutil.Process(pid).get_ext_memory_info()[0]
                vms += psutil.Process(pid).get_ext_memory_info()[1]
            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                pass
        #Return value in Byte
        return (rss, vms)
        
        
    def check(self, instance):
        name = instance.get('name', '')
        exact_match = instance.get('exact_match', True)
        search_string = instance.get('search_string')
        pids_list = self.process_finder(exact_match, search_string)
        self.log.debug('ProcessCheck: process %s analysed' % name)
        self.gauge('system.processes.number', len(pids_list), tags=[name])
        self.gauge('system.processes.mem.rss', self.processes_memory(pids_list)[0], tags=[name])
        self.gauge('system.processes.mem.vms', self.processes_memory(pids_list)[1], tags=[name])

if __name__ == '__main__':
    from pprint import pprint as pp
    check, instances = ProcessCheck.from_yaml('../conf.d/process.yaml.example')
    for instance in instances:
        check.check(instance)
    print 'Metrics:'
    pp(check.get_metrics())
