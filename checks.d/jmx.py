from checks.jmx_connector import JmxConnector, JmxCheck


class JMX(JmxCheck):

    def check(self, instance):
        (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        dump = jmx.dump()

        self.get_jvm_metrics(dump, tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()

