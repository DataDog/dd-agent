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

    TOMCAT_DOMAINS = ['Catalina', 'java.lang']

    def check(self, instance):
        try:
            (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        except Exception, e:
            self.log.critical(str(e))
            return False
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        

        domains = Tomcat.TOMCAT_DOMAINS + self.init_config.get('domains', [])
        dump = jmx.dump_domains(domains)

        self.get_and_send_jvm_metrics(instance, dump, tags)
        self.create_metrics(instance, self.get_beans(dump, domains), TomcatMetric, tags=tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()


    @staticmethod
    def parse_agent_config(agentConfig):

        return JmxCheck.parse_agent_config(agentConfig, 'tomcat', INIT_CONFIG)



INIT_CONFIG = {'conf': [{'include': {'attribute': {'currentThreadCount': {'alias': 'tomcat.threads.count',
        'metric_type': 'gauge'},
        'currentThreadsBusy': {'alias': 'tomcat.threads.busy',
        'metric_type': 'gauge'},
        'maxThreads': {'alias': 'tomcat.threads.max',
        'metric_type': 'gauge'}},
        'type': 'ThreadPool'}},
        {'include': {'attribute': {'bytesReceived': {'alias': 'tomcat.bytes_rcvd',
        'metric_type': 'counter'},
        'bytesSent': {'alias': 'tomcat.bytes_sent',
        'metric_type': 'counter'},
        'errorCount': {'alias': 'tomcat.error_count',
        'metric_type': 'counter'},
        'maxTime': {'alias': 'tomcat.max_time',
        'metric_type': 'gauge'},
        'processingTime': {'alias': 'tomcat.processing_time',
        'metric_type': 'counter'},
        'requestCount': {'alias': 'tomcat.request_count',
        'metric_type': 'counter'}},
        'type': 'GlobalRequestProcessor'}},
        {'include': {'attribute': {'errorCount': {'alias': 'tomcat.servlet.error_count',
        'metric_type': 'counter'},
        'processingTime': {'alias': 'tomcat.servlet.processing_time',
        'metric_type': 'counter'},
        'requestCount': {'alias': 'tomcat.servlet.request_count',
        'metric_type': 'counter'}},
        'j2eeType': 'Servlet'}},
        {'include': {'accessCount': {'alias': 'tomcat.cache.access_count',
        'metric_type': 'counter'},
        'hitsCounts': {'alias': 'tomcat.cache.hits_count',
        'metric_type': 'counter'},
        'type': 'Cache'}},
        {'include': {'jspCount': {'alias': 'tomcat.jsp.count',
        'metric_type': 'counter'},
        'jspReloadCount': {'alias': 'tomcat.jsp.reload_count',
        'metric_type': 'counter'},
        'type': 'JspMonitor'}}]}