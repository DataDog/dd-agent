"""
Module that tries to migrate old style configuration to checks.d interface
for checks that don't support old style configuration anymore

It also comments out related lines in datadog.conf.
Point of entry is: migrate_old_style_configuration at the bottom of the file
which is called when the checks.d directory is loaded when Agent starts.

"""

# std
import os.path
import logging
import string

# project
from util import yDumper

# 3rd party
import yaml

log = logging.getLogger(__name__)

CASSANDRA_CONFIG = {
'init_config': {'conf': [{'exclude': {'attribute': ['MinimumCompactionThreshold', 
'MaximumCompactionThreshold',
'RowCacheKeysToSave',
'KeyCacheSavePeriodInSeconds',
'RowCacheSavePeriodInSeconds',
'PendingTasks',
'Scores',
'RpcTimeout'],
'keyspace': 'system'},
'include': {'attribute': ['BloomFilterDiskSpaceUsed',
'BloomFilterFalsePositives',
'BloomFilterFalseRatio',
'Capacity',
'CompressionRatio',
'CompletedTasks',
'ExceptionCount',
'Hits',
'RecentHitRate',
'LiveDiskSpaceUsed',
'LiveSSTableCount',
'Load',
'MaxRowSize',
'MeanRowSize',
'MemtableColumnsCount',
'MemtableDataSize',
'MemtableSwitchCount',
'MinRowSize',
'ReadCount',
'Requests',
'Size',
'TotalDiskSpaceUsed',
'TotalReadLatencyMicros',
'TotalWriteLatencyMicros',
'UpdateInterval',
'WriteCount',
'PendingTasks'],
'domain': 'org.apache.cassandra.db'}},
{'include': {'attribute': ['ActiveCount',
'CompletedTasks',
'CurrentlyBlockedTasks',
'TotalBlockedTasks'],
'domain': 'org.apache.cassandra.internal'}},
{'include': {'attribute': ['TotalTimeouts'],
           'domain': 'org.apache.cassandra.net'}}]},
 'instances': [{'host': 'localhost', 'port': 7199}]
 }

CASSANDRA_MAPPING = { 
	'cassandra_host': ('host', str), 
	'cassandra_port': ('port', int),
	}


ACTIVEMQ_INIT_CONFIG = {
'conf': [{'include': {'Type': 'Queue',
'attribute': {'AverageEnqueueTime': {'alias': 'activemq.queue.avg_enqueue_time',
'metric_type': 'gauge'},
'ConsumerCount': {'alias': 'activemq.queue.consumer_count',
'metric_type': 'gauge'},
'DequeueCount': {'alias': 'activemq.queue.dequeue_count',
'metric_type': 'counter'},
'DispatchCount': {'alias': 'activemq.queue.dispatch_count',
'metric_type': 'counter'},
'EnqueueCount': {'alias': 'activemq.queue.enqueue_count',
'metric_type': 'counter'},
'ExpiredCount': {'alias': 'activemq.queue.expired_count',
'type': 'counter'},
'InFlightCount': {'alias': 'activemq.queue.in_flight_count',
'metric_type': 'counter'},
'MaxEnqueueTime': {'alias': 'activemq.queue.max_enqueue_time',
'metric_type': 'gauge'},
'MemoryPercentUsage': {'alias': 'activemq.queue.memory_pct',
'metric_type': 'gauge'},
'MinEnqueueTime': {'alias': 'activemq.queue.min_enqueue_time',
'metric_type': 'gauge'},
'ProducerCount': {'alias': 'activemq.queue.producer_count',
'metric_type': 'gauge'},
'QueueSize': {'alias': 'activemq.queue.size',
'metric_type': 'gauge'}}}},
{'include': {'Type': 'Broker',
'attribute': {'MemoryPercentUsage': {'alias': 'activemq.broker.memory_pct',
'metric_type': 'gauge'},
'StorePercentUsage': {'alias': 'activemq.broker.store_pct',
'metric_type': 'gauge'},
'TempPercentUsage': {'alias': 'activemq.broker.temp_pct',
'metric_type': 'gauge'}}}}]}

SOLR_INIT_CONFIG = {
'conf': 
[{'include': 
{'attribute': 
{'maxDoc': 
{'alias': 'solr.searcher.maxdoc',
'metric_type': 'gauge'},
'numDocs': 
{'alias': 'solr.searcher.numdocs',
'metric_type': 'gauge'},
'warmupTime': 
{'alias': 'solr.searcher.warmup',
'metric_type': 'gauge'}},
'type': 'searcher'}},
{'include': 
{'attribute': 
{'cumulative_evictions': 
{'alias': 'solr.cache.evictions',
'metric_type': 'counter'},
'cumulative_hits': {'alias': 'solr.cache.hits',
'metric_type': 'counter'},
'cumulative_inserts': {'alias': 'solr.cache.inserts',
'metric_type': 'counter'},
'cumulative_lookups': {'alias': 'solr.cache.lookups',
'metric_type': 'counter'}},
'id': 'org.apache.solr.search.FastLRUCache'}},
{'include': {'attribute': {'cumulative_evictions': {'alias': 'solr.cache.evictions',
'metric_type': 'counter'},
'cumulative_hits': {'alias': 'solr.cache.hits',
'metric_type': 'counter'},
'cumulative_inserts': {'alias': 'solr.cache.inserts',
'metric_type': 'counter'},
'cumulative_lookups': {'alias': 'solr.cache.lookups',
'metric_type': 'counter'}},
'id': 'org.apache.solr.search.LRUCache'}},
{'include': {'attribute': {'avgRequestsPerSecond': {'alias': 'solr.search_handler.avg_requests_per_sec',
'metric_type': 'gauge'},
'avgTimePerRequest': {'alias': 'solr.search_handler.avg_time_per_req',
'metric_type': 'gauge'},
'errors': {'alias': 'solr.search_handler.errors',
'metric_type': 'counter'},
'requests': {'alias': 'solr.search_handler.requests',
'metric_type': 'counter'},
'timeouts': {'alias': 'solr.search_handler.timeouts',
'metric_type': 'counter'},
'totalTime': {'alias': 'solr.search_handler.time',
'metric_type': 'counter'}},
'id': 'org.apache.solr.handler.component.SearchHandler'}}]}

