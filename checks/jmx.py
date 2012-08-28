import time
import re
import os
from checks import Check
import sys
from nose.tools import set_trace
import pexpect
class JmxConnector:

    attr_re = re.compile(r"(.*)=(.*);")

    def __init__(self, logger):
        self._jmx = None
        self.logger = logger

    def _wait_prompt(self):
        self._jmx.expect_exact("$>") # got prompt, we can continue

    def connected(self):
        return self._jmx is not None

    def connect(self,connection,user=None,passwd=None,timeout = 15):
        if self._jmx is not None:
            if self._jmx.isalive():
                self._wait_prompt()
                self._jmx.sendline("close")
                self._wait_prompt()

        if self._jmx is None or not self._jmx.isalive():
            #print "connecting"
            # Figure out which path to the jar, __file__ is jmx.pyc
            pth = os.path.realpath(os.path.join(os.path.abspath(__file__), "..", "libs", "jmxterm-1.0-alpha-4-uber.jar"))
            self._jmx = pexpect.spawn("java -jar %s" % pth, timeout = timeout)
            self._jmx.delaybeforesend = 0
            self._wait_prompt()

        cnt = "open %s" % connection
        if user is not None:
            cnt = cnt + " -u " + user
        if passwd is not None:
            cnt = cnt + " -p " + passwd
        self._jmx.sendline(cnt)
        self._jmx.expect_exact("#Connection to "+connection+" is opened")
        self.logger.info("Connection to "+connection+" is opened")
        self._wait_prompt()
        #print "done"

    def set_domain(self,domain):
        #print "set domain"

        # Fix for solr domain which can be either "solr" or "solr/"
        if type(domain)==type([]):
            for dom in domain:
                if dom in self.list_domains():
                    self._jmx.sendline("domain " + dom)
                    break
        else:
            self._jmx.sendline("domain " + domain)
        self._wait_prompt()

    def list_domains(self):
        self._jmx.sendline("domains")
        self._wait_prompt()
        return self._jmx.before.replace('\r','').split('\n')


    def set_bean(self,bean):
        #print "set bean"
        
        # Fix when you want to set a bean fetched by the list_beans() function
        try:
            bean = bean.split(":")[1]
        except Exception:
            pass
        self._jmx.sendline("bean " + bean)
        self._wait_prompt()

    def list_beans(self):
        #print "list beans"
        self._jmx.sendline("beans")
        self._wait_prompt()
        return self._jmx.before.replace('\r','').split('\n')

    def get_attribute(self,attribute,**keywords):
        #print "get attr"
        cmd = None
        domain = keywords.get("domain",None)
        for key in keywords:
            if key != "domain":
                val = key + "=" + keywords[key]
                if cmd is None:
                    cmd = [val]
                else:
                    cmd.append(val)

        if cmd is not None:
            cmd = ",".join(cmd)

        if domain is not None:
            self._jmx.sendline("get -d %s -b %s %s" % (domain, cmd, attribute))
        elif cmd is not None:
            #set_trace()
            self._jmx.sendline("get -b %s %s" % (cmd, attribute))
        else:
            self._jmx.sendline("get %s" % attribute)

        self._jmx.expect("%s = (.*);" % attribute)
        values = self._jmx.match.group(1)
        self._wait_prompt()

        #Check for composite values
        if values is not None:
            v = values.replace('\r','').split('\n')
            if len(v) == 1:
                return values
            else:
                ret = {}
                for item in v:
                    m = self.attr_re.match(item)
                    if m is not None:
                        key, val = m.groups()
                        ret[key.strip()] = val.strip()

                return ret
    
        return None

    def match_beans(self,string):
        #print "match bean"
        beans = self.list_beans()
        matching_beans = []
        for bean in beans:
            if bean.find(string) != -1:
                matching_beans.append(bean) 

        return matching_beans

    # High level JVM memory/thread status
    def get_jvm_status(self):
        ret = {}

        def _append_to_metric(mname,value):
            if type(value) == type(dict()):
                for key in value:
                    ret[mname + '.' + key] = value[key]
            else:
                ret[mname] = value

        self.set_domain("java.lang")
        _append_to_metric('jvm.thread_count',self.get_attribute("ThreadCount",type="Threading"))
        _append_to_metric('jvm.heap_memory',self.get_attribute("HeapMemoryUsage",type="Memory"))
        _append_to_metric('jvm.non_heap_memory',self.get_attribute("NonHeapMemoryUsage",
            type="Memory"))

        return ret


