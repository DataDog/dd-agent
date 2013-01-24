import threading
from checks import Check
import subprocess


class CollectorMetrics(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('datadog.collector.collection.time')
        self.gauge('datadog.emitter.emit.time')
        self.gauge('datadog.collector.threads.count')
        self.gauge('datadog.collector.cpu.used')

    def check(self, agentConfig, collection_time, emit_time, cpu_time=None):
        self.save_sample('datadog.collector.threads.count', threading.active_count())
        self.save_sample('datadog.collector.collection.time', collection_time)
        if emit_time is not None:
            self.save_sample('datadog.emitter.emit.time', emit_time)
        if cpu_time is not None:
            try:
                self.save_sample('datadog.collector.cpu.used', 100.0 * float(cpu_time)/float(collection_time))
            except Exception, e:
                self.logger.error("Couldn't compute cpu used by collector with values %s %s %s"
                    % (cpu_time, collection_time, str(e)))
        return self.get_metrics()