TOMCAT_INIT_CONFIG = {'conf': [{'include': {'attribute': {'currentThreadCount': {'alias': 'tomcat.threads.count',
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

class NoConfigToMigrateException(Exception): pass

def migrate_cassandra(agentConfig):
    for old_key, params in CASSANDRA_MAPPING.iteritems():
        new_key, param_type = params
        if old_key not in agentConfig:
            return None
        CASSANDRA_CONFIG['instances'][0][new_key] = param_type(agentConfig[old_key])

    return CASSANDRA_CONFIG

def migrate_tomcat(agentConfig):
    return parse_jmx_agent_config(agentConfig, "tomcat", init_config=TOMCAT_INIT_CONFIG)

def migrate_solr(agentConfig):
    return parse_jmx_agent_config(agentConfig, "solr", init_config=SOLR_INIT_CONFIG)

def migrate_activemq(agentConfig):
    return parse_jmx_agent_config(agentConfig, 'activemq', init_config=ACTIVEMQ_INIT_CONFIG)

def migrate_java(agentConfig):
    return parse_jmx_agent_config(agentConfig, 'java')

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

def parse_jmx_agent_config(agentConfig, config_key, init_config=None):
    """ Converts the old style config to the checks.d style"""

    (connections, users, passwords) = _load_old_config(agentConfig, config_key)

    # If there is no old configuration, don't try to run these
    # integrations.
    if not (connections and users and passwords):
        return None

    config = {}
    instances = []
    for i in range(len(connections)):
        try:
            connect = connections[i].split(':')
            instance = {
            'host':connect[0],
            'port':int(connect[1]),
            'user':users[i],
        	'password':passwords[i]
            }
            if len(connect) == 3:
                instance['name'] = connect[2]

            instances.append(instance)

        except Exception, e:
            log.error("Cannot migrate JMX instance %s" % config_key)
	    
    config['instances'] = instances
	    
    if init_config is not None:
        config['init_config'] = init_config
    else: 
        config['init_config'] = {}
    return config

def _write_conf(check_name, config, confd_dir):
    if config is None:
        log.debug("No config for check: %s" % check_name)
        raise NoConfigToMigrateException()

    try:
        yaml_config = yaml.dump(config, Dumper=yDumper, default_flow_style=False)
    except Exception, e:
        log.exception("Couldn't create yaml from config: %s" % config)
        return

    file_name = "%s.yaml" % check_name
    full_path = os.path.join(confd_dir, file_name)
    if os.path.exists(full_path):
        log.debug("Config already exists for check: %s" % full_path)
        return

    try:
        f = open(full_path, 'w')
        f.write(yaml_config)
        log.info("Successfully wrote %s" % full_path)
    except Exception, e:
        log.exception("Cannot write config file %s" % full_path)

CHECKS_TO_MIGRATE = {
    # A dictionary of check name, migration function
	'cassandra' : migrate_cassandra, 
	'tomcat': migrate_tomcat,
	'solr': migrate_solr,
	'activemq': migrate_activemq,
	'jmx': migrate_java,
}

TO_COMMENT = [
    'java_',
    'cassandra_',
    'tomcat_',
    'solr_',
    'activemq_'
]

def _comment_old_config(datadog_conf_path):
    """Tries to comment lines in datadog.conf that shouldn't be used anymore"""

    f = open(datadog_conf_path, "r+")
    config_lines = map(string.strip, f.readlines())
    new_lines = []
    for line in config_lines:
        should_comment = False
        for key in TO_COMMENT:
            if line.startswith(key):
                should_comment = True
                break

        if should_comment:
            new_lines.append("# %s" % line)
        else:
            new_lines.append(line)

    f.seek(0)
    f.write("\n".join(new_lines))
    f.truncate()
    f.close()


def migrate_old_style_configuration(agentConfig, confd_dir, datadog_conf_path):
    """This will try to migrate some integration configurations configured in datadog._comment_old_conf 
    to the checks.d format 
    """
    log.info("Running migration script")
    should_comment_datadog_conf = False
    for check_name, migrate_fct in CHECKS_TO_MIGRATE.iteritems():
        log.debug("Migrating %s integration" % check_name)
        try:
            _write_conf(check_name, migrate_fct(agentConfig), confd_dir)
            should_comment_datadog_conf = True
        except NoConfigToMigrateException:
            pass
        except Exception, e:
            log.exception("Error while migrating %s" % check_name)

    if should_comment_datadog_conf:
        try:
            _comment_old_config(datadog_conf_path)
        except Exception, e:
            log.exception("Error while trying to comment deprecated lines in datadog.conf")

