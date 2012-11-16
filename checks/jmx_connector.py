# Import json for the agent. Try simplejson first, then the stdlib version and
# if all else fails, use minjson which we bundle with the agent.
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        import minjson
        class json(object):
            @staticmethod
            def dumps(data):
                return minjson.write(data)

            @staticmethod
            def loads(data):
                return minjson.safeRead(data)


import os
import re
import sys

from checks import AgentCheck


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

    def terminate(self):
        self._jmx.sendline("bye")
        self._jmx.terminate(force=True)



    def connect(self, connection, user=None, passwd=None, timeout=20):
        import pexpect
        from pexpect import ExceptionPexpect

        try:
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
        except:
            if self._jmx:
                try:
                    self._jmx.terminate(force=True)
                except ExceptionPexpect:
                    self.log.error("Cannot terminate process %s" % self._jmx)
            self._jmx = None
            self.log.info('Error while fetching JVM metrics %s' % sys.exc_info()[0])
            raise Exception('Error while fetching JVM metrics at attdress: %s:%s' % (connection, passwd))

    def dump(self):
        """Returns a dictionnary of all beans and attributes
        
        keys are bean's names
        values are bean's attributes in json format

        ex: 

        {"org.apache.cassandra.db:instance=1826959904,type=DynamicEndpointSnitch":
            {"UpdateInterval":100,
            "Scores":{},
            "SubsnitchClassName":"org.apache.cassandra.locator.SimpleSnitch",
            "BadnessThreshold":0.1,
            "ResetInterval":600000},
        "org.apache.cassandra.db:columnfamily=NodeIdInfo,keyspace=system,type=ColumnFamilies":
            {"LiveSSTableCount":0,
            "LiveDiskSpaceUsed":0,
            "MinimumCompactionThreshold":4,
            "WriteCount":0,
            "RowCacheKeysToSave":2147483647,
            "RecentWriteLatencyHistogramMicros":[0,0,0,0,0,0,0,0,0,0]}
        }

        """

        self._jmx.sendline("dump")
        self._wait_prompt()
        content = self._jmx.before.replace('dump','').strip()
        jsonvar = json.loads(content)
        return jsonvar

class JMXMetric:
    WHITELIST = {
        'CollectionCount' : {
            'java.lang:name=ConcurrentMarkSweep,type=GarbageCollector' : ('jvm.gc.cms.count', 'gauge'),
            'java.lang:name=ParNew,type=GarbageCollector' : ('jvm.gc.parnew.count', 'gauge')
            },
        'CollectionTime' : {
            "java.lang:name=ParNew,type=GarbageCollector" : ("jvm.gc.parnew.time", "gauge"),
            "java.lang:name=ConcurrentMarkSweep,type=GarbageCollector" : ("jvm.gc.cms.time", "gauge")
            },

        'ThreadCount' : ('jvm.thread_count', 'gauge'),
        'HeapMemoryUsage.used' : ("jvm.heap_memory", 'gauge'),
        'NonHeapMemoryUsage.used' : ("jvm.non_heap_memory", 'gauge')

    }


    
    def __init__(self, instance, bean_name, attribute_name, attribute_value, 
        tags={}):

        (self.domain, self.tags) = self.get_bean_attr(bean_name) 
        self.tags.update(tags)
        self.value = attribute_value
        self.attribute_name = attribute_name
        self.instance = instance
        self.bean_name = bean_name

    def get_bean_attr(self, bean_name):
        split = bean_name.split(":")
        domain = split[0]
        attr_split = split[1].split(',')
        tags = {}

        for attr in attr_split:
            split = attr.split("=")
            tag_name = split[0].strip()
            tag_value = split[1].strip()
            tags[tag_name] = tag_value

        return (domain, tags)


    @property
    def send_metric(self):
        """
        return a boolean that shows if the metric should be posted or not
        """
        if JMXMetric.WHITELIST.has_key(self.attribute_name):
            params = JMXMetric.WHITELIST[self.attribute_name]
            if type(params) == type({}):
                if params.has_key(self.bean_name):
                    return True
            if type(params) == type(()):
                return True
        return False

    @property
    def metric_name(self):
        params = JMXMetric.WHITELIST[self.attribute_name]
        if type(params) == type({}):
            return params[self.bean_name][0]
        else:
            return params[0]

    @property
    def type(self):
        params = JMXMetric.WHITELIST[self.attribute_name]
        if type(params) == type({}):
            return params[self.bean_name][1]
        else:
            return params[1]

    @property
    def device(self):
        return None



    @property
    def tags_list(self):
        tags = []
        for tag in self.tags.keys():
            tags.append("%s:%s" % (tag, self.tags[tag]))

        return tags


    def filter_tags(self, keys_to_remove=[], values_to_remove=[]):
        for k in keys_to_remove:
            if self.tags.has_key(k):
                del self.tags[k]

        for v in values_to_remove:
            for (key, value) in self.tags.items():
                if v == value:
                    del self.tags[key]

    def __str__(self):
        return "Domain:{0},  bean_name:{1}, {2}={3} tags={4}".format(self.domain,
            self.bean_name, self.attribute_name, self.value, self.tags)

class JmxCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        
        # Used to store the instances of the jmx connector (1 per instance)
        self.jmxs = {}
        self.jmx_metrics = []

    def kill_jmx_connectors(self):
        for key in self.jmxs.keys():
            self.jmxs[key].terminate()

    def _load_config(self, instance):
        host = instance.get('host')
        port = instance.get('port')
        user = instance.get('user', None)
        password = instance.get('password', None)
        instance_name = instance.get('name', "%s-%s-%s" % (self.name, host, port))

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

        return (host, port, user, password, jmx, instance_name)

    def get_and_send_jvm_metrics(self, instance, dump, tags=[]):
        self.create_metrics(instance, 
            self.get_beans(dump, domains=["java.lang"]), JMXMetric, tags=tags)
        
        self.send_jmx_metrics()
        self.clear_jmx_metrics()



    def create_metrics(self, instance, beans, metric_class, tags={}):
        """ Create a list of JMXMetric by filtering them according to the send_metric
        attribute """

        def create_metric(val):
            if type(val) == type(1) or type(val) == type(1.1):
                metric = metric_class(instance, bean_name, attr, val, tags=tags)
                if metric.send_metric:
                    self.jmx_metrics.append(metric)
                    
            elif type(val) == type({}):
                for subattr in val.keys():
                    subval = val[subattr]
                    create_metric(subval)

            elif type(val) == type("") and val != "NaN":
                # This is a workaround for solr as every attribute is a string...
                try:
                    val = float(val)
                    create_metric(val)
                except ValueError:
                    pass



        for bean_name in beans.keys():
            bean = beans[bean_name]
            for attr in bean:
                val = bean[attr]
                create_metric(val)

    def get_jmx_metrics(self):
        return self.jmx_metrics

    def set_jmx_metrics(self, metrics):
        self.jmx_metrics = metrics

    def clear_jmx_metrics(self):
        self.jmx_metrics = []

    def send_jmx_metrics(self):
        """Actually call the self.gauge and self.rate method that will store
        the metrics in the payload"""

        for metric in self.jmx_metrics:
            device_name = metric.device or self.name.lower()
            if metric.type == "gauge":
                self.gauge(metric.metric_name, metric.value, metric.tags_list, 
                    device_name=device_name)
            else:
                self.rate(metric.metric_name, metric.value, metric.tags_list, 
                    device_name=device_name)

    def get_beans(self, dump, domains=None, approx=False):
        """Returns a dictionnary whose keys are beans names
        and values are json dump of the bean's attributes

        Approx allows to do approximate research on the domain name (used by solr)
        ex: Solr domains can be : 
            - solr
            - solr/
            - solr/aaa
            - ...


        """

        def in_domains(domain):
            if domain in domains:
                return True
            if approx:
                for d in domains:
                    regex = re.compile(r"(.*)%s(\.*)" % d)
                    m = regex.match(domain)
                    if m is not None:
                        return True
            return False

        if domains is None:
            return dump
        else:
            return dict((k,dump[k]) for k in [ke for ke in dump.keys() if in_domains(ke.split(':')[0])] if k in dump)

    @staticmethod
    def _load_old_config(agentConfig, config_key):
        """ Load the configuration according to the previous syntax in datadog.conf"""

        connections = []
        users = []
        passwords = []
        # We load the configuration according to the previous config schema
        server = agentConfig.get("%s_jmx_server" % config_key, None)
        user = agentConfig.get("%s_jmx_user" % config_key, None)
        passw = agentConfig.get("%s_jmx_pass" % config_key, None)

        if server is not None:
            connections.append(server)
            users.append(user)
            passwords.append(passw)

        # We load the configuration according to the current schema
        def load_conf(index=1):
            instance = agentConfig.get("%s_jmx_instance_%s" % (config_key, index), None)
            if instance:
                if '@' in instance:
                    instance = instance.split('@')
                    auth = "@".join(instance[0:-1]).split(':')
                    users.append(auth[0])
                    passwords.append(auth[1])
                    connections.append(instance[-1])
                else:
                    users.append(None)
                    passwords.append(None)
                    connections.append(instance)
                load_conf(index+1)

        load_conf()
        return (connections, users, passwords)

    @staticmethod
    def parse_agent_config(agentConfig, config_key):
        """ Converts the old style config to the checks.d style"""

        (connections, users, passwords) = JmxCheck._load_old_config(agentConfig, config_key)
        config = {}
        instances = []
        for i in range(len(connections)):
            connect = connections[i].split(':')
            instance = {
                'host':connect[0],
                'port':connect[1],
                'user':users[i],
                'password':passwords[i]
            }
            if len(connect) == 3:
                instance['name'] = connect[2]
            instances.append(instance)
        config['instances'] = instances
        return config



