
from datetime import datetime, timedelta
import time
from types import DictType, ListType, StringTypes

from collections import namedtuple


class agg(object):

    @staticmethod
    def avg(args):
        if len(args) > 0:
            return sum(args)/len(args)
        else:
            return 0

    @staticmethod
    def append(args):
        l = []
        for arg in args:
            if isinstance(arg, StringTypes):
                l.extend(arg.split(","))
            else:
                l.append(str(arg))

        return ",".join(list(set(l)))


MetricDescriptor = namedtuple('MetricDescriptor',['version','name','type','aggregator',
        'temporal_aggregator','server_aggregator','server_temporal_aggregator',
        'group_on','temporal_group_on'])
SnapshotDesc = namedtuple('SnapshotDesc',['version','fields'])

def SnapshotField(name,_type,aggregator=sum,temporal_aggregator=agg.avg,
                    server_aggregator=None,server_temporal_aggregator=None,
                    group_on = False, temporal_group_on = False):
    if server_aggregator is None:
        if _type == 'str':
            server_aggregator = agg.append
        else:
            server_aggregator = sum

    if server_temporal_aggregator is None:
        if _type == 'str':
            server_temporal_aggregator = agg.append
        else:
            server_temporal_aggregator = agg.avg

    return MetricDescriptor(2,name,_type,aggregator,temporal_aggregator,
                server_aggregator,server_temporal_aggregator,
                group_on = group_on, temporal_group_on = temporal_group_on)

def SnapshotDescriptor(version,*fields):
    return SnapshotDesc(version, fields)

