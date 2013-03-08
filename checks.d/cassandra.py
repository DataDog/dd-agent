from checks.jmx_connector import JmxCheck, JMXMetric, convert

class CassandraMetric(JMXMetric):
    

    @property
    def metric_name(self):
        if hasattr(self, '_metric_name'):
            return self._metric_name
        names_list = [self.attribute_name]
        return convert(".".join(self.domain.split('.')[2:]+names_list))

    @property
    def type(self):
        if hasattr(self, '_metric_type'):
            return self._metric_type
        return "gauge"


class Cassandra(JmxCheck):


    def check(self, instance):
        try:
            CASSANDRA_DOMAINS = [c['include']['domain'] for c in self.init_config['conf']]
        except Exception:
            CASSANDRA_DOMAINS = ["org.apache.cassandra.db", 
            "org.apache.cassandra.internal",
            "org.apache.cassandra.net",
            "org.apache.cassandra.request"]
            
        JAVA_DOMAINS = ['java.lang']
        try:
            (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        except Exception, e:
            self.log.critical(str(e))
            return False
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        
        domains = CASSANDRA_DOMAINS + JAVA_DOMAINS + self.init_config.get('domains', [])
        dump = jmx.dump_domains(domains)

        self.get_and_send_jvm_metrics(instance, dump, tags)

        self.create_metrics(instance, self.get_beans(dump, None), CassandraMetric, tags=tags)

        metrics = []
        for m in self.get_jmx_metrics():
            m.filter_tags(values_to_remove=['ColumnFamilies'])
            metrics.append(m)

        self.set_jmx_metrics(metrics)

        self.send_jmx_metrics()
        self.clear_jmx_metrics()
