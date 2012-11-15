from checks.jmx_connector import JmxCheck, JMXMetric


class ActiveMQMetric(JMXMetric):

    WHITELIST = {
    'AverageEnqueueTime' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.avg_enqueue_time", "gauge")}],
    'ConsumerCount' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.consumer_count", "gauge")}],
    'ProducerCount' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.producer_count", "gauge")}],
    'MaxEnqueueTime' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.max_enqueue_time", "gauge")}],
    'MinEnqueueTime' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.min_enqueue_time", "gauge")}],
    'MemoryPercentUsage' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.memory_pct", "gauge")},{
        
        'Type' : 'Broker',
        'params' : ("activemq.broker.memory_pct", "gauge")}
        ],
    'QueueSize' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.size", "gauge")}],
    

    'DequeueCount' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.dequeue_count", "counter")}],
    'DispatchCount' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.dispatch_count", "counter")}],
    'EnqueueCount' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.enqueue_count", "counter")}],
    'ExpiredCount' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.expired_count", "counter")}],
    'InFlightCount' : [{
        'Type' : 'Queue',
        'params' : ("activemq.queue.in_flight_count", "counter")}],

    'StorePercentUsage' : [{
        'Type' : 'Broker',
        'params' : ("activemq.broker.store_pct", "gauge")}],
    'TempPercentUsage' : [{
        'Type' : 'Broker',
        'params' : ("activemq.broker.temp_pct", "gauge")}],

    }

 

    def get_params(self):
        if ActiveMQMetric.WHITELIST.has_key(self.attribute_name):
            for dic in ActiveMQMetric.WHITELIST[self.attribute_name]:
                invalid = False
                for key in dic.keys():
                    if key=='params':
                        continue
                    if self.tags.get(key) != dic[key]:
                        invalid = True
                        break
                if not invalid:
                    return dic['params']

        return None


    @property
    def send_metric(self):
        return self.get_params() is not None

    @property
    def metric_name(self):
        return self.get_params()[0]

    @property
    def type(self):
        return self.get_params()[1]


class ActiveMQ(JmxCheck):

    ACTIVEMQ_DOMAINS = ['org.apache.activemq']

    def check(self, instance):
        (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        dump = jmx.dump()

        self.get_and_send_jvm_metrics(instance, dump, tags)
        self.create_metrics(self.get_beans(instance, dump, ActiveMQ.ACTIVEMQ_DOMAINS), ActiveMQMetric, tags=tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()

    @staticmethod
    def parse_agent_config(agentConfig):

        return JmxCheck.parse_agent_config(agentConfig, 'activemq')



