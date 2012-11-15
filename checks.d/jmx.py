from checks.jmx_connector import JmxCheck, JMXMetric
import re
import pdb
metric_replacement = re.compile(r'([^a-zA-Z0-9_.]+)|(^[^a-zA-Z]+)')

class JMXCustomMetric(JMXMetric):

    @property
    def type(self):
        params = self.get_params()

        if params is None or params == "default" or params[0]=="default":
            return "gauge"

        return params[0]

    @property
    def metric_name(self):
        params = self.get_params()

        if params is None or params == "default" or params[1] == "default":
            return "jmx.%s.%s" % (self.domain, self.attribute_name)

        return params[1]

    def get_params(self):
        domains = self.instance.get('domains', None)
        #pdb.set_trace()
        if domains is not None and type(domains) == type([]) and len(domains) > 0:
            for d in domains:
                if self.domain != d.get('name', None):
                    continue

                beans = d.get('beans', None)
                if beans == "all":
                    return "default"

                if beans is not None and type(beans) == type([]) and len(beans) > 0:
                    for b in beans:
                        b_attrs = self.get_bean_attr(b.get('name'))[1]

                        wrong_bean = False
                        for atr in b_attrs.keys():
                            if self.tags.get(atr) != b_attrs[atr]:
                                wrong_bean = True

                        if wrong_bean:
                            continue

                        attributes = b.get('attributes', None)

                        if attributes == "all":
                            return "default"

                        for a in attributes:
                            if self.attribute_name != a.get('name', None):
                                continue

                            return (a.get('type', "default"), a.get('metric_name', "default")) 



        elif domains == "all":
            return "default"

        return None



    @property
    def send_metric(self):
        return self.get_params() is not None



class JMX(JmxCheck):

    def check(self, instance):
        (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        dump = jmx.dump()

        self.get_and_send_jvm_metrics(instance, dump, tags)
        self.create_metrics(instance, self.get_beans(dump), JMXCustomMetric, tags=tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()


    @staticmethod
    def parse_agent_config(agentConfig):

        return JmxCheck.parse_agent_config(agentConfig, 'java')





