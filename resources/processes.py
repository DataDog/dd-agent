from collections import namedtuple
import subprocess
import sys
import traceback
from resources import ResourcePlugin, SnapshotDescriptor, SnapshotField, agg

class Processes(ResourcePlugin):

    RESOURCE_KEY   = "processes"
    FLUSH_INTERVAL = 1 # in minutes

    def describe_snapshot(self):
        return SnapshotDescriptor(1,
                SnapshotField("user",aggregator=agg.append,temporal_aggregator=agg.append),
                SnapshotField("pct_cpu"),
                SnapshotField("pct_mem"),
                SnapshotField("vsz"),
                SnapshotField("rss"),
                SnapshotField("family",aggregator=None,temporal_aggregator=None),
                SnapshotField("ps_count"))

    def _get_proc_list(self):
        self.log.debug('getProcesses: start')
        
        # Get output from ps
        try:
            self.log.debug('getProcesses: attempting Popen')
            
            ps = subprocess.Popen(['ps', 'auxww'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
            
        except Exception, e:
            import traceback
            self.log.error('getProcesses: exception = ' + traceback.format_exc())
            return False
        
        self.log.debug('getProcesses: Popen success, parsing')
        
        # Split out each process
        processLines = ps.split('\n')
        
        del processLines[0] # Removes the headers
        processLines.pop() # Removes a trailing empty line
        
        processes = []
        
        self.log.debug('getProcesses: Popen success, parsing, looping')
        
        for line in processLines:
            line = line.split(None, 10)
            processes.append(map(lambda s: s.strip(), line))
        
        self.log.debug('getProcesses: completed, returning')
        
        return processes 

    @staticmethod
    def group_by_family(o):
        return o[4]

    @staticmethod
    def filter_by_usage(o):
        #keep everything over 1% (cpu or ram)
        return o[0] > 1 or o[1] > 1

    def _parse_proc_list(self,processes):

        def _compute_family(command):
            if command.startswith('['):
                return 'kernel'
            else:
                return (command.split()[0]).split('/')[-1]
        
        PSLine = namedtuple("PSLine","user,pid,pct_cpu,pct_mem,vsz,rss,tty,stat,started,time,command")

        self.start_snapshot()
        for line in processes:
            psl = PSLine(*line)
            self.add_to_snapshot([psl.user,float(psl.pct_cpu),float(psl.pct_mem),int(psl.vsz),
                                int(psl.rss),_compute_family(psl.command),1])
        self.end_snapshot(group_by= self.group_by_family)

    def flush_snapshots(self,snapshot_group):
        self._flush_snapshots(snapshot_group = snapshot_group,
                              group_by = self.group_by_family,
                              filter_by= self.filter_by_usage)

    def check(self):
        self._parse_proc_list(self._get_proc_list())

if __name__ == "__main__":
    
    import logging

    logger = logging.getLogger("processes")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    proc = Processes(logger,{})
    proc.check()
    print proc._snapshots
    print proc._current_ts
    proc.check()
    print proc._current_ts
    print proc._snapshots
    proc.flush_snapshots()
    print "##########################"
    print proc.pop_snapshot()
    print proc._current_ts
