import threading
from checks import Check, AgentCheck

MAX_THREADS_COUNT = 50
MAX_COLLECTION_TIME = 30
MAX_EMIT_TIME = 5
MAX_CPU_PCT = 10


class CollectorMetrics(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.logger = logger
        self.gauge('datadog.agent.collector.collection.time')
        self.gauge('datadog.agent.emitter.emit.time')
        self.gauge('datadog.agent.collector.threads.count')
        self.gauge('datadog.agent.collector.cpu.used')

    def check(self, payload, agent_config, collection_time, emit_time, cpu_time=None):

        if threading.activeCount() > MAX_THREADS_COUNT:
            self.save_sample('datadog.agent.collector.threads.count', threading.activeCount())
            self.logger.info("Thread count is high: %d" % threading.activeCount())

        if collection_time > MAX_COLLECTION_TIME:
            self.save_sample('datadog.agent.collector.collection.time', collection_time)
            self.logger.info("Collection time (s) is high: %.1f, metrics count: %d, events count: %d"
                                % (collection_time, len(payload['metrics']), len(payload['events'])))

        if emit_time is not None and emit_time > MAX_EMIT_TIME:
            self.save_sample('datadog.agent.emitter.emit.time', emit_time)
            self.logger.info("Emit time (s) is high: %.1f, metrics count: %d, events count: %d"
                                % (emit_time, len(payload['metrics']), len(payload['events'])))

        if cpu_time is not None:
            try:
                cpu_used_pct = 100.0 * float(cpu_time)/float(collection_time)
                if cpu_used_pct > MAX_CPU_PCT:
                    self.save_sample('datadog.agent.collector.cpu.used', cpu_used_pct)
                    self.logger.info("CPU consumed (%%) is high: %.1f, metrics count: %d, events count: %d"
                                        % (cpu_used_pct, len(payload['metrics']), len(payload['events'])))
            except Exception, e:
                self.logger.debug("Couldn't compute cpu used by collector with values %s %s %s"
                                  % (cpu_time, collection_time, str(e)))

        return self.get_metrics()

class AgentMetrics(AgentCheck):

    def __init__(self, *args, **kwargs):
        AgentCheck.__init__(self, *args, **kwargs)
        self._collector_payload = {}
        self._metric_context = {}

    def set_metric_context(self, payload, context):
        self._collector_payload = payload
        self._metric_context = context

    def get_metric_context(self):
        return self._collector_payload, self._metric_context

    def check(self, instance):
        #check needs payload, collection_time, emit_time and cpu_used_pct
        payload, context = self.get_metric_context()
        collection_time = context.get('collection_time', None)
        emit_time = context.get('emit_time', None)
        cpu_time = context.get('cpu_time', None)

        if threading.activeCount() > MAX_THREADS_COUNT:
            self.gauge('datadog.agent.collector.threads.count', threading.activeCount())
            self.log.info("Thread count is high: %d" % threading.activeCount())

        if collection_time is not None and collection_time > MAX_COLLECTION_TIME:
            self.gauge('datadog.agent.collector.collection.time', collection_time)
            self.log.info("Collection time (s) is high: %.1f, metrics count: %d, events count: %d"
                                % (collection_time, len(payload['metrics']), len(payload['events'])))

        if emit_time is not None and emit_time > MAX_EMIT_TIME:
            self.gauge('datadog.agent.emitter.emit.time', emit_time)
            self.log.info("Emit time (s) is high: %.1f, metrics count: %d, events count: %d"
                                % (emit_time, len(payload['metrics']), len(payload['events'])))

        if cpu_time is not None:
            try:
                cpu_used_pct = 100.0 * float(cpu_time)/float(collection_time)
                if cpu_used_pct > MAX_CPU_PCT:
                    self.gauge('datadog.agent.collector.cpu.used', cpu_used_pct)
                    self.log.info("CPU consumed (%%) is high: %.1f, metrics count: %d, events count: %d"
                                        % (cpu_used_pct, len(payload['metrics']), len(payload['events'])))
            except Exception, e:
                self.log.debug("Couldn't compute cpu used by collector with values %s %s %s"
                                  % (cpu_time, collection_time, str(e)))
