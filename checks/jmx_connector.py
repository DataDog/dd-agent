import os
import re
import sys

from checks import AgentCheck
from util import json

import logging
log = logging.getLogger('jmx')

JAVA_CONF = [{'include':
                {'attribute': 
                    {'CollectionCount': 
                        {'alias': 'jvm.gc.cms.count',
                         'metric_type': 'gauge'},
                     'CollectionTime': 
                        {'alias': 'jvm.gc.parnew.time',
                        'metric_type': 'gauge'}},
                'domain': 'java.lang',
                'type': 'GarbageCollector'}
                },
               {'include':
                   {'attribute': 
                    {'HeapMemoryUsage.used':
                        {'alias': 'jvm.heap_memory',
                          'metric_type': 'gauge'},
                     'NonHeapMemoryUsage.used': 
                         {'alias': 'jvm.non_heap_memory',
                         'metric_type': 'gauge'},
                     'ThreadCount': 
                         {'alias': 'jvm.thread_count',
                         'metric_type': 'gauge'}},
                    'domain': 'java.lang'}
    }]

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')
metric_replacement = re.compile(r'([^a-zA-Z0-9_.]+)|(^[^a-zA-Z]+)')
metric_dotunderscore_cleanup = re.compile(r'_*\._*')

DO_NOT_NICE = 0
DEFAULT_PRIORITY = 0
MAX_JMX_RETRIES = 3

