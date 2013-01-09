from checks.jmx_connector import JmxCheck, JMXMetric, convert


class ActiveMQMetric(JMXMetric):

    @property
    def metric_name(self):
        if hasattr(self, '_metric_name'):
            return self._metric_name
        name = ['activemq', self.domain, self.attribute_name]
        return convert(".".join(name))

  
    @property
    def device(self):
        type_tag = self.tags.get('Type')
        if type_tag == "Broker":
            return self.tags.get('BrokerName')

        if type_tag == "Queue":
            return "%s:%s" % (self.tags.get('BrokerName'), self.tags.get('Destination'))

        return None


class ActiveMQ(JmxCheck):

    ACTIVEMQ_DOMAINS = ['org.apache.activemq', 'java.lang']

    def check(self, instance):
        try:
            (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        except Exception, e:
            self.log.critical(str(e))
            raise
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name

        domains = ActiveMQ.ACTIVEMQ_DOMAINS + self.init_config.get('domains', [])
        dump = jmx.dump_domains(domains)

        self.get_and_send_jvm_metrics(instance, dump, tags)
        self.create_metrics(instance, self.get_beans(dump, domains), ActiveMQMetric, tags=tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()

    @staticmethod
    def parse_agent_config(agentConfig):

        return JmxCheck.parse_agent_config(agentConfig, 'activemq', INIT_CONFIG)


INIT_CONFIG = {
'conf': [{'include': {'Type': 'Queue',
'attribute': {'AverageEnqueueTime': {'alias': 'activemq.queue.avg_enqueue_time',
'metric_type': 'gauge'},
'ConsumerCount': {'alias': 'activemq.queue.consumer_count',
'metric_type': 'gauge'},
'DequeueCount': {'alias': 'activemq.queue.dequeue_count',
'metric_type': 'counter'},
'DispatchCount': {'alias': 'activemq.queue.dispatch_count',
'metric_type': 'counter'},
'EnqueueCount': {'alias': 'activemq.queue.enqueue_count',
'metric_type': 'counter'},
'ExpiredCount': {'alias': 'activemq.queue.expired_count',
'type': 'counter'},
'InFlightCount': {'alias': 'activemq.queue.in_flight_count',
'metric_type': 'counter'},
'MaxEnqueueTime': {'alias': 'activemq.queue.max_enqueue_time',
'metric_type': 'gauge'},
'MemoryPercentUsage': {'alias': 'activemq.queue.memory_pct',
'metric_type': 'gauge'},
'MinEnqueueTime': {'alias': 'activemq.queue.min_enqueue_time',
'metric_type': 'gauge'},
'ProducerCount': {'alias': 'activemq.queue.producer_count',
'metric_type': 'gauge'},
'QueueSize': {'alias': 'activemq.queue.size',
'metric_type': 'gauge'}}}},
{'include': {'Type': 'Broker',
'attribute': {'MemoryPercentUsage': {'alias': 'activemq.broker.memory_pct',
'metric_type': 'gauge'},
'StorePercentUsage': {'alias': 'activemq.broker.store_pct',
'metric_type': 'gauge'},
'TempPercentUsage': {'alias': 'activemq.broker.temp_pct',
'metric_type': 'gauge'}}}}]}





