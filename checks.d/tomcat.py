from checks.jmx_connector import JmxCheck, JMXMetric, convert


class TomcatMetric(JMXMetric):

    @property
    def device(self):
        type_tag = self.tags.get('type')

        if type_tag == "ThreadPool" or type_tag == "GlobalRequestProcessor":
            return self.tags.get('name')

        if type_tag == "Cache":
            device = "%s:%s" % (self.tags.get('host'), self.tags.get('context'))
            return device

        if type_tag == "JspMonitor":
            device = "%s:%s:%s" % (self.tags.get('J2EEApplication'),
                self.tags.get('J2EEServer'), self.tags.get('WebModule'))
            return device

        if self.tags.get('j2eeType') == "Servlet":
            device = "%s:%s:%s:%s" % (self.tags.get('J2EEApplication'),
                self.tags.get('J2EEServer'), self.tags.get('WebModule'),
                    self.tags.get('name'))

        return None


    @property
    def metric_name(self):
        if hasattr(self, '_metric_name'):
            return self._metric_name
        name = ['tomcat', self.domain, self.attribute_name]
        return convert(".".join(name))




class Tomcat(JmxCheck):

    TOMCAT_DOMAINS = ['Catalina']

    def check(self, instance):
        (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        dump = jmx.dump()

        domains = Tomcat.TOMCAT_DOMAINS + self.init_config.get('domains', [])

        self.get_and_send_jvm_metrics(instance, dump, tags)
        self.create_metrics(instance, self.get_beans(dump, domains), TomcatMetric, tags=tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()

    @staticmethod
    def parse_agent_config(agentConfig):

        return JmxCheck.parse_agent_config(agentConfig, 'tomcat')



