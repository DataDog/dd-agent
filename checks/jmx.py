import time
import re
import pexpect

from checks import Check

class JmxConnector:

    attr_re = re.compile(r"(.*)=(.*);")

    def __init__(self):
        self._jmx = None

    def _wait_prompt(self):
        self._jmx.expect_exact("$>") # got prompt, we can continue

    def connect(self,connection,user=None,passwd=None,timeout = 4):
        self._jmx = pexpect.spawn("java -jar libs/jmxterm-1.0-alpha-4-uber.jar", timeout = timeout)
        self._wait_prompt()
        cnt = "open %s" % connection
        if user is not None:
            cnt = cnt + " -u " + user
        if passwd is not None:
            cnt = cnt + " -p " + passwd
        self._jmx.sendline(cnt)
        self._jmx.expect_exact("#Connection to "+connection+" is opened")
        self._wait_prompt()

    def set_domain(self,domain):
        self._jmx.sendline("domain " + domain)
        self._wait_prompt() 

    def list_beans(self):
        self._jmx.sendline("beans")
        self._wait_prompt()
        return self._jmx.before.replace('\r','').split('\n')

    def get_attribute(self,name,type,attribute,domain = None):
        if name is not None and type is not None:
            cmd = "name=%s,type=%s" % (name,type)
        elif name is None:
            cmd = "type=%s" % type
        else:
            cmd = "name=%s" % name

        if domain is not None:
            self._jmx.sendline("get -d %s -b %s %s" % (domain, cmd, attribute))
        else:
            self._jmx.sendline("get -b %s %s" % (cmd, attribute))

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
        _append_to_metric('jvm.thread_count',self.get_attribute(None,"Threading","ThreadCount"))
        _append_to_metric('jvm.heap_memory',self.get_attribute(None,"Memory","HeapMemoryUsage"))
        _append_to_metric('jvm.non_heap_memory',self.get_attribute(None,"Memory","NonHeapMemoryUsage"))

        return ret


class Jvm(Check):

    def __init__(self, logger):
        Check.__init__(self, logger)
        self.jmx = JmxConnector()

    def _store_metric(self,kind,mname,jvm_name,val):
        name = jvm_name + "." + mname
        if kind == "gauge":
            if not self.is_gauge(name):
                self.gauge(name)
        else:
            if not self.is_counter(name):
                self.counter(name)
        self.save_sample(name,float(val))

    def _check_jvm(self, jvm_name, agentConfig, key_server, key_user, key_passwd):
        connection = agentConfig.get(key_server,None)
        if connection is not None and jvm_name is not None:
            user = agentConfig.get(key_user,None)
            passwd = agentConfig.get(key_passwd,None)
            try:
                self.jmx.connect(connection,user,passwd)
                values = self.jmx.get_jvm_status()
            except Exception, e:
                self.logger.exception('Error while fetching JVM metrics: %s' % e)
                return False

            for key in values:
                self._store_metric("gauge",key,jvm_name,values[key])  

    def check(self, agentConfig):
        self._check_jvm(agentConfig.get('JVMName'),agentConfig,'JVMServer','JVMUser','JVMPassword')
        return self.get_samples()

class Tomcat(Jvm):

    thread_pool_re = re.compile(r".*name=(.*),.*")

    def _get_service_stat(self,name):

        #Thread pool
        self._store_metric("gauge","tomcat.threads.max",name,
            self.jmx.get_attribute(name,"ThreadPool","maxThreads"))
        self._store_metric("gauge","tomcat.threads.count",name,
            self.jmx.get_attribute(name,"ThreadPool","currentThreadCount"))
        self._store_metric("gauge","tomcat.threads.busy",name,
            self.jmx.get_attribute(name,"ThreadPool","currentThreadsBusy"))

        # Global request processor
        self._store_metric("counter","tomcat.bytes_sent",name,
            self.jmx.get_attribute(name,"GlobalRequestProcessor","bytesSent"))
        self._store_metric("counter","tomcat.bytes_rcvd",name,
            self.jmx.get_attribute(name,"GlobalRequestProcessor","bytesReceived"))        
        self._store_metric("counter","tomcat.processing_time",name,
            self.jmx.get_attribute(name,"GlobalRequestProcessor","processingTime"))
        self._store_metric("counter","tomcat.error_count",name,
             self.jmx.get_attribute(name,"GlobalRequestProcessor","errorCount"))
        self._store_metric("counter","tomcat.request_count",name,
            self.jmx.get_attribute(name,"GlobalRequestProcessor","requestCount"))        
        self._store_metric("gauge","tomcat.request_count",name,
            self.jmx.get_attribute(name,"GlobalRequestProcessor","maxTime"))

    def get_stats(self):
        self.jmx.set_domain("Catalina")
        beans = self.jmx.match_beans("type=ThreadPool")
        for bean in beans:
            m = self.thread_pool_re.match(bean)
            if m is not None:
                self._get_service_stat(m.group(1))

    def check(self, agentConfig):

        try:
            self._check_jvm('tomcat',agentConfig,'TomcatServer','TomcatUser','TomcatPassword')
            self.get_stats()
        except Exception, e:
            self.logger.exception('Error while fetching Tomcat metrics: %s' % e)

        return self.get_samples()
        

if __name__ == "__main__":
    
    import logging

    #jvm = Jvm(logging)
    #print jvm.check({'JVMServer': "localhost:8090", 'JVMName': "tomcat"})

    tomcat = Tomcat(logging)
    print tomcat.check({'TomcatServer': 'localhost:8090'})
    print tomcat.check({'TomcatServer': 'localhost:8090'})
