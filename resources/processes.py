

import subprocess
import sys
import traceback

from resources import ResourcePlugin, SnapshotDescriptor, SnapshotField, agg
from collections import namedtuple

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
        # Get output from ps
        try:
            process_exclude_args = self.config.get('exclude_process_args', False)
            if process_exclude_args:
                ps_arg = 'aux'
            else:
                ps_arg = 'auxww'
            ps = subprocess.Popen(['ps', ps_arg], stdout=subprocess.PIPE, close_fds=True).communicate()[0]
        except Exception, e:
            self.log.exception('Cannot get process list')
            return False

        # Split out each process
        processLines = ps.split('\n')

        del processLines[0] # Removes the headers
        processLines.pop() # Removes a trailing empty line

        processes = []

        for line in processLines:
            line = line.split(None, 10)
            processes.append(map(lambda s: s.strip(), line))

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
            try:
                psl = PSLine(*line)
                self.add_to_snapshot([psl.user,
                                      float(psl.pct_cpu),
                                      float(psl.pct_mem),
                                      int(psl.vsz),
                                      int(psl.rss),
                                      _compute_family(psl.command),
                                      1])
            except Exception:
                pass
        self.end_snapshot(group_by= self.group_by_family)

    def flush_snapshots(self,snapshot_group):
        self._flush_snapshots(snapshot_group = snapshot_group,
                              group_by = self.group_by_family,
                              filter_by= self.filter_by_usage)

    def check(self):
        self._parse_proc_list(self._get_proc_list())