class Jvm(Check):

    def __init__(self, logger):
        Check.__init__(self, logger)
        self.jmx = JmxConnector(logger)

    def _store_metric(self, kind, name, jvm_name, val, tags=None):
        if kind == "gauge":
            if not self.is_gauge(name):
                self.gauge(name)
        else:
            if not self.is_counter(name):
                self.counter(name)
        self.save_sample(name, float(val), tags=tags, device_name=jvm_name)

    def store_attribute(self, kind, mname, jvm_name, attribute, tags=None):
        self._store_metric(kind,mname,jvm_name,
            self.jmx.get_attribute(attribute), tags=tags)

    def _check_jvm(self, jvm_name, agentConfig, config_key):
        """ It allows multiple instances of a same check.
        The datadog.conf file should follow the syntax below:
        'config_key'_jmx_instance_1: user1:password1@server_address1:server_port1:tag1
        'config_key'_jmx_instance_2: user2:password2@server_address2:server_port2:tag2
        'config_key'_jmx_instance_3: server_address3:server_port3:tag3

        Where config_key is the name of the service, (tomcat, activemq, solr, ...)
        """

        # We load the configuration according to the previous config schema
        connections = [agentConfig.get("%s_jmx_server" % config_key, None)]
        users = [agentConfig.get("%s_jmx_user" % config_key, None)]
        passwords = [agentConfig.get("%s_jmx_pass" % config_key, None)]

        # We load the configuration according to the current schema
        def loadConf(index=1):
            instance = agentConfig.get("%s_jmx_instance_%s" % (config_key, index), None)
            if instance:
                if '@' in instance:
                    instance = instance.split('@')
                    auth = instance[0].split(':')
                    users.append(auth[0])
                    passwords.append(auth[1])
                    connections.append(instance[1])
                else:
                    users.append(None)
                    passwords.append(None)
                    connections.append(instance)
                loadConf(index+1)

        loadConf()

        if connections and jvm_name:

            for i in range(len(connections)):
                user = None
                passwd = None
                if connections[i]:
                    connection = connections[i].split(':')
                    user = users[i]
                    passwd = passwords[i]
                    
                    tags = None
                    if len(connection) == 3:
                        tags = ["instance:%s" % connection[2]]
                    connection = "%s:%s" % (connection[0], connection[1])

                    try:
                        self.logger.info("JMX Connection with %s %s %s" % (connection,user,passwd))
                        self.jmx.connect(connection,user,passwd)
                        self.logger.info((self.jmx._jmx.isalive()))
                        if self.jmx.connected():
                            self.logger.info("Connected")
                            values = self.jmx.get_jvm_status()

                            for key in values:
                                self._store_metric("gauge",key,jvm_name,values[key], tags=tags) 
                        else:
                            self.logger.info("Connection to %s %s %s failed" % (connection, user, passwd))
                    except:
                        if(self.jmx._jmx):
                            self.jmx._jmx.kill(0)
                            self.jmx._jmx = None
                            continue
                        self.logger.info('Error while fetching JVM metrics %s' % sys.exc_info()[0])

                    try:
                        self.get_stats(tags)
                    except:
                        if(self.jmx._jmx):
                            self.jmx._jmx.kill(0)
                            self.jmx._jmx = None
                        self.logger.info('Error while fetching %s metrics %s' % (jvm_name, sys.exc_info()[0]))


                        

                    
    def get_stats(self):
        #Should be overwritten by inherited classes
        pass

    def check(self, agentConfig):
        self._check_jvm(agentConfig.get('jvm_jmx_name'),agentConfig,'jvm')
        return self.get_samples()

