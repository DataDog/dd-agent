from checks.jmx_connector import JmxCheck, JMXMetric


class TomcatMetric(JMXMetric):

    WHITELIST = {
    "maxThreads" : [{
        'type' : 'ThreadPool',
        'params' : ("tomcat.threads.max", "gauge")
    }],
    "currentThreadCount" : [{
        'type': 'ThreadPool',
        'params' : ("tomcat.threads.count", "gauge")
    }],
    "currentThreadsBusy" : [{
        'type': 'ThreadPool',
        'params' : ("tomcat.threads.busy", "gauge")
    }],
    "bytesSent" : [{
        'type' : 'GlobalRequestProcessor',
        'params' : ("tomcat.bytes_sent", "counter")
    }],
    "bytesReceived" : [{
        'type' : 'GlobalRequestProcessor',
        'params' : ("tomcat.bytes_rcvd", "counter")
    }],
    "processingTime" : [{
        'type' : 'GlobalRequestProcessor',
        'params' : ("tomcat.processing_time", "counter")
    }],
    "errorCount" : [
        {
        'type' : 'GlobalRequestProcessor',
        'params' : ("tomcat.error_count", "counter")
        },
        {
        'j2eeType' : 'Servlet',
        'params' :  ("tomcat.servlet.error_count", "counter")
        }],

    "requestCount" : [{
        'type' : 'GlobalRequestProcessor',
        'params' : ("tomcat.request_count", "counter")
    }],
    "maxTime" : [{
        'type' : 'GlobalRequestProcessor',
        'params' : ("tomcat.max_time", "gauge")
    }],
    
    "accessCount" : [{
        'type' : 'Cache',
        'params': ("tomcat.cache.access_count", "counter")
    }],
    
    "hitsCounts" : [{
        'type' : 'Cache',
        'params' : ("tomcat.cache.hits_count", "counter")
    }],

    "jspCount" : [{
        'type' : 'JspMonitor',
        'params' : ("tomcat.jsp.count", "counter")
    }],
    "jspReloadCount" : [{
        'type' : 'JspMonitor',
        'params' : ("tomcat.jsp.reload_count", "counter")
    }],

    "processingTime" : [{
        'j2eeType' : 'Servlet',
        'params' : ("tomcat.servlet.processing_time", "counter")
    }],

    "requestCount" : [{
        'j2eeType' : 'Servlet',
        'params' : ("tomcat.servlet.request_count", "counter")
    }]

    }

    def get_params(self):
        if TomcatMetric.WHITELIST.has_key(self.attribute_name):
            for dic in TomcatMetric.WHITELIST[self.attribute_name]:
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


class Tomcat(JmxCheck):

    TOMCAT_DOMAINS = ['Catalina']

    def check(self, instance):
        (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        dump = jmx.dump()

        self.get_and_send_jvm_metrics(instance, dump, tags)
        self.create_metrics(instance, self.get_beans(dump, Tomcat.TOMCAT_DOMAINS), TomcatMetric, tags=tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()

    @staticmethod
    def parse_agent_config(agentConfig):

        return JmxCheck.parse_agent_config(agentConfig, 'tomcat')