class ResourcePlugin(object):

    def __init__(self, logger, agentConfig):
        self.log = logger
        self.config = agentConfig
        self._descriptor = None
        self._snapshots = []  # stack with non (temporarly) aggregated snapshots
        self._last_snapshots = None  # last aggregated snapshots
        self._current_snapshot = None  # snapshot being built
        self._current_ts = None
        self._format_described = False  # Do we need to send format description to the intake ?
        self._descriptor = self.describe_snapshot()

    @classmethod
    def get_group_ts(cls,ts):
        """find the aggregation group this timestamp belongs to
            taking into account the flush interval"""
        m = ((ts.minute/cls.FLUSH_INTERVAL) + 1) * cls.FLUSH_INTERVAL
        return ts.replace(microsecond=0,second=0,minute=0) + timedelta(minutes=m)

    @staticmethod
    def _group_by(keys, lines):
        if keys is None:
            return lines

        if not isinstance(keys, ListType):
            keys = [keys]

        group = {}
        key = keys[0]

        for line in lines:
            k = key(line)
            if k in group:
                group[k].append(line)
            else:
                group[k] = [line]

        return group


    def _aggregate_lines(self, lines, temporal = False):

        if len(lines) == 1:
            return lines[0]

        result = []
        i = 0

        for metric in self._descriptor.fields:
            if temporal:
                agg_fun = metric.temporal_aggregator
            else:
                agg_fun = metric.aggregator
            if agg_fun is None:
                result.append(lines[0][i])
            else:
                arglist = []
                for line in lines:
                    arglist.append(line[i])
                try:
                    result.append(agg_fun(arglist))
                except Exception, e:
                    self.log.error("Error aggregating metric: %s" % metric.name)
                    self.log.error("Error while applying %s on %s" % (agg_fun, str(arglist)))
                    raise e

            i = i + 1

        return result

    def _aggregate(self,lines,group_by = None, filter_by = None, temporal = False):

        #group the current snapshot if needed
        if group_by is not None:
            groups = self._group_by(group_by,lines)
        else:
            groups = {'foo': lines}

        #Aggregate each terminal group
        dlist = []

        def _aggregate_groups(groups):
            for group in groups:
                rows = groups[group]
                if isinstance(rows, DictType):
                    _aggregate_groups(rows)
                else:
                    dlist.append(self._aggregate_lines(rows, temporal = temporal))

        _aggregate_groups(groups)

        # Now filter dlist and keep only what is interesting
        if filter_by is None:
            dlist2 = dlist
        else:
            dlist2 = filter(filter_by,dlist)

        return dlist2

    def _flush_snapshots(self,snapshot_group = None, group_by = None, filter_by = None,
                              temporal = True):
        #Aggregate (temporally) all snaphots into last_snapshots

        new_snap = (int(time.mktime(snapshot_group.timetuple())),
                               self._aggregate(self._snapshots,
                                              group_by = group_by,
                                              filter_by = filter_by,
                                              temporal = temporal))
        if self._last_snapshots is None:
            self._last_snapshots = [new_snap]
        else:
            self._last_snapshots.append(new_snap)

        self._snapshots = []


    def _check_current_snapshot(self,now):
        """Check if the current snapshot is complete"""
        if self._current_ts is not None:
            g1 = self.get_group_ts(self._current_ts)
            g2 = self.get_group_ts(now)
            if g1 != g2:
                self.log.debug("Snapshot complete at %s" % g1)
                self.end_snapshot(self._current_ts)
                self.flush_snapshots(g1)
        if self._current_snapshot is None:
            self.start_snapshot()

    def _flush_if_needed(self,now):
        """Check the older snapshot in the stack, and flush
            them all if needed"""
        if self._current_ts is not None:
            g1 = self.get_group_ts(self._current_ts)
            g2 = self.get_group_ts(now)
            self.log.debug("Resources: (%s) group now: %s, group ts: %s" % (self.RESOURCE_KEY,g2,g1))
            if g1 != g2:  # It's time to flush
                self.log.debug("Resources: Flushing %s snapshots" % self.RESOURCE_KEY)
                self.flush_snapshots(g2)
                self._current_ts = None

    #--------------------------------- public API ------------------------------------------

    def get_format_version(self):
        return self._descriptor.version

    def describe_format_if_needed(self):
        if not self._format_described:
            self._format_described = True
            ret = []
            for field in self._descriptor.fields:
                f_agg_name = f_tagg_name = None
                f_serv_agg_name = f_serv_tagg_name = None

                if field.aggregator is not None:
                    f_agg_name = field.aggregator.__name__

                if field.temporal_aggregator is not None:
                    f_tagg_name = field.temporal_aggregator.__name__

                if field.server_aggregator is not None:
                    f_serv_agg_name = field.server_aggregator.__name__

                if field.server_temporal_aggregator is not None:
                    f_serv_tagg_name = field.server_temporal_aggregator.__name__

                ret.append([
                    field.version,
                    field.name,
                    field.type,
                    f_agg_name,
                    f_tagg_name,
                    f_serv_agg_name,
                    f_serv_tagg_name,
                    field.group_on,
                    field.temporal_group_on,
                ])
            return ret

    def describe_snapshot(self):
        """Register the snapshot details for this plugin:
           - What a line is made of
           - How to aggregate it
            Must return a SnapshotDescriptor
        """
        raise Exception("To be implemented in plugin")

    def start_snapshot(self):
        """Start a new snapshot for any timestamp"""
        self._current_snapshot = []

    def add_to_snapshot(self,metric_line,ts = None):
        """2 modes:
            - raw snapshots: do not provide ts
            - incremental snapshots: provide ts, a new snapshot group
              will be created if needed"""
        if ts is None:
            self._current_snapshot.append(metric_line)
        else:
            self._check_current_snapshot(ts)
            self._current_ts = ts
            self._current_snapshot.append(metric_line)

    def end_snapshot(self,ts=None,group_by=None,filter_by=None):
        """End the current snapshot:
            group and aggregate as configured
            ts: a datetime object
        """

        if ts is None:
            now = datetime.now()
        else:
            now = ts

        # We flush before, by checking if the new snapshot
        # is in the same group as the one before and if
        # the flush interval is correct
        self._flush_if_needed(now)

        if self._current_ts is None:
            self._current_ts = now
        if group_by is not None or filter_by is not None:
            self._snapshots.extend(
                self._aggregate(self._current_snapshot,
                                group_by = group_by,
                                filter_by = filter_by,
                                temporal = False))
        else:
            self._snapshots.extend(self._current_snapshot)

        self._current_snapshot = None

    def flush_snapshots(self,snapshot_group):
        raise Exception("To be implemented (by calling _flush_snapshot) in a plugin")

    def check(self):
        raise Exception("To be implemented in a plugin")

    def pop_snapshots(self):
        ret = self._last_snapshots
        self._last_snapshots = None
        return ret
