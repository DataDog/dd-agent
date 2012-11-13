from checks.jmx_connector import JmxConnector, JmxCheck, JMXMetric

class CassandraMetric(JMXMetric):
    BLACKLIST = ['pendingTasks', 
    'MinimumCompactionThreshold',
    'RowCacheKeysToSave',
    'MaximumCompactionThreshold',
    'KeyCacheSavePeriodInSeconds',
    'RowCacheSavePeriodInSeconds',
    ]

    @property
    def send_metric(self):
        if self.tags.get('keyspace', "") == "system":
            return False

        if self.attribute_name in CassandraMetric.BLACKLIST:
            return False

        return True

    def filter_tags(self, keys_to_remove=[], values_to_remove=[]):
        for k in keys_to_remove:
            if self.tags.has_key(k):
                del self.tags[k]

        for v in values_to_remove:
            for (key, value) in self.tags.items():
                if v == value:
                    del self.tags[key]



class Cassandra(JmxCheck):

    CASSANDRA_DOMAINS = ['org.apache.cassandra.db',
                        'org.apache.cassandra.internal',
                        'org.apache.cassandra.net',
                        'org.apache.cassandra.request'
                        ]


    def check(self, instance):
        (host, port, user, password, jmx) = self._load_config(instance)
        dump = jmx.dump()

        self.get_jvm_metrics(dump)

        for bean_name in self.get_beans(dump, Cassandra.CASSANDRA_DOMAINS).keys():
            bean = dump[bean_name]
            for attr in bean:
                val = bean[attr]
                if type(val) == type(1) or type(val) == type(1.1):
                    metric = CassandraMetric(bean_name, attr, val)
                    metric.filter_tags(keys_to_remove=['columnfamily'],
                        values_to_remove=['ColumnFamilies'])
                    if metric.send_metric:
                        metric.convert_name()
                        self.gauge(metric.metric_name, metric.value, metric.tagslist)
