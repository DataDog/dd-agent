import random
from resources import ResourcePlugin, agg, SnapshotDescriptor, SnapshotField


class RailsMockup(ResourcePlugin):

    RESOURCE_KEY = "rails"
    FLUSH_INTERVAL = 1 # in minutes

    TIME_THRESHOLD = 20 # time in ms to skip records (everything below is trashed)
    NUMBER_OF_SAMPLE_PER_SNAP = 2000

    def describe_snapshot(self):
        return SnapshotDescriptor(1,
                SnapshotField("url", aggregator = agg.append, temporal_aggregator = agg.append),
                # Grouping is done on action, no need to aggregate
                SnapshotField("action", aggregator = None, temporal_aggregator = None),
                SnapshotField("web_time", temporal_aggregator = sum),
                SnapshotField("db_time", temporal_aggregator = sum),
                SnapshotField("total_time", temporal_aggregator = sum),
                SnapshotField("hits", temporal_aggregator = sum))

    @staticmethod
    def group_by(o):
        return o[1] #Action

    @classmethod
    def filter_by(cls,o):
        return o[2] > cls.TIME_THRESHOLD or o[3] > cls.TIME_THRESHOLD

    def flush_snapshots(self,snapshot_group):
        self._flush_snapshots(group_by = self.group_by, 
                              filter_by = self.filter_by,
                              snapshot_group = snapshot_group)

    def check(self):

        self.start_snapshot()
        for counter in xrange(self.NUMBER_OF_SAMPLE_PER_SNAP):
            #Build URL
            url_depth = random.randint(1,6)
            url = ""
            last = None
            for i in xrange(url_depth):
                last = chr(ord('a') + random.randint(0,25))
                url = url + last + "/"

            #each terminal level is associated to the same action
            action = "Action#" + last

            #random times
            web = random.randint(10,350)
            db = random.randint(10,1550)
            total = web + db

            self.add_to_snapshot([url,action,web,db,total,1])

        self.end_snapshot(group_by = self.group_by)

        

if __name__ == "__main__":

    import logging

    logger = logging.getLogger("mockup_rails")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    rails = RailsMockup(logger,{})
    rails.check()
    print rails._snapshots
    rails.check()
    rails.flush_snapshots()
    print rails.pop_snapshot()