class Tomcat(Jvm):

    thread_pool_re = re.compile(r".*name=(.*),.*")
    cache_re = re.compile(r".*host=(.*),path=(.*),type=Cache")
    jsp_re = re.compile(r".*J2EEApplication=(.*),J2EEServer=(.*),WebModule=(.*),name=jsp,type=JspMonitor")
    servlet_re = re.compile(r".*J2EEApplication=(.*),J2EEServer=(.*),WebModule=(.*),j2eeType=Servlet,name=(.*)")

    def _get_service_stat(self, name, tags=None):

        #Thread pool
        self.jmx.set_bean("name=%s,type=ThreadPool" % name)
        self.store_attribute("gauge","tomcat.threads.max",name,"maxThreads", tags=tags)
        self.store_attribute("gauge","tomcat.threads.count",name,"currentThreadCount", tags=tags)
        self.store_attribute("gauge","tomcat.threads.busy",name,"currentThreadsBusy", tags=tags)

        # Global request processor
        self.jmx.set_bean("name=%s,type=GlobalRequestProcessor" % name)
        self.store_attribute("counter","tomcat.bytes_sent",name,"bytesSent", tags=tags)
        self.store_attribute("counter","tomcat.bytes_rcvd",name,"bytesReceived", tags=tags)
        self.store_attribute("counter","tomcat.processing_time",name,"processingTime", tags=tags)
        self.store_attribute("counter","tomcat.error_count",name,"errorCount", tags=tags)
        self.store_attribute("counter","tomcat.request_count",name,"requestCount", tags=tags)
        self.store_attribute("gauge","tomcat.max_time",name,"maxTime", tags=tags)

    def _get_cache_data(self, tags=None):

        beans = self.jmx.match_beans("type=Cache")
        for bean in beans:
            m = self.cache_re.match(bean)
            if m is not None:
                self.jmx.set_bean(bean)
                host, path = m.groups()
                name = host + ":" + path
                self.store_attribute("counter","tomcat.cache.access_count",name,"accessCount", tags=tags)
                self.store_attribute("counter","tomcat.cache.hits_count",name,"hitsCount", tags=tags)

    def _get_jsp_data(self, tags=None):

        beans = self.jmx.match_beans("name=jsp,type=JspMonitor")
        for bean in beans:
            m = self.jsp_re.match(bean)
            if m is not None:
                self.jmx.set_bean(bean)
                module, app, server = m.groups()
                name = app + ":" + server + ":" + module
                self.store_attribute("counter","tomcat.jsp.count",name,"jspCount", tags=tags)
                self.store_attribute("counter","tomcat.jsp.reload_count",name,"jspReloadCount", tags=tags)

    def _get_servlet_data(self, tags=None):

        beans = self.jmx.match_beans("j2eeType=Servlet")
        for bean in beans:
            m = self.servlet_re.match(bean)
            if m is not None:
                self.jmx.set_bean(bean)
                app, server, module, app_name = m.groups()
                name = app + ":" + server + ":" + module + ":" + app_name
                self.store_attribute("counter","tomcat.servlet.error_count",name,"errorCount", tags=tags)
                self.store_attribute("counter","tomcat.servlet.processing_time",name,"processingTime", tags=tags)
                self.store_attribute("counter","tomcat.servlet.request_count",name,"requestCount", tags=tags)

    def get_stats(self, tags=None):        
        self.jmx.set_domain("Catalina")

        beans = self.jmx.match_beans("type=ThreadPool")
        for bean in beans:
            m = self.thread_pool_re.match(bean)
            if m is not None:
                self._get_service_stat(m.group(1), tags=tags)

        self._get_cache_data(tags)
        self._get_jsp_data(tags)
        self._get_servlet_data(tags)

    def check(self, agentConfig):

        try:
            self._check_jvm('tomcat', agentConfig, 'tomcat')
        except Exception, e:
            self.logger.exception('Error while fetching Tomcat metrics: %s' % e)

        return self.get_metrics()
        

class ActiveMQ(Jvm):

    queue_re = re.compile(r"org.apache.activemq:BrokerName=(.*),Destination=(.*),Type=Queue")
    broker_re = re.compile(r"org.apache.activemq:BrokerName=(.*),Type=Broker")

    def _get_queue_stat(self, bean, broker, queue, tags=None):
        self.jmx.set_bean(bean)
        name = "%s:%s" % (broker, queue)
        #gauge
        self.store_attribute("gauge","activemq.queue.avg_enqueue_time",name,"AverageEnqueueTime", tags=tags)
        self.store_attribute("gauge","activemq.queue.consumer_count",name,"ConsumerCount", tags=tags)
        self.store_attribute("gauge","activemq.queue.producer_count",name,"ProducerCount", tags=tags)
        self.store_attribute("gauge","activemq.queue.max_enqueue_time",name,"MaxEnqueueTime", tags=tags)
        self.store_attribute("gauge","activemq.queue.min_enqueue_time",name,"MinEnqueueTime", tags=tags)
        self.store_attribute("gauge","activemq.queue.memory_pct",name,"MemoryPercentUsage", tags=tags)
        self.store_attribute("gauge","activemq.queue.size",name,"QueueSize", tags=tags)

        #counter
        self.store_attribute("counter","activemq.queue.dequeue_count",name,"DequeueCount", tags=tags)
        self.store_attribute("counter","activemq.queue.dispatch_count",name,"DispatchCount", tags=tags)
        self.store_attribute("counter","activemq.queue.enqueue_count",name,"EnqueueCount", tags=tags)
        self.store_attribute("counter","activemq.queue.expired_count",name,"ExpiredCount", tags=tags)
        self.store_attribute("counter","activemq.queue.in_flight_count",name,"InFlightCount", tags=tags)

    def _get_broker_stats(self ,bean, broker, tags=None):
        
        self.jmx.set_bean(bean)

        self.store_attribute("gauge","activemq.broker.store_pct",broker,"StorePercentUsage", tags=tags)
        self.store_attribute("gauge","activemq.broker.memory_pct",broker,"MemoryPercentUsage", tags=tags)
        self.store_attribute("gauge","activemq.broker.temp_pct",broker,"TempPercentUsage", tags=tags)

    def get_stats(self, tags=None):
        self.jmx.set_domain("org.apache.activemq")

        beans = self.jmx.match_beans("Type=Broker")
        for bean in beans:
            m = self.broker_re.match(bean)
            if m is not None:
                self._get_broker_stats(bean, m.group(1), tags=tags)

        beans = self.jmx.match_beans("Type=Queue")
        for bean in beans:
            m = self.queue_re.match(bean)
            if m is not None:
                broker, queue = m.groups()
                self._get_queue_stat(bean, broker, queue, tags=tags)

    def check(self, agentConfig):

        try:
            self._check_jvm('activemq',agentConfig,'activemq')
        except Exception, e:
            self.logger.exception('Error while fetching ActiveMQ metrics: %s' % e)

        return self.get_metrics()


