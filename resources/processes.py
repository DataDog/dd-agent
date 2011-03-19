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
                SnapshotField("user",'str',aggregator=agg.append,temporal_aggregator=agg.append),
                SnapshotField("pct_cpu",'float'),
                SnapshotField("pct_mem",'float'),
                SnapshotField("vsz",'int'),
                SnapshotField("rss",'int'),
                SnapshotField("family",'str',aggregator=None,temporal_aggregator=None,
                    group_on = True, temporal_group_on = True),
                SnapshotField("ps_count",'int'))

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
        return o[5]

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
    from datetime import datetime
    import numpy
    from scipy import stats

    logger = logging.getLogger("processes")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    proc = Processes(logger,{})
   
    times = { 'avro': [],
              'json': [],
              'proto': [],
              'pickle': [] }

    dectimes = { 'avro': [],
                 'json': [],
                 'proto': [],
                 'pickle': [] }


    schema = proc.get_avro_schema()

    for index in xrange(0,1000):
        proc.check()
        proc.flush_snapshots(datetime.now())
        snap = proc.pop_snapshot()[1]
        base_name = 'data/processes-%d' % index

        dt = datetime.now()
        proc.write_avro_file(schema,base_name + '.avro',snap)
        dt2 = datetime.now()
        times['avro'].append((dt2-dt).microseconds)
        dt = datetime.now()
        proc.read_avro_file(base_name + '.avro')
        dt2 = datetime.now()
        dectimes['avro'].append((dt2-dt).microseconds)
        
        dt = datetime.now()
        proc.write_json_file(base_name + '.json',snap)
        dt2 = datetime.now()
        times['json'].append((dt2-dt).microseconds)
        dt = datetime.now()
        proc.read_json_file(base_name + '.json')
        dt2 = datetime.now()
        dectimes['json'].append((dt2-dt).microseconds)

        dt = datetime.now()
        proc.write_proto_file(base_name + '.proto',snap)
        dt2 = datetime.now()
        times['proto'].append((dt2-dt).microseconds)
        dt = datetime.now()
        proc.read_proto_file(base_name + '.proto')
        dt2 = datetime.now()
        dectimes['proto'].append((dt2-dt).microseconds)

        dt = datetime.now()
        proc.write_pickle_file(base_name + '.pickle',snap)
        dt2 = datetime.now()
        times['pickle'].append((dt2-dt).microseconds)
        dt = datetime.now()
        proc.read_pickle_file(base_name + '.pickle')
        dt2 = datetime.now()
        dectimes['pickle'].append((dt2-dt).microseconds)


    #Display stats
    for enc in times:
        print "enc:", enc, "mean:", numpy.mean(times[enc]),"median:", numpy.median(times[enc]),"90%:",stats.scoreatpercentile(times[enc], 90) 
        print "dec:", enc, "mean:", numpy.mean(dectimes[enc]),"median:", numpy.median(dectimes[enc]),"90%:",stats.scoreatpercentile(dectimes[enc], 90) 