def convert(name):
    """Convert from CamelCase to camel_case
    And substitute illegal metric characters
    """

    metric_name = first_cap_re.sub(r'\1_\2', name)
    metric_name = all_cap_re.sub(r'\1_\2', metric_name).lower()
    metric_name = metric_replacement.sub('_', metric_name)
    return metric_dotunderscore_cleanup.sub('.', metric_name).strip('_')


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
        if self._jmx is not None:
            try:
                self._jmx.sendline("bye")
            except BaseException, e:
                pass

            try:
                self._jmx.terminate(force=True)
            except BaseException, e:
                pass

        self._jmx = None

    def connect(self, connection, user=None, passwd=None, timeout=20, priority=DEFAULT_PRIORITY):
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
                # Only use nice is the requested priority warrants it
                if priority == DO_NOT_NICE:
                    cmd = "java -jar %s -l %s" % (pth, connection)
                else:
                    cmd = "nice -n %s java -jar %s -l %s" % (priority, pth, connection)
                if user is not None and passwd is not None:
                    cmd += " -u %s -p %s" % (user, passwd)
                self.log.info("Opening JMX connector with PATH=%s" % cmd)
                self._jmx = pexpect.spawn(cmd, timeout = timeout)
                self._jmx.delaybeforesend = 0
                self._wait_prompt()
        except BaseException, e:
            self.terminate()
            self.log.exception('Error when connecting to JMX Service at address %s. JMX Connector will be relaunched.\n%s' % (connection, str(e)))
            raise Exception('Error when connecting to JMX Service at address %s. JMX Connector will be relaunched.\n%s' % (connection, str(e)))

    def dump_domains(self, domains, values_only=True):
        d = {}
        for domain in domains:
            d.update(self.dump(domain, values_only))
        return d

    def dump(self, domain=None, values_only=True):
        """Returns a dictionnary of all beans and attributes

        If values_only parameter is true, only numeric values will be fetched by 
        the jmx connector.

        If domain is None, all attributes from all domains will be fetched
        
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
        msg = "Dumping"
        if domain is not None:
            msg = "%s domain: %s" % (msg, domain)
        self.log.info(msg)
        
        cmd = "dump"
        if domain is not None:
            cmd = "%s -d %s" % (cmd, domain)
        if values_only:
            cmd = "%s -v true" % cmd
        
        try:
            self._jmx.sendline(cmd)
            self._wait_prompt()
            content = self._jmx.before.replace(cmd,'').strip()
        except BaseException, e:
            self.log.critical("POPEN error while dumping data. \n JMX Connector will be relaunched  \n %s" % str(e))
            self.terminate()
            raise

        try:
            jsonvar = json.loads(content)
        except Exception, e:
            self.log.error("Couldn't decode JSON %s. %s \n JMX Connector will be relaunched" % (str(e), content))
            self.terminate()
            raise

        return jsonvar

class JMXMetric:


    def __init__(self, instance, init_config, bean_name, attribute_name, attribute_value, 
        tags={}, name_suffix=None):
        if name_suffix is not None:
            attribute_name = "%s.%s" % (attribute_name, name_suffix)

        (self.domain, self.tags) = self.get_bean_attr(bean_name) 
        self.tags.update(tags)
        self.value = attribute_value

        self.attribute_name = attribute_name
        self.instance = instance
        self.init_config = init_config or {}
        self.bean_name = bean_name

        self.fields = {
            'attribute': self.attribute_name,
            'attribute_name': self.attribute_name,
            'bean_name': self.bean_name,
            'bean': self.bean_name,
            'domain': self.domain
        }
        for t in self.tags.keys():
            self.fields[t] = self.tags[t]

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
    def tags_list(self):
        tags = []
        for tag in self.tags.keys():
            tags.append("%s:%s" % (tag, self.tags[tag]))

        return tags

    def check_conf(self, include_fields={}, exclude_fields={}):
        include_fields = include_fields.copy()
        attributes = None
        if include_fields.has_key("attribute"):
            attributes = include_fields['attribute']
            del include_fields['attribute']
            attributes_ok = False
        else:
            attributes_ok = True

        include_fields_ok = {}
        for k in include_fields.keys():
            include_fields_ok[k] = False

        exclude_fields_ok = {}
        for k in exclude_fields.keys():
            exclude_fields_ok[k] = True

        if attributes is not None:        
            for attr in attributes:
                if self.attribute_name == attr:
                    if type(attributes) == type({}) and type(attributes[attr]) == type({}):
                        attr = attributes[attr]
                        if attr.has_key('alias'):
                            self._metric_name = attr['alias']
                        if attr.has_key('metric_type'):
                            self._metric_type = attr['metric_type']
                    attributes_ok = True
                    break

        for k in include_fields.keys():
            field = self.fields.get(k, None)
            if field is None:
                include_fields_ok[k] = False

            else:
                if type(include_fields[k]) != type([]):
                    include_fields[k] = [include_fields[k]]
                for value in include_fields[k]:
                    regex = re.compile(r"%s" % value.replace('*', '(.*)'))
                    if regex.match(field) is not None:
                        include_fields_ok[k] = True
                        break

        for k in exclude_fields.keys():
            field = self.fields.get(k, None)
            if field is not None:
                if type(exclude_fields[k]) != type([]):
                    exclude_fields[k] = [exclude_fields[k]]
                for value in exclude_fields[k]:
                    regex = re.compile(r"%s" % value.replace('*', '(.*)'))
                    if regex.match(field) is not None:
                        exclude_fields_ok[k] = False
                        break

        return attributes_ok and False not in exclude_fields_ok.values() and \
            False not in include_fields_ok.values()

    def send_metric(self, conf=None):
        if conf is None:
            default_conf = self.init_config.get('conf', [])
            conf = self.instance.get('conf', default_conf)

        for c in conf:
            if self.check_conf(include_fields=c.get('include', {}), exclude_fields=c.get('exclude', {})):
                return True
        return False
        
    @property
    def metric_name(self):
        if hasattr(self, '_metric_name'):
            return self._metric_name
        name = ['jmx', self.domain, self.attribute_name]
        return ".".join(name)

    @property
    def type(self):
        if hasattr(self, '_metric_type'):
            return self._metric_type

        return "gauge"

    @property
    def device(self):
        return None

    def __str__(self):
        return "Domain:{0},  bean_name:{1}, {2}={3} tags={4}, fields={5}".format(self.domain,
            self.bean_name, self.attribute_name, self.value, self.tags, self.fields)

    def filter_tags(self, keys_to_remove=[], values_to_remove=[]):
        for k in keys_to_remove:
            if self.tags.has_key(k):
                del self.tags[k]

        for v in values_to_remove:
            for (key, value) in self.tags.items():
                if v == value:
                    del self.tags[key]


class JmxCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        
        # Used to store the instances of the jmx connector (1 per instance)
        self.jmxs = {}
        self.jmx_metrics = []
        self.init_config = init_config

        # Used to store the number of times we opened a new jmx connector for this instance
        self.jmx_connections_watcher = {}


    def kill_jmx_connectors(self):
        for key in self.jmxs.keys():
            self.jmxs[key].terminate()

    def _load_config(self, instance):
        host = instance.get('host')
        port = instance.get('port')
        user = instance.get('user', None)
        password = instance.get('password', None)
        instance_name = instance.get('name', "%s-%s-%s" % (self.name, host, port))

        if user is not None and len(user.strip()) == 0:
            user = None
        if password is not None and len(password.strip()) == 0:
            password = None


        key = (host,port)

        def connect():
            if key in self.jmx_connections_watcher:
                self.jmx_connections_watcher[key] += 1
            else:
                self.jmx_connections_watcher[key] = 1

            if self.jmx_connections_watcher[key] > MAX_JMX_RETRIES:
                raise Exception("JMX Connection failed too many times in a row.  Skipping instance name: %s" % instance_name)

            jmx = JmxConnector(self.log)

            priority = int(instance.get('priority', DEFAULT_PRIORITY))
            if priority < 0:
                priority = 0
            jmx.connect("%s:%s" % (host, port), user, password, priority=priority)
            self.jmxs[key] = jmx
            
            # When the connection succeeds we set the counter to a lower value
            # Because it means that the configuration is good
            if jmx.connected():
                self.jmx_connections_watcher[key] = 0

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
            self.get_beans(dump, domains=["java.lang"]), JMXMetric, tags=tags, conf=JAVA_CONF)
        
        self.send_jmx_metrics()
        self.clear_jmx_metrics()

    def create_metrics(self, instance, beans, metric_class, tags={}, conf=None):
        """ Create a list of JMXMetric by filtering them according to the send_metric
        attribute """

        def create_metric(val, name_suffix=None):
            if type(val) == type(1) or type(val) == type(1.1):
                metric = metric_class(instance, self.init_config, bean_name, attr, val, tags=tags, name_suffix=name_suffix)
                if metric.send_metric(conf=conf):
                    self.jmx_metrics.append(metric)
                    
            elif type(val) == type({}):
                for subattr in val.keys():
                    if subattr == 'null':
                        continue
                    subval = val[subattr]
                    create_metric(subval, subattr)

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

        def in_domains(dom, doms, approx):
            if approx:
                return len([d for d in doms if dom in d]) > 0
            else:
                return dom in doms

        if domains is None:
            return dump
        else:
            beans = dict((k,dump[k]) for k in [ke for ke in dump.keys() \
                                                   if in_domains(ke.split(':')[0], domains, approx)] \
                             if k in dump)
            return beans

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
    def parse_agent_config(agentConfig, config_key, init_config=None):
        """ Converts the old style config to the checks.d style"""

        (connections, users, passwords) = JmxCheck._load_old_config(agentConfig, config_key)

        # If there is no old configuration, don't try to run these
        # integrations.
        if not (connections and users and passwords):
            return None

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
        if init_config is not None:
            config['init_config'] = init_config
        return config



