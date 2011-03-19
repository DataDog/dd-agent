import os
import re
import time
import datetime
from stat import *
from checks.utils import TailFile
from resources import ResourcePlugin, agg, SnapshotDescriptor, SnapshotField

class RailsLP(ResourcePlugin):

    RESOURCE_KEY = "rails"
    FLUSH_INTERVAL = 1 # in minutes

    INIT = 0
    END  = 1

    # Regexp
    date_format = "%Y-%m-%d %H:%M:%S"
    result_re = re.compile("Completed in (\d+)ms \((.*)\) \| (\d+) (.+) \[(.*)\]")
    init_re = re.compile("Processing (\S+) \(for (\S+) at (\S+ \S+)\) \[(\S+)\]")
    view_re = re.compile(r"View: (\d+)")
    db_re = re.compile(r"DB: (\d+)")

    def __init__(self, logger, agentConfig):
        ResourcePlugin.__init__(self, logger, agentConfig)
        self.context = None
        self.state = self.INIT
        self._max_lines = agentConfig.get('rails_max_lines',None)
        self._line_counter = 0

        self.gens = []
        log_paths = agentConfig.get('rails_logs', None)
        if log_paths is not None:
            for log_path in log_paths.split(','):
                #FIXME, move end = true
                gen = TailFile(logger, log_path, self._parse_line).tail(move_end = False)
                self.gens.append((log_path, gen))

    def describe_snapshot(self):
        return SnapshotDescriptor(1,
            SnapshotField('url','str', aggregator = agg.append, temporal_aggregator = agg.append),
            SnapshotField("action", 'str', aggregator = agg.append, 
                temporal_aggregator = agg.append, group_on = True, temporal_group_on = True),
            SnapshotField("web_time", 'int'),
            SnapshotField("db_time", 'int'),
            SnapshotField("total_time", 'int'),
            # Compute hints/min, sum locally (flush interval is 1 min) 
            SnapshotField("hits", 'int', temporal_aggregator = sum, 
                server_temporal_aggregator = agg.avg))

    @staticmethod
    def _group_by_action(o):
        return o[1]

    @staticmethod
    def _filter_by_usage(o):
        # More than 10ms:
        return o[4] > 10
        
    @staticmethod
    def _string_to_ts(string):
        return datetime.datetime.strptime(string,RailsLP.date_format)

    @staticmethod
    def _dt_to_ts(dt):
        return int(time.mktime(dt.timetuple()))

    def _parse_init(self,line):
        m = self.init_re.match(line)
        if m is not None:
            (action, ip, date, method) = m.groups()
            self.context = {"action": action,
                            "ts": self._string_to_ts(date), 
                            "ip": ip,
                            "method": method}
            self.state = self.END
        
    def _parse_timings(self,timings):
        """ View: 16, DB: 0 """

        m = self.view_re.match(timings)
        view = 0
        if m is not None:
            view = int(m.group(1))

        m = self.db_re.match(timings)
        db = 0
        if m is not None:
            db = int(m.group(1))
       
        return (view, db)

    def _parse_end(self,line):
        m = self.result_re.match(line)
        if m is not None:
            (total_time, timings, ret_code, ret_str, url) = m.groups()
            view_time, db_time = self._parse_timings(timings)

            self.add_to_snapshot([url,
                                  self.context['action'], 
                                  int(view_time), int(db_time), int(total_time), 1], 
                                  ts = self.context['ts'])

            self.state = self.INIT

    def _parse_line(self,line):
        """Returns false to stop iteration, true to go on"""
        if self.state == self.INIT:
            self._parse_init(line)
        else:
            self._parse_end(line)

        if self._max_lines is not None:
            self._line_counter = self._line_counter + 1
            if self._line_counter > self._max_lines:
                self._line_counter = 0
                self.log.debug("Max lines reached")
                return True
        else:
            return False

    def flush_snapshots(self,snapshot_group):
        self._flush_snapshots(snapshot_group = snapshot_group,
                group_by = self._group_by_action,
                filter_by = self._filter_by_usage, temporal = False)

    def check(self):

        # Read until the EOF or until max_lines is reached
        for (log_path, gen) in self.gens:
            try:
                gen.next()
                self.log.debug("Done checking Rails log {0}".format(log_path))
            except StopIteration, e:
                self.log.exception(e)
                self.log.warn("Can't tail file {0}".format(log_path))

if __name__ == "__main__":

    import logging
    import time
    logger = logging.getLogger("rails")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    rlp = RailsLP(logger, { 'rails_logs':'/home/fabrice/dev/datadog/gsr_rails.log',
                            'rails_max_lines': 50,
                             })

    while True:
        rlp.check()
        print rlp.pop_snapshots()
