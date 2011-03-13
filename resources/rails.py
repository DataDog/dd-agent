import os
import re
import time
import datetime
from stat import *
from utils import TailFile
from resources import ResourcePlugin, agg, SnapshotDescriptor, SnapshotField

class RailsLP(ResourcePlugin):

    RESOURCE_KEY = "rails"
    FLUSH_INTERVAL = 1 # in minutes

    INIT = 0
    END  = 1

    # Regexp
    date_format = "%Y-%m-%d %H:%M:%S"
    result_re = re.compile("Completed in (\d+)ms \(View\: (\d+), DB: (\d+)\) \| (\d+) (\S+) \[(.*)\]")
    init_re = re.compile("Processing (\S+) \(for (\S+) at (\S+ \S+)\) \[(\S+)\]")

    def __init__(self, logger, agentConfig):
        ResourcePlugin.__init__(logger, agentConfig)
        self.gens = None
        self.resources = None
        self.context = None
        self.state = self.INIT


    def describe_snapshot(self):
        return SnapshotDescriptor(1,
            SnapshotField('url','str', aggregator = agg.append, temporal_aggregator = agg.append)
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
        # FIXME add a way to get a top 10 (or x, but a top)
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
                            "ts": self._dt_to_ts(self._string_to_ts(date)), 
                            "ip": ip,
                            "method": method}
            self.state = self.END
        
    def _parse_end(self,line):
        m = self.result_re.match(line)
        if m is not None:
            (total_time, view_time, db_time, ret_code, ret_str, url) = m.groups()

            self.add_to_snapshot([url,
                                  self.context['action'], 
                                  view_time, db_time, total_time, 1])

            self.state = self.INIT

    def _parse_line(self,line):
        if self.state == self.INIT:
            self._parse_init(line)
        else:
            self._parse_end(line)

    def flush_snapshots(self,snapshot_group):
        self._flush_snapshots(snapshot_group = snapshot_group,
                group_by = self._group_by_action,
                filter_by = self._filter_by_usage)

    def check(self, logger, agentConfig):
        self.logger = logger

        # Init if needed
        if self.gens is None:
            self.gens = []
            log_paths = agentConfig.get('rails_logs', None)
            if log_paths is not None:
                for log_path in log_paths.split(','):
                    #FIXME, move end = true
                    gen = TailFile(logger, log_path, self._parse_line).tail(move_end = False)
                    self.gens.append((log_path, gen))

        
        self.resources = {}

        # Read until the EOF
        self.start_snapshot()
        for (log_path, gen) in self.gens:
            try:
                gen.next()
                self.logger.debug("Done checking Rails log {0}".format(log_path))
            except StopIteration, e:
                self.logger.exception(e)
                self.logger.warn("Can't tail file {0}".format(log_path))

        self.end_snapshot(group_by = self._group_by_action)

if __name__ == "__main__":

    import logging
    import time
    logger = logging.getLogger("rails")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    rlp = RailsLP()

    while True:
        rlp.check(logger, {
            'rails_logs':'/Users/fabrice/dev/datadog/gsr_rails.log'
            })
        time.sleep(1)
