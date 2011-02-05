from collections import namedtuple
import time

MetricDescriptor = namedtuple('MetricDescriptor',['name','aggregator','temporal_aggregator'])

class agg():

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
            if type(arg) == type("") or type(arg) == type(u""):
                l.extend(arg.split(","))
            else:
                l.append(str(arg))

        return ",".join(list(set(l)))


class ResourcePlugin(object):

    def __init__(self):
        self._metrics = []
        self._snapshots = []
        self._current_snapshot = None
        self._current_ts = None
        self.register_metrics()

    @staticmethod
    def _group_by(keys, lines):

        if keys is None:
            return lines

        if type(keys) != type([]):
            keys = [keys]

        group = {}
        key = keys[0]

        for line in lines:
            k = key(line)
            if group.has_key(k):
                group[k].append(line)
            else:
                group[k] = [line]

        #Refine groups if needed
        newkeys = keys[1:]
        if len(newkeys) > 0:
            for k in group:
                lines = group[k]
                group[k] = self._group_by(newkeys,lines)

        return group


    def _aggregate_lines(self, lines, temporal = False):

        if len(lines) == 1:
            return lines[0]

        result = []
        i = 0

        for metric in self._metrics:
            agg_fun = metric.temporal_aggregator if temporal else metric.aggregator
            if agg_fun is None:
                result.append(lines[0][i])
            else:
                arglist = []
                for line in lines:
                    arglist.append(line[i])
                result.append(agg_fun(arglist))

            i = i + 1

        return result

    def _aggregate(self,lines,group_by = None, filter_by = None, temporal = False):

        #group the current snapshot if needed
        if group_by is not None:
            groups = self._group_by(group_by,lines)
        else:
            groups = { 'foo': lines}

        #Aggregate each terminal group
        dlist = []

        def _aggregate_groups(groups):
            for group in groups:
                rows = groups[group]
                if type(rows) == type({}):
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

    def _flush_snapshots(self,group_by = None, filter_by = None):
        #Aggregate (temporally) all snaphots into last_snapshots
        self._last_snapshot = self._aggregate(self._snapshots,
                                              group_by = group_by,
                                              filter_by = filter_by,
                                              temporal = True)

        self._snapshots = []


    def _flush_if_needed(self):
        """Check the older snapshot in the stack, and flush
            them all if needed"""
        if self._current_ts is not None:
            now = int(time.time())
            if (now - self._current_ts) > self.FLUSH_INTERVAL:
                self.flush_snapshot()
                self._current_ts = None

    #----------------- public API ------------------------------------------

    def add_metric(self,name,aggregator=sum,temporal_aggregator=agg.avg):
        self._metrics.append(MetricDescriptor(name,aggregator,temporal_aggregator))

    def register_metrics(self):
        """Register the snapshot details for this plugin:
           - What a line is made of
           - How to aggregate it
        """
        raise Exception("To be implemented in plugin")

    def start_snapshot(self):
        """Start a new snapshot for the current timestamp"""
        self._flush_if_needed()
        self._current_snapshot = []

    def add_to_snapshot(self,metric_line):
        self._current_snapshot.append(metric_line)

    def end_snapshot(self,group_by=None,filter_by=None):
        """End the current snapshot:
            group and aggregate as configured
        """
        if self._current_ts is None:
            self._current_ts = int(time.time())
        self._snapshots.extend(
            self._aggregate(self._current_snapshot, 
                            group_by = group_by,
                            filter_by = filter_by,
                            temporal = False))
        self._flush_if_needed()

    def flush_snapshot(self):
        raise Exception("To be implemented (by calling _flush_snapshot) in a plugin")

    def pop_snapshot(self):
        ret = self._last_snapshot
        self._last_snapshot = None
        return ret
