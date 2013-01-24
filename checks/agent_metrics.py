import threading
from checks import Check


class CollectorMetrics(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('datadog.collector.collection.time')
        self.gauge('datadog.emitter.emit.time')
        self.gauge('datadog.collector.threads.count')

    def check(self, agentConfig, collection_time, emit_time):
        self.save_sample('datadog.collector.threads.count', threading.active_count())
        self.save_sample('datadog.collector.collection.time', collection_time)
        if emit_time is not None:
            self.save_sample('datadog.emitter.emit.time', emit_time)
        return self.get_metrics()


