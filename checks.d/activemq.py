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

    ACTIVEMQ_DOMAINS = ['org.apache.activemq']

    def check(self, instance):
        (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        dump = jmx.dump()

        domains = ActiveMQ.ACTIVEMQ_DOMAINS + self.init_config.get('domains', [])

        self.get_and_send_jvm_metrics(instance, dump, tags)
        self.create_metrics(instance, self.get_beans(dump, domains), ActiveMQMetric, tags=tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()

    @staticmethod
    def parse_agent_config(agentConfig):

        return JmxCheck.parse_agent_config(agentConfig, 'activemq')



