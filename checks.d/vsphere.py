# stdlib
from datetime import datetime, timedelta
import time
import traceback
from Queue import Queue, Empty

# project
from checks import AgentCheck
from util import Timer
from checks.libs.thread_pool import Pool

# 3rd party
from pyVim import connect
from pyVmomi import vim

SOURCE_TYPE = 'vsphere'
REAL_TIME_INTERVAL = 20 # Default vCenter sampling interval

# The size of the ThreadPool used to process the request queue
DEFAULT_SIZE_POOL = 4
# The interval in seconds between two refresh of the entities list
REFRESH_MORLIST_INTERVAL = 3 * 60
# The interval in seconds between two refresh of metrics metadata (id<->name)
REFRESH_METRICS_METADATA_INTERVAL = 10 * 60

# Time after which we reap the jobs that clog the queue
# TODO: use it
JOB_TIMEOUT = 10


def atomic_method(method):
    """ Decorator to catch the exceptions that happen in detached thread atomic tasks
    and display them in the logs.
    FIXME: get a traceback instead of a __repr__
    """
    def wrapper(*args, **kwargs):
        try:
            method(*args, **kwargs)
        except Exception as e:
            args[0].exceptionq.put(e)
    return wrapper


class VSphereCheck(AgentCheck):
    """ Get performance metrics from a vCenter server and upload them to Datadog
    References:
        http://pubs.vmware.com/vsphere-51/index.jsp#com.vmware.wssdk.apiref.doc/vim.PerformanceManager.html

    *_atomic jobs perform one single task asynchronously in the ThreadPool, we
    don't know exactly when they will finish, but we reap them if they're stuck.
    The other calls are performed synchronously.
    """

    def __init__(self, name, init_config, agentConfig, instances):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.time_started = time.time()
        self.pool_started = False
        self.exceptionq = Queue()

        # Connections open to vCenter instances
        self.server_instances = {}

        # Caching resources, timeouts
        self.cache_times = {}
        for instance in self.instances:
            i_key = self._instance_key(instance)
            self.cache_times[i_key] = {
                'morlist': {
                    'last': 0,
                    'interval': init_config.get('refresh_morlist_interval', 
                                    REFRESH_MORLIST_INTERVAL)
                },
                'metrics_metadata': {
                    'last': 0,
                    'interval': init_config.get('refresh_metrics_metadata_interval', 
                                    REFRESH_METRICS_METADATA_INTERVAL)
                }
            }
        # First layer of cache (get entities from the tree)
        self.morlist_raw = {}
        # Second layer, processed from the first one
        self.morlist = {}
        # Metrics metadata, basically perfCounterId -> {name, group, description}
        self.metrics_metadata = {}

        self.latest_event_query = {}

    def stop(self):
        self.stop_pool()
        self.pool_started = False

    def start_pool(self):
        # The pool size should be the minimum between the number of instances
        # and the DEFAULT_SIZE_POOL. It can also be overridden by the 'threads_count'
        # parameter in the init_config of the check
        self.log.info("Starting Thread Pool")
        self.pool_size = int(self.init_config.get('threads_count', DEFAULT_SIZE_POOL))

        self.pool = Pool(self.pool_size)
        self.pool_started = True
        self.jobs_status = {}

    def stop_pool(self):
        self.log.info("Stopping Thread Pool")
        if self.pool_started:
            self.pool.terminate()
            self.pool.join()
            self.jobs_status.clear()
            assert self.pool.get_nworkers() == 0

    def restart_pool(self):
        self.stop_pool()
        self.start_pool()

    def _clean(self):
        now = time.time()
        for name in self.jobs_status.keys():
            start_time = self.jobs_status[name]
            if now - start_time > JOB_TIMEOUT:
                self.log.critical("Restarting Pool. One check is stuck.")
                self.restart_pool()
                break

    def _query_event(self, instance):
        i_key = self._instance_key(instance)
        last_time = self.latest_event_query.get(i_key, None)

        server_instance = self._get_server_instance(instance)
        event_manager = server_instance.content.eventManager

        # Be sure we don't duplicate any event, never query the "past"
        if not last_time:
            last_time = self.latest_event_query[i_key] = \
                event_manager.latestEvent.createdTime.replace(tzinfo=None) + timedelta(seconds=1)

        query_filter = vim.event.EventFilterSpec()
        time_filter = vim.event.EventFilterSpec.ByTime(beginTime=self.latest_event_query[i_key])
        query_filter.time = time_filter

        new_events = event_manager.QueryEvents(query_filter)
        self.log.info("Got {0} events".format(len(new_events)))
        for event in new_events:
            self.event({
                "timestamp": int((event.createdTime.replace(tzinfo=None) - datetime(1970, 1, 1)).total_seconds()),
                "event_type": SOURCE_TYPE,
                "msg_title": u"vCenter event: {0}".format(event.__class__.__name__[10:]), # trim vim.event
                "msg_text": u"@@@\n{0}\n@@@".format(event.fullFormattedMessage)
            })
            last_time = event.createdTime.replace(tzinfo=None) + timedelta(seconds=1)

        self.latest_event_query[i_key] = last_time

    def _instance_key(self, instance):
        i_key = instance.get('name')
        if i_key is None:
            raise Exception("Must define a unique 'name' per vCenter instance")
        return i_key

    def _should_cache(self, instance, entity):
        i_key = self._instance_key(instance)
        now = time.time()
        return now - self.cache_times[i_key][entity]['last'] > self.cache_times[i_key][entity]['interval']

    def _get_server_instance(self, instance):
        i_key = self._instance_key(instance)

        if i_key not in self.server_instances:
            try:
                server_instance = connect.SmartConnect(
                    host=instance.get('host'),
                    user=instance.get('username'),
                    pwd=instance.get('password')
                )
            except Exception as e:
                raise Exception("Connection to %s failed: %s" % (instance.get('host'), e))

            self.server_instances[i_key] = server_instance

        return self.server_instances[i_key]

    def get_extra_host_tags(self):
        """ Returns a list of tags for every host that is detected by the vSphere
        integration.
        List of pairs (hostname, list_of_tags)
        """
        extra_host_tags = []
        for instance in self.instances:
            i_key = self._instance_key(instance)
            mor_list = self.morlist[i_key].keys()
            for mor_name in mor_list:
                mor = self.morlist[i_key][mor_name]
                extra_host_tags.append((mor['hostname'], mor['tags']))

        return SOURCE_TYPE, extra_host_tags

    @atomic_method
    def _cache_morlist_raw_atomic(self, i_key, obj_type, obj, tags):
        """ Compute tags for a single node in the vCenter rootFolder
        and queue other such jobs for children nodes.
        Usual hierarchy:
        rootFolder
            - datacenter1
                - compute_resource1 == cluster
                    - host1
                    - host2
                    - host3
                - compute_resource2
                    - host5
                        - vm1
                        - vm2
        If it's a node we want to query metric for, queue it in self.morlist_raw
        that will be processed by another job.
        """
        ### <TEST-INSTRUMENTATION>
        t = Timer()
        self.log.debug("job_atomic: Exploring MOR {0} (type={1})".format(obj, obj_type))
        ### </TEST-INSTRUMENTATION>

        if obj_type == 'rootFolder':
            for datacenter in obj.childEntity:
                # Skip non-datacenter
                if not hasattr(datacenter, 'hostFolder'):
                    continue
                self.pool.apply_async(
                    self._cache_morlist_raw_atomic,
                    args=(i_key, 'datacenter', datacenter, tags)
                )

        elif obj_type == 'datacenter':
            dc_tag = "vsphere_datacenter:%s" % obj.name
            tags.append(dc_tag)
            for compute_resource in obj.hostFolder.childEntity:
                # Skip non-compute resource
                if not hasattr(compute_resource, 'host'):
                    continue
                self.pool.apply_async(
                    self._cache_morlist_raw_atomic,
                    args=(i_key, 'compute_resource', compute_resource, tags)
                )
                
        elif obj_type == 'compute_resource':
            if obj.__class__ == vim.ClusterComputeResource:
                cluster_tag = "vsphere_cluster:%s" % obj.name
                tags.append(cluster_tag)
            for host in obj.host:
                # Skip non-host
                if not hasattr(host, 'vm'):
                    continue
                self.pool.apply_async(
                    self._cache_morlist_raw_atomic,
                    args=(i_key, 'host', host, tags)
                )

        elif obj_type == 'host':
            watched_mor = dict(mor_type='host', mor=obj, hostname=obj.name, tags=tags)
            self.morlist_raw[i_key].append(watched_mor)

            host_tag = "vsphere_host:%s" % obj.name
            tags.append(host_tag)
            for vm in obj.vm:
                if vm.runtime.powerState != 'poweredOn':
                    continue
                self.pool.apply_async(
                    self._cache_morlist_raw_atomic,
                    args=(i_key, 'vm', vm, tags)
                )

        elif obj_type == 'vm':
            watched_mor = dict(mor_type='vm', mor=obj, hostname=obj.name, tags=tags)
            self.morlist_raw[i_key].append(watched_mor)

        ### <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.morlist_raw_atomic.time', t.total())
        ### </TEST-INSTRUMENTATION>

    def _cache_morlist_raw(self, instance):
        """ Initiate the first layer to refresh self.morlist by queueing
        _cache_morlist_raw_atomic on the rootFolder in a recursive/asncy approach
        """

        i_key = self._instance_key(instance)
        self.log.debug("Caching the morlist for vcenter instance %s" % i_key)
        self.morlist_raw[i_key] = []

        server_instance = self._get_server_instance(instance)
        root_folder = server_instance.content.rootFolder

        instance_tag = "vcenter_server:%s" % instance.get('name')
        self.pool.apply_async(
            self._cache_morlist_raw_atomic,
            args=(i_key, 'rootFolder', root_folder, [instance_tag])
        )
        self.cache_times[i_key]['morlist']['last'] = time.time()

    @atomic_method
    def _cache_morlist_process_atomic(self, instance, mor):
        """ Process one item of the self.morlist_raw list by querying the available
        metrics for this MOR and then putting it in self.morlist
        """
        ### <TEST-INSTRUMENTATION>
        t = Timer()
        ### </TEST-INSTRUMENTATION>
        i_key = self._instance_key(instance)
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager

        self.log.debug("job_atomic: Querying available metrics for MOR {0} (type={1})"\
            .format(mor['mor'], mor['mor_type']))

        mor['metrics'] = perfManager.QueryAvailablePerfMetric(
            mor['mor'], intervalId=REAL_TIME_INTERVAL)
        mor_name = str(mor['mor'])

        if mor_name in self.morlist[i_key]:
            # Was already here last iteration
            self.morlist[i_key][mor_name]['metrics']
        else:
            self.morlist[i_key][mor_name] = mor

        self.morlist[i_key][mor_name]['last_seen'] = time.time()

        ### <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.morlist_process_atomic.time', t.total())
        ### </TEST-INSTRUMENTATION>
                            
    def _cache_morlist_process(self, instance):
        """ Empties the self.morlist_raw by popping items and running asynchronously
        the _cache_morlist_process_atomic operation that will get the available
        metrics for this MOR and put it in self.morlist
        """
        i_key = self._instance_key(instance)
        if i_key not in self.morlist:
            self.morlist[i_key] = {}

        # Batch per 50 request
        for i in xrange(50):
            try:
                mor = self.morlist_raw[i_key].pop()
                self.pool.apply_async(self._cache_morlist_process_atomic, args=(instance, mor))
            except (IndexError, KeyError):
                self.log.debug("No more work to process in morlist_raw")
                return

    def _vacuum_morlist(self, instance):
        """ Check if self.morlist doesn't have some old MORs that are gone, ie
        we cannot get any metrics from them anyway (or =0)
        """
        i_key = self._instance_key(instance)
        morlist = self.morlist[i_key].keys()

        for mor_name in morlist:
            last_seen = self.morlist[i_key][mor_name]['last_seen']
            if (time.time() - last_seen) > 2 * REFRESH_MORLIST_INTERVAL:
                del self.morlist[i_key][mor_name]

    def _cache_metrics_metadata(self, instance):
        """ Get from the server instance, all the performance counters metadata
        meaning name/group/description... attached with the corresponding ID
        """
        ### <TEST-INSTRUMENTATION>
        t = Timer()
        ### </TEST-INSTRUMENTATION>

        self.log.info("Warming metrics metadata cache")
        i_key = self._instance_key(instance)
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager

        # Reset metadata
        self.metrics_metadata[i_key] = {}
        for counter in perfManager.perfCounter:
            d = dict(
                name = "%s.%s" % (counter.groupInfo.key, counter.nameInfo.key),
                unit = counter.unitInfo.key,
                instance_tag = 'instance' #FIXME: replace by what we want to tag!
            )
            self.metrics_metadata[i_key][counter.key] = d
        self.cache_times[i_key]['metrics_metadata']['last'] = time.time()

        ### <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.metric_metadata_collection.time', t.total())
        ### </TEST-INSTRUMENTATION>

    @atomic_method
    def _collect_metrics_atomic(self, instance, mor):
        """ Task that collects the metrics listed in the morlist for one MOR
        """
        ### <TEST-INSTRUMENTATION>
        t = Timer()
        ### </TEST-INSTRUMENTATION>

        i_key = self._instance_key(instance)
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager
        query = vim.PerformanceManager.QuerySpec(maxSample=1,
                                     entity=mor['mor'],
                                     metricId=mor['metrics'],
                                     intervalId=20,
                                     format='normal')
        results = perfManager.QueryPerf(querySpec=[query])
        if results:
            for result in results[0].value:
                instance_name = result.id.instance or "none"
                self.gauge("vsphere.%s" % self.metrics_metadata[i_key][result.id.counterId]['name'],
                            result.value[0],
                            hostname=mor['hostname'],
                            tags=['instance:%s' % instance_name]
                )

        ### <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.metric_colection.time', t.total())
        ### </TEST-INSTRUMENTATION>

    def collect_metrics(self, instance):
        """ Calls asynchronously _collect_metrics_atomic on all MORs, as the
        job queue is processed the Aggregator will receive the metrics.
        """
        i_key = self._instance_key(instance)
        if i_key not in self.morlist:
            self.log.debug("Not collecting metrics for this instance, nothing to do yet: {0}".format(i_key))
            return

        mors = self.morlist[i_key].keys()
        self.log.debug("Collecting metrics of %d mors" % len(mors))

        vm_count = 0

        for mor_name in mors:
            mor = self.morlist[i_key][mor_name]
            if mor['mor_type'] == 'vm':
                vm_count += 1
            if 'metrics' not in mor:
                # self.log.debug("Skipping entity %s collection because we didn't cache its metrics yet" % mor['hostname'])
                continue

            self.pool.apply_async(self._collect_metrics_atomic, args=(instance, mor))

        self.gauge('vsphere.vm.count', vm_count, tags=["vcenter_server:%s" % instance.get('name')])

    def check(self, instance):
        if not self.pool_started:
            self.start_pool()
        ### <TEST-INSTRUMENTATION>
        self.gauge('datadog.agent.vsphere.queue_size', self.pool._workq.qsize(), tags=['instant:initial'])
        ### </TEST-INSTRUMENTATION>

        # First part: make sure our object repository is neat & clean
        if self._should_cache(instance, 'metrics_metadata'):
            self._cache_metrics_metadata(instance)

        if self._should_cache(instance, 'morlist'):
            self._cache_morlist_raw(instance)
        self._cache_morlist_process(instance)
        self._vacuum_morlist(instance)

        # Second part: do the job
        self.collect_metrics(instance)
        self._query_event(instance)

        # For our own sanity
        self._clean()
        # TODO: raise if the exceptionq is too high
        try:
            while True:
                self.log.critical(self.exceptionq.get_nowait())
        except Empty:
            pass
            
        ### <TEST-INSTRUMENTATION>
        self.gauge('datadog.agent.vsphere.queue_size', self.pool._workq.qsize(), tags=['instant:final'])
        ### </TEST-INSTRUMENTATION>

if __name__ == '__main__':
    check = VSphereCheck.from_yaml('conf.d/vsphere.yaml')
    try:
        for i in xrange(200):
            print "Loop %d" % i
            for instance in check.instances:
                check.check(instance)
                if check.has_events():
                    print 'Events: %s' % (check.get_events())
                print 'Metrics: %d' % (len(check.get_metrics()))
            time.sleep(10)
    except Exception as e:
        print "Whoops something happened {0}".format(traceback.format_exc())
    finally:
        check.stop()