class Solr(Jvm):

    _name_re = re.compile(r".*,type=(.*)")

    def _lru_cache_stat(self,bean, tags=None):

        m = self._name_re.match(bean)
        if m is not None:
            name = m.group(1)
            self.jmx.set_bean(bean)
            self.store_attribute("counter","solr.cache.lookups",name,"cumulative_lookups", tags=tags)
            self.store_attribute("counter","solr.cache.hits",name,"cumulative_hits", tags=tags)
            self.store_attribute("counter","solr.cache.inserts",name,"cumulative_inserts", tags=tags)
            self.store_attribute("counter","solr.cache.evictions",name,"cumulative_evictions", tags=tags)
 
    def _searcher_stat(self,bean, tags=None):
        self.jmx.set_bean(bean)
        self.store_attribute("gauge","solr.searcher.maxdoc",None,"maxDoc", tags=tags)
        self.store_attribute("gauge","solr.searcher.numdocs",None,"numDocs", tags=tags)
        self.store_attribute("gauge","solr.searcher.warmup",None,"warmupTime", tags=tags)

    def _get_search_handler_stats(self, bean, tags=None):
        m = self._name_re.match(bean)
        if m is not None:
            name = m.group(1)
            self.jmx.set_bean(bean)
            self.store_attribute("gauge","solr.search_handler.avg_requests_per_sec",
                    name,"avgRequestsPerSecond", tags=tags)
            self.store_attribute("gauge","solr.search_handler.avg_time_per_req",
                    name,"avgTimePerRequest", tags=tags)

            self.store_attribute("counter","solr.search_handler.errors",name,"errors", tags=tags)
            self.store_attribute("counter","solr.search_handler.requests",name,"requests", tags=tags)
            self.store_attribute("counter","solr.search_handler.timeouts",name,"timeouts", tags=tags)
            self.store_attribute("counter","solr.search_handler.time",name,"totalTime", tags=tags)

    def get_stats(self, tags=None):
        
        # The solr domain depends on the version
        self.jmx.set_domain(["solr","solr/"])

        beans = self.jmx.match_beans("type=searcher")
        if len(beans) > 0:
            self._searcher_stat(beans[0], tags=tags)

        beans = self.jmx.match_beans("id=org.apache.solr.search.FastLRUCache")
        for bean in beans:
            self._lru_cache_stat(bean, tags=tags)

        beans = self.jmx.match_beans("id=org.apache.solr.search.LRUCache")
        for bean in beans:
            self._lru_cache_stat(bean, tags=tags)

        beans = self.jmx.match_beans("id=org.apache.solr.handler.component.SearchHandler")
        #print beans
        for bean in beans:
            self._get_search_handler_stats(bean, tags=tags)

    def check(self, agentConfig):

        try:
            self._check_jvm('solr',agentConfig,'solr')
        except Exception, e:
            self.logger.exception('Error while fetching Solr metrics: %s' % e)

        return self.get_metrics()

def testprofiling():
    import logging
    tomcat = Tomcat(logging)
    print tomcat.check({'tomcat_jmx_instance_1': 'localhost:8090:moncat'})



if __name__ == "__main__":
    
    import logging

    #jvm = Jvm(logging)
    #print jvm.check({'jvm_jmx_server': "localhost:8090", 'jvm_jmx_name': "tomcat"})

    #tomcat = Tomcat(logging)
    #print tomcat.check({'tomcat_jmx_instance_1': 'localhost:8090:moncat'})

    #a = ActiveMQ(logging)
    #print a.check({'activemq_jmx_server': '4934'})
    #print a.check({'activemq_jmx_server': '4934'})

    #s = Solr(logging)
    #print s.check({'solr_jmx_server': '6975'})
    #print s.check({'solr_jmx_server': '6975'})
