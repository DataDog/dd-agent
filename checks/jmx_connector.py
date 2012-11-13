import simplejson as json
import os
import re

from checks import AgentCheck

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')

def convert(name):
    """Convert from CamelCase to camel_case"""

    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()

class JmxConnector:
    """Persistent connection to JMX endpoint.
    Uses jmxterm to read from JMX
    """
    def __init__(self, log):
        self._jmx = None
        self.log = log

    def _wait_prompt(self):
        self._jmx.expect_exact("$>") # got prompt, we can continue

    def connected(self):
        return self._jmx is not None and self._jmx.isalive()


    def connect(self, connection, user=None, passwd=None, timeout=10):
        # third party 
        import pexpect
        if self._jmx is not None:
            if self._jmx.isalive():
                self._wait_prompt()
                self._jmx.sendline("close")
                self._wait_prompt()

        if self._jmx is None or not self._jmx.isalive():
            # Figure out which path to the jar, __file__ is jmx.pyc
            pth = os.path.realpath(os.path.join(os.path.abspath(__file__), "..", "libs", "jmxterm-1.0-DATADOG-uber.jar"))
            cmd = "java -jar %s -l %s" % (pth, connection)
            if user is not None and passwd is not None:
                cmd += " -u %s -p %s" % (user, passwd)
            self.log.debug("PATH=%s" % cmd)
            self._jmx = pexpect.spawn(cmd, timeout = timeout)
            self._jmx.delaybeforesend = 0
            self._wait_prompt()

    def dump(self):
        self._jmx.sendline("dump")
        self._wait_prompt()
        content = self._jmx.before.replace('dump','').strip()
        jsonvar = json.loads(content)
        return jsonvar

class JMXMetric:
    def __init__(self, bean_name, attribute_name, attribute_value):
        split = bean_name.split(":")

        self.domain = split[0]
        attr_split = split[1].split(',')
        self.tags = {}
        self.bean_name = bean_name

        for attr in attr_split:
            split = attr.split("=")
            tag_name = split[0].strip()
            tag_value = split[1].strip()

            
            self.tags[tag_name] = tag_value


        self.value = attribute_value
        self.attribute_name = attribute_name

    @property
    def metric_name(self):
        return ".".join(self.domain.split('.')[2:]+[self.attribute_name])

    @property
    def tagslist(self):
        tags = []
        for tag in self.tags.keys():
            tags.append("%s:%s" % (tag, self.tags[tag]))

        return tags

    def convert_name(self):
        self.attribute_name = convert(self.attribute_name)

    def __str__(self):
        return "Domain:{0}, bean_name:{1}, {2}={3} tags={4}".format(self.domain,
            self.bean_name, self.attribute_name, self.value, self.tags)



class MetricList:

    def __init__(self, dump=[], metric_object=JMXMetric):
        self.mlist = []

        for bean_name in dump.keys():
            bean = dump[bean_name]
            for attr in bean:
                val = bean[attr]
                if type(val) == type(1) or type(val) == type(1.1):
                    metric = metric_object(bean_name, attr, val)
                    self.append(metric)

                if type(val) == type({}):
                    for subattr in val.keys():
                        subval = val[subattr]
                        if type(subval) == type(1) or type(subval) == type(1.1):
                            metric = metric_object(bean_name, "%s.%s" % (attr, subattr), subval)
                            self.append(metric)


    def append(self, metric):
        self.mlist.append(metric)

    def get(self, domain=None, attribute_name=None, bean_name=None, tags=None):

        return_list = self.mlist
        if domain is not None:
            return_list = [m for m in return_list if m.domain == domain]

        if attribute_name is not None:
            return_list = [m for m in return_list if m.attribute_name == attribute_name]

        if bean_name is not None:
            return_list = [m for m in return_list if m.bean_name == bean_name]

        if tags is not None:
            for key in tags.keys():
                return_list = [m for m in return_list if m.tags.get(key, None) == tags[key]]

        return return_list

    def __str__(self):
        return [m.__str__() for m in self.mlist].__str__()

    


class JmxCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.jmxs = {}

    def _load_config(self, instance):
        host = instance.get('host')
        port = instance.get('port')
        user = instance.get('user', None)
        password = instance.get('password', None)

        key = (host,port)

        def connect():
            jmx = JmxConnector(self.log)
            jmx.connect("%s:%s" % (host, port), user, password)
            self.jmxs[key] = jmx
            return jmx

        if not self.jmxs.has_key(key):
            jmx = connect()

        else:
            jmx = self.jmxs[key]

        if not jmx.connected():
            jmx = connect()

        return (host, port, user, password, jmx)

    def get_jvm_metrics(self, dump, tags=[]):
        metric_list = MetricList(dump=self.get_beans(dump, domains=["java.lang"]))

        m = metric_list.get(bean_name="java.lang:name=ParNew,type=GarbageCollector",
            attribute_name="CollectionCount")[0]
        self.gauge("jvm.gc.parnew.count", m.value, tags+m.tagslist)

        m = metric_list.get(bean_name="java.lang:name=ParNew,type=GarbageCollector",
            attribute_name="CollectionTime")[0]
        self.gauge("jvm.gc.parnew.time", m.value, tags+m.tagslist)

        m = metric_list.get(bean_name="java.lang:name=ConcurrentMarkSweep,type=GarbageCollector",
            attribute_name="CollectionCount")[0]
        self.gauge("jvm.gc.cms.count", m.value, tags+m.tagslist)

        m = metric_list.get(bean_name="java.lang:name=ConcurrentMarkSweep,type=GarbageCollector",
            attribute_name="CollectionTime")[0]
        self.gauge("jvm.gc.cms.time", m.value, tags+m.tagslist)

        m = metric_list.get(attribute_name="ThreadCount", tags={'type':'Threading'})[0]
        self.gauge("jvm.thread_count", m.value, tags+m.tagslist)

        m = metric_list.get(attribute_name="HeapMemoryUsage.used", tags={'type':'Memory'})[0]
        self.gauge("jvm.heap_memory", m.value, tags+m.tagslist)

        m = metric_list.get(attribute_name="NonHeapMemoryUsage.used", tags={'type':'Memory'})[0]
        self.gauge("jvm.non_heap_memory", m.value, tags+m.tagslist)



    def get_beans(self, dump, domains=None):
        if domains is None:
            return dump
        else:
            return dict((k,dump[k]) for k in [ke for ke in dump.keys() if ke.split(':')[0] in domains] if k in dump)

