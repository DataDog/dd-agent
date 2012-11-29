from checks.jmx_connector import JmxCheck, JMXMetric, convert

class SolrMetric(JMXMetric):
    
    @property
    def metric_name(self):
        if hasattr(self, '_metric_name'):
            return self._metric_name
        name = ['solr', self.domain, self.attribute_name]
        if self.name_suffix is not None:
            name.insert(2, self.name_suffix)
        return convert(".".join(name))

    @property
    def device(self):
        type_tag = self.tags.get('type')
        if type_tag == "searcher":
            return None
            
        return self.tags.get('type')


class Solr(JmxCheck):

    SOLR_DOMAINS = ['solr']

    def check(self, instance):
        (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        dump = jmx.dump()

        domains = Solr.SOLR_DOMAINS + self.init_config.get('domains', [])

        self.get_and_send_jvm_metrics(instance, dump, tags)
        self.create_metrics(instance, self.get_beans(dump, domains, approx=True), SolrMetric, tags=tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()

    @staticmethod
    def parse_agent_config(agentConfig):

        return JmxCheck.parse_agent_config(agentConfig, 'solr')



