import sys
from pprint import pprint as pp
import psutil
from checks import AgentCheck
class ProcessCheck(AgentCheck):
    
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
#        self.log.info('ProcessCheck: Agent started')
        
    def process_finder(self, process=None, search_string=None):
        """
        Create a set of pids of selected process.
        Search for search_string and process lists
        """
        counter = 0
        found_process_list = []
        if search_string:
            for proc in psutil.process_iter():
                found = False
                for string in search_string:
                    if not found:
                        if string in ' '.join(proc.cmdline):
                            found = True
                if found:
                    found_process_list.append(proc.pid)
        if process:                
            for proc in psutil.process_iter():
                for current_proc in process:
                    if current_proc == 'All':
                        found_process_list.append(proc.pid)
                    if proc.name == current_proc:
                        found_process_list.append(proc.pid)
                    
        return set(found_process_list)
        
    def processes_memory(self, pids_list):
        rss = 0
        vms = 0
        for pid in set(pids_list):
            try:
                rss += psutil.Process(pid).get_memory_info()[0]
                vms += psutil.Process(pid).get_memory_info()[1]
            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                pass
        #Return value in KB
        return (rss, vms)
        
        
    def check(self, instance):
        name = instance.get('name', '')
        process = instance.get('process')
        if name == 'All':
            process = ['All']
        search_string = instance.get('search_string')
        pids_list = self.process_finder(process, search_string)
        self.log.info('ProcessCheck: process %s analysed' % name)
        self.gauge('system.processes', len(pids_list), tags=[name])
        self.gauge('system.processes.mem.rss', self.processes_memory(pids_list)[0], tags=[name])
        #self.gauge('system.%s.processes.mem.vms', self.processes_memory(pids_list)[1], tags=[name])

if __name__ == '__main__':
    check, instances = ProcessCheck.from_yaml('../conf.d/process.yaml.example')
    for instance in instances:
        check.check(instance)
    print 'Metrics:'
    pp(check.get_metrics())
