import psutil
import os
import threading
from checks import Check, AgentCheck
from config import _is_affirmative

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

    def _psutil_config_to_stats(self):
        process_config = self.init_config.get('process', None)
        assert process_config

        current_process = psutil.Process(os.getpid())
        filtered_methods = [k for k,v in process_config.items() if _is_affirmative(v) and\
                                hasattr(current_process, k)]
        stats = {}

        if filtered_methods:
            for method in filtered_methods:
                method_key = method[4:] if method.startswith('get_') else method
                try:
                    raw_stats = getattr(current_process, method)()
                    try:
                        stats[method_key] = raw_stats._asdict()
                    except AttributeError:
                        if isinstance(raw_stats, int):
                            stats[method_key] = raw_stats
                        else:
                            self.log.warn("Could not serialize output of {} to dict".format(method))

                except psutil.AccessDenied:
                    self.log.warn("Cannot call psutil method {} : Access Denied".format(method))

        return stats

    def _register_psutil_metrics(self):
        '''
        Saves sample metrics from psutil

        self.stats looks like:
        {
         'memory_info': OrderedDict([('rss', 24395776), ('vms', 144666624)]),
         'io_counters': OrderedDict([('read_count', 4536),
                                    ('write_count', 100),
                                    ('read_bytes', 0),
                                    ('write_bytes', 61440)])
         ...
         }

         This creates a metric like `datadog.agent.{key_1}.{key_2}` where key_1 is a top-level
         key in self.stats, and key_2 is a nested key.
         E.g. datadog.agent.memory_info.rss
        '''

        base_metric = 'datadog.agent.{0}.{1}'
        for k, v in self.stats.items():
            if isinstance(v, dict):
                for _k, _v in v.items():
                    full_metric_name = base_metric.format(k, _k)
                    self.gauge(full_metric_name, _v)
            else:
                self.gauge('datadog.agent.{0}'.format(k), v)

    def set_metric_context(self, payload, context):
        self._collector_payload = payload
        self._metric_context = context

    def get_metric_context(self):
        return self._collector_payload, self._metric_context

    def check(self, instance):
        in_developer_mode = self.agentConfig['developer_mode']
        if in_developer_mode:
            self.stats = self._psutil_config_to_stats()
            self._register_psutil_metrics()

        payload, context = self.get_metric_context()
        collection_time = context.get('collection_time', None)
        emit_time = context.get('emit_time', None)
        cpu_time = context.get('cpu_time', None)

        if threading.activeCount() > MAX_THREADS_COUNT:
            self.gauge('datadog.agent.collector.threads.count', threading.activeCount())
            self.log.info("Thread count is high: %d" % threading.activeCount())

        collect_time_exceeds_threshold = collection_time  > MAX_COLLECTION_TIME
        if collection_time is not None and \
                (collect_time_exceeds_threshold or in_developer_mode):

            self.gauge('datadog.agent.collector.collection.time', collection_time)
            if collect_time_exceeds_threshold:
                self.log.info("Collection time (s) is high: %.1f, metrics count: %d, events count: %d"
                                    % (collection_time, len(payload['metrics']), len(payload['events'])))

        emit_time_exceeds_threshold = emit_time > MAX_EMIT_TIME
        if emit_time is not None and \
                (emit_time_exceeds_threshold or in_developer_mode):
            self.gauge('datadog.agent.emitter.emit.time', emit_time)
            if emit_time_exceeds_threshold:
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
