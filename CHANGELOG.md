Changes
=======

# 5.4.4 / 08-05-2015
**Source Install only**

### Details
https://github.com/DataDog/dd-agent/compare/5.4.3...5.4.4

### Changes
* [BUGFIX] Update `ntplib` to 0.3.3 to fix source install requirements. See [#1792][]

# 5.4.3 / 07-13-2015
**Linux or Source Install only**

### Details
https://github.com/DataDog/dd-agent/compare/5.4.2...5.4.3

### Changes
* [SECURITY] The deb and rpm packages now bundle OpenSSL 1.0.1p. For more details, see the [security advisory](http://openssl.org/news/secadv_20150709.txt).
* [BUGFIX] Docker: Do not fail when the event API returns a bad JSON response. See [#1757][]


# 5.4.2 / 06-18-2015
**Linux or Source Install only**

### Details
https://github.com/DataDog/dd-agent/compare/5.4.1...5.4.2

### Changes
* [BUGFIX] Disk: Strict backward compatibility with old disk check. See [#1710][]
* [BUGFIX] Etcd: Do not query leader endpoint on followers (was causing check failure). See [#1709][]


# 5.4.1 / 06-16-2015
**Linux or Source Install only**

### Details
https://github.com/DataDog/dd-agent/compare/5.4.0...5.4.1

### Changes
* [BUGFIX] Disk: Get metrics only from physical disk by default. See [#1700][]
* [BUGFIX] Kafka: Fix indentation issue in the configuration YAML example file. See [#1701][]


# 5.4.0 / 06-16-2015
### Details
https://github.com/DataDog/dd-agent/compare/5.3.2...5.4.0

### New integrations
* Mesosphere master
* Mesosphere slave

### Updated integrations
* Disk
* Docker
* Elasticsearch
* etcd
* Fluentd
* HAProxy
* HTTP Check
* JMXFetch
* Kafka consumer
* Mesosphere
* MySQL
* NTP
* PHP-FPM
* PostgreSQL
* Process
* SQL Server
* System
* TCP Check
* Varnish
* WMI

### Agent Developer mode
The Agent Developer Mode allows the user to collect a wide array of metrics concerning the performance of the agent itself. It provides visibility into bottlenecks when writing an `AgentCheck` and when making changes to the collector core.
For more information, see [our wiki page](https://github.com/DataDog/dd-agent/wiki/Agent-Developer-Mode).

### Deprecation notice

#### Old agent commands
Old command line tools `dd-agent`, `dd-forwarder` and `dogstatsd` are deprecated as for `5.4.0`. `dd-forwarder` & `dogstatsd` will be removed in a future version, and `dd-agent` functions will be limited to `check`, `jmx` and `flare`.
For more information, see [our wiki page](https://github.com/DataDog/dd-agent/wiki/Deprecation-notice--(old-command-line-tools))
See [#1457][], [#1569][]

#### Ganglia integration
The Ganglia integration is deprecated and will be removed in a future version of the Datadog Agent.
See [#1621][]

### Changes
* [FEATURE] Agent developer mode. See [#1577][]
* [FEATURE] Application names to tags ("dd_check:appname") support. See [#1570][]
* [FEATURE] Service metadata support. See [#1611][]
* [FEATURE] Dogstream: Add filename globing support. See [#1550][] (Thanks [@gtaylor][])
* [FEATURE] Elasticsearch: Add pending tasks metrics. See [#1507][]
* [FEATURE] Elasticsearch: Add tags to events. See [#1444][]
* [FEATURE] etcd: Add etcd latency metrics. See [#1429][]
* [FEATURE] Flare: Add commands standard error stream to content. See [#1586][]
* [FEATURE] Fluentd: Add type tag support. See [#1623][] (Thanks [@yyamano][])
* [FEATURE] HAProxy: Add new time metrics available in 1.5. See [#1579][] (Thanks [@warnerpr-cyan][])
* [FEATURE] HTTP/TCP Check: Add support for custom tags. See [#1642][]
* [FEATURE] JMXFetch: Add service check count to JMX checks statuses. See [#1559][]
* [FEATURE] Mesosphere: New checks for masters -reporting metrics from leaders- and slaves -reporting metrics from the selected tasks-. See [#1535][]
* [FEATURE] MySQL: Add threads running metrics. See [#1613][] (Thanks [@polynomial][])
* [FEATURE] PHP-FPM: Add custom ping reply support. See [#1582][] (Thanks [@squaresurf][])
* [FEATURE] System: Add system swap metrics. See [#1549][]

* [IMPROVEMENT] Limit process restart attempts on Windows on a specific time frame. See [#1664][]
* [IMPROVEMENT] Only start the Collector and Dogstatsd when needed. See [#1569][]
* [IMPROVEMENT] Use internal `/run` for temporary pid, pickle and JMXFetch files. See [#1569][], [#1679][]
* [IMPROVEMENT] Disk: New check based on `psutil` replaces the old system check. See [#1596][]
* [IMPROVEMENT] JMXFetch: Run JMXFetch as `dd-agent` user. See [#1619][]
* [IMPROVEMENT] NTP: Use Datadog NTP pool. See [#1618][]
* [IMPROVEMENT] Process: Cache AccessDenied failures and PID list. See [#1595][]
* [IMPROVEMENT] SQL Server: Set a timeout for each SQL command, default to 30s. See [#1446][]

* [BUGFIX] Cast service checks messages to strings. See [#1617][]
* [BUGFIX] Fix incorrect EC2 metadata resulting from the no proxy environment settings. See [#1650][] [#1594][]
* [BUGFIX] Uses NTP check settings to avoid failures in status checks. See [#1651][] [#1558][]
* [BUGFIX] Disk: Fix a bug where all devices were ignored if the device blacklist regex was empty. See [#1666][]
* [BUGFIX] Docker: Fix intermittent failures (bad support) when a container has no name. See [#1565][]
* [BUGFIX] Elasticsearch: Fix data being illegitimately filtered out when the local node reports under a different hostname. See [#1657][]
* [BUGFIX] HTTP Check: Fix status type errors in service check. See [#1644][]
* [BUGFIX] JMXFetch: Clean previous JMX status python file at start. See [#1655][]
* [BUGFIX] JMXFetch: Fix `jmx` agent commands false warning. See [#1612][].
* [BUGFIX] JMXFetch: Format service check names prefix names to strip non alphabetic characters.
* [BUGFIX] JMXFetch: Properly exit on Windows when a specified file is created. See [#1643][]
* [BUGFIX] JMXFetch: Rename 'host' bean parameter to 'bean_host' in tags to avoid conflicts.
* [BUGFIX] JMXFetch: Support bean names that have an attribute with an empty value.
* [BUGFIX] Kafka consumer: Add timeout for ZooKeeper and Kafka connections. See [#1592][] [#1589][]
* [BUGFIX] Mesosphere: Cast error messages to strings. See [#1614][] [TEST?]
* [BUGFIX] PostgreSQL: Ignore `rdsadmin` database in PostgreSQL check to avoid permission error. See [#1590][] (Thanks [@etrepum][])
* [BUGFIX] PostgreSQL: Properly log bugs for custom metrics. See [#1633][] (Thanks [@orenmazor][])
* [BUGFIX] SQL Server: Fix collector freezes when connection is failing. See [#1640][]
* [BUGFIX] SQL Server: Properly close cursor, avoid leaks. See [#1631][]
* [BUGFIX] SQL Server: Send fractional metrics as floats. See [#1616][]
* [BUGFIX] Varnish: Allow tags in varnish 3 XML style parsing. See [#1645][]
* [BUGFIX] WMI: Cast tag values as strings. See [#1630][]


# 5.3.2 / 04-29-2015
**Debian only**

### Details
https://github.com/DataDog/dd-agent/compare/5.3.1...5.3.2

### Changes
* [BUGFIX/FEATURE] Native support of systemd with a new service file


# 5.3.1 / 04-22-2015
**Windows only**

### Details
https://github.com/DataDog/dd-agent/compare/5.3.0...5.3.1

### Changes
* [BUGFIX] JMXFetch: Fix bootloop issue when no JMX integration is set. See [#1561][]


# 5.3.0 / 04-16-2015
### Details
https://github.com/DataDog/dd-agent/compare/5.2.2...5.3.0

### New integrations
* PGBouncer: See [#1391][]
* PHP-FPM: See [#1441][] (Thanks [@arosenhagen][])
* Supervisor. See [#1165][], [#1511][] & [#1512][]

### Updated integrations
* Cassandra
* ElasticSearch
* Gearman
* HTTP Check
* Jenkins
* JMXFetch
* Kafka
* Marathon
* Memcache
* nginx
* PostgreSQL
* Redis
* SNMP
* Varnish
* WMI
* ZooKeeper

### Changes
* [FEATURE] Add a "flare" feature to contact our support team. See [#1422][] & [#1509][]
* [FEATURE] nginx: Add a metric to track dropped connections
* [FEATURE] Redis: Add replication metrics and status. See [#1350][] and [#1447][] (Thanks [@pbitty][])
* [FEATURE] Redis: Collect slow log metrics. See [#1400][]
* [FEATURE] WMI: Extend tagging options: tag metrics with a target class property, or a set of fixed values. See [#1388][]
* [FEATURE] PostgreSQL: Add support for custom queries, StatIO metrics, and database size metric. See [#1395][] and [#1415][] (Thanks [@ipolishchuk][] and [@adriandoolittle][])
* [FEATURE] Kafka: Add support of kafka >= 0.8.2. See [#1438][] (Thanks [@patrickbcullen][])
* [FEATURE] Cassandra: Add more storage proxy metrics to default config. See [#1393][]
* [FEATURE] SNMP: Add support of SNMPv1. See [#1408][] (Thanks [@slushpupie][])
* [FEATURE] Jenkins: Add support of version >= 1.598. See [#1442][]
* [FEATURE] JMX Checks: Add service checks
* [FEATURE] JMX Checks: Add support of list of filters. See http://docs.datadoghq.com/integrations/java/
* [FEATURE] Varnish: Add support of Varnish 4.x. See [#1459][] and [#1461][]
* [FEATURE] HTTP Check: Add the possibility to test for the content of the response. See [#1297][], [#1326][] and [#1390][] (Thanks [@chrissnel][] and [@handigarde][])
* [IMPROVEMENT] JMXFetch: Move JMXFetch to its own entry in the supervisor
* [IMPROVEMENT] Switch http library used in checks to requests. See [#1399][]
* [IMPROVEMENT] NTP Check: Enable by default
* [IMPROVEMENT] EC2 tags: require only DescribeTags permission. See [#1503][] (Thanks [@oremj][])
* [BUGFIX] JMXFetch: Add default min and max heap size
* [BUGFIX] PostgreSQL: Fix "Metric has an interval of 0 bug". See [#1211][] and [#1396][]
* [BUGFIX] Marathon: Fix bad url construction. See [#1278][] and [#1401][]
* [BUGFIX] Zookeeper: Fix misleading metric name. See [#1443][] and [#1383][]
* [BUGFIX] Proxy settings: Cast proxy port to an integer. See [#1414][] and [#1416][]
* [BUGFIX] Support EC2 tag discovery in all regions. See [#1332][]
* [BUGFIX] Source installation: Fix "error: no such option: --use_simple_http_client". See [#1454][]
* [BUGFIX] Memcache: Fix bad support of multi instances. See [#1490][]
* [BUGFIX] Gearman: Fix bad support of multi instances. See [#1476][]
* [BUGFIX] HTTP Check: Fix for servers using SNI
* [BUGFIX] ElasticSearch: Fix bad support of multi instances. See [#1487][]
* [BUGFIX] Core: Do not use proxy for local connection. See [#1518][]



# 5.2.3 / 03-30-2015
**Windows only**

### Details
https://github.com/DataDog/dd-agent/compare/5.2.2...5.2.3

### Changes
* [BUGFIX] Fix vSphere service check

# 5.2.2 / 03-20-2015
**Linux or Source Install only**

### Details
https://github.com/DataDog/dd-agent/compare/5.2.1...5.2.2

### Changes
* [SECURITY] The deb and rpm packages now bundle OpenSSL 1.0.1m
* [BUGFIX] Fix "pidfile /tmp/dd-agent.pid already exists" bug. See [#1435][]
* [BUGFIX] Fix bundling of rrdtool python binding


# 5.2.1 / 02-20-2015
**Linux or Source Install only**

### Details
https://github.com/DataDog/dd-agent/compare/5.2.0...5.2.1

### Changes
* [BUGFIX] varnish: fix regression, bad argument in _parse_varnishstat. See [#1377][] (Thanks [@mms-gianni][])
* [BUGFIX] source install: move pysnmp and pysnmp-mibs to optional reqs. See [#1380][]
* [BUGFIX] etcd: service check OK is now returned. See [#1379][]
* [BUGFIX] varnish: fix varnishadm sudoed call with subprocess. See [#1389][]


# 5.2.0 / 02-17-2015
### Details
https://github.com/DataDog/dd-agent/compare/5.1.1...5.2.0

### New and updated integrations
* CouchDB
* Couchbase
* Docker
* ElasticSearch
* etcd
* fluentd
* Gearman
* GUnicorn
* HTTP
* JMXFetch
* KyotoTycoon
* Marathon
* Mesos
* Network
* Postgresql
* Process
* Riak
* RiakCS
* SNMP
* Supervisor
* TeamCity
* TokuMX
* Varnish
* VSphere
* Windows Event Viewer
* Windows Services
* Windows System metrics

### Endpoints
Starting from this version of the agent, the default endpoint URL `app.datadoghq.com` is replaced by an ad-hoc by version endpoint: `5-2-0-app.agent.datadoghq.com`. We might use other endpoints to better route the traffic on our end in the future. See more details at https://github.com/DataDog/dd-agent/wiki/Network-Traffic-and-Proxy-Configuration#new-agent-endpoints

### Changes
* [FEATURE] Dogstatsd: Add an option to namespace all metrics. See [#1210][] (Thanks [@igor47][])
* [FEATURE] Couchdb: Add a service check. See [#1201][]
* [FEATURE] Couchbase: Add a service check. See [#1200][]
* [FEATURE] Gearman: Add a service check. See [#1203][]
* [FEATURE] GUnicorn: Add a service check. See [#1163][]
* [FEATURE] KyotoTycoon: Add a service check. See [#1202][]
* [FEATURE] Marathon: Add a service check. See [#1205][]
* [FEATURE] Mesos: Add a service check. See [#1205][]
* [FEATURE] Riak: Add a service check. See [#1187][]
* [FEATURE] SNMP: Add a service check. See [#1236][]
* [FEATURE] TokuMX: Add a service check. See [#1173][]
* [FEATURE] Varnish: Add a service check. See [#1213][]
* [FEATURE] VSphere: Add a service check. See [#1238][]
* [FEATURE] VSphere: Allow host filtering. See [#1226][]
* [FEATURE] HTTPCHeck: Check for SSL certificate expiration. See [#1152][]
* [FEATURE] etcd: Add new etcd integration. See [#1235][] (Thanks [@gphat][])
* [FEATURE] Process: Better SmartOS support. See [#1073][] (Thanks [@djensen47][])
* [FEATURE] Windows Event Viewer: Allow filtering by id. See [#1255][]
* [FEATURE] Windows Services: Monitor state of Windows Services. See [#1225][]
* [FEATURE] Windows: Get more system metrics regarding memory and disk usage.
* [FEATURE] Windows: Better GUI
* [FEATURE] Adding “min” metric to histograms. See [#1219][]
* [FEATURE] Activemq: New ActiveMQ XML check that collect more metrics. See [#1227][] (Thanks [@brettlangdon][])
* [FEATURE] TeamCity: New TeamCity integration. See [#1171][] (Thanks [@AirbornePorcine][])
* [FEATURE] RiakCS: Add a RiakCS Integration. See [#1101][] (Thanks [@glickbot][])
* [FEATURE] FluentD: Add a FluentD integration. See [#1080][] (Thanks [@takus][])
* [FEATURE] Docker: Configurable image count collection. See [#1345][]
* [FEATURE] SNMP: Integer and Integer32 metric types support. See [#1318][]
* [FEATURE] JMXFetch: Fetch more JVM (Non)Heap variables by default. See [#42](https://github.com/DataDog/jmxfetch/pull/42)

* [BUGFIX] Docker: Filter events too. See [#1285][]
* [BUGFIX] ElasticSearch: Handle Timeout. See [#1267][]
* [BUGFIX] ElasticSearch: Only query the local node. See [#1181][] (Thanks [@jonaf][])
* [BUGFIX] Marathon: Fix check on Marathon >= 0.7. See [#1240][]
* [BUGFIX] Network: Fix interface skipping. See [#1260][] (Thanks [@sirlantis][])
* [BUGFIX] Postgreql: Fix service check. See [#1273][]
* [BUGFIX] Postgresql: Fix BGW metrics. See [#1272][] (Thanks [@ipolishchuk][])
* [BUGFIX] Postgresql: Fix buffers_backend_fsync. See [#1275][]
* [BUGFIX] SNMP: Fix "tooBig" SNMP error. See [#1155][] (Thanks [@bpuzon][])
* [BUGFIX] Zookeeper: Fix bad command sending.
* [BUGFIX] ElasticSearch: Fix host tagging. See [#1282][]
* [BUGFIX] SNMP: Fix non-increasing OID issue. See [#1281][]
* [BUGFIX] Dogstatsd: Properly handle UTF-8 packets. See [#1279][]
* [BUGFIX] SQLServer: Fix for Latin1_General_BIN Collection Servers. See [#1214][] (Thanks [@PedroMiguelFigueiredo][])
* [BUGFIX] FreeBSD: Get full interface name. See [#1141][] (Thanks [@mutemule][])
* [BUGFIX] SNMP: Fix a 'Missing OID' issue. See [#1318][]
* [BUGFIX] JMXFetch: Fix a memory leak issue. See [#30](https://github.com/DataDog/jmxfetch/issues/30)
* [BUGFIX] Windows Event Log: Fix a timezone issue. See [#1370][]

# 5.1.1 / 12-09-2014
#### Details
https://github.com/DataDog/dd-agent/compare/5.1.0...5.1.1

### Updated integrations
* BTRFS
* MongoDB

### Changes

* [BUGFIX] MongoDB: Fix TypeError that was happening in some cases. See [#1222][]
* [BUGFIX] BTRFS: Handle "unknown" usage type. See [#1221][]
* [BUGFIX] Windows: When uninstalling the Agent, the uninstaller was mistakenly telling the user that the machine would reboot. This is fixed.


# 5.1.0 / 11-24-2014

### Notes
* Pup is now removed from the Datadog Agent
* The "ALL" parameter in the process check is deprecated and will be removed in a future version of the agent.
* The Windows installer does not require the .NET framework anymore.

### New and updated integrations
* PostgreSQL
* Directory
* Jenkins
* MongoDB
* Process
* ElasticSearch
* IIS
* ZooKeeper
* Memcached
* SSH
* System Core
* BTRFS

### Changes

* [FEATURE] Add Service Checks for the following integration:
    - Apache
    - HAProxy
    - Lighttpd
    - NginX
    - NTP
    - HTTP
    - TCP
    - Process
    - ElasticSearch
    - IIS
    - ZooKeeper
    - Memcached
    - MongoDB
    - SQL Server
    - MySQL
    - PostgeSQL


* [FEATURE] PostgreSQL: Pick up per-table size stats. See [#1105][]
* [FEATURE] PostgreSQL: Collect locks per mode and bgwriter metrics. See [#1019][]
* [FEATURE] Directory Check: Let the possibilty to tag metrics at the file level. See [#1041][] (Thanks [@Osterjour][])
* [FEATURE] Jenkins: Add result and build number to events tags. See [#1068][] (Thanks [@jzoldak][])
* [FEATURE] Add a SSH Check. See [#1117][]
* [FEATURE] Add a check to collect metrics from BTRFS. See [#1123][]
* [FEATURE] Add a check to collect system core metrics. See [#1124][]
* [FEATURE] DogStatsD recognizes and uses `host` and `device` tags as metric attributes. See [#1164][].
* [FEATURE] Docker: Revamp events and add more options. See [#1162][].
* [FEATURE] Docker: Collect relevant Docker metrics by default, make the others optional. See [#1207][].
* [FEATURE] Docker: Improve Docker metrics tagging. See [#1208][] and [#1218][].
* [BUGFIX] Jenkins: Fix when build does not yet have results. See [#1060][] (Thanks [@jzoldak][])
* [BUGFIX] PostgreSQL: If connection drops, re-establish at next run. See [#1105][]
* [BUGFIX] MongoDB: Add logging of serverStatus errors. See [#1065][] (Thanks [@igroenewold][])
* [BUGFIX] Docker: Fix various time-outs and errors. See [#1162][].

# 5.0.5 (Every platform) / 10-31-2014

This release fixes a bug on servers that are configured in local time instead of UTC Time.
If your server's clock is configured to use daylight saving time, your server might stop sending metrics for up to one hour when the Daylight Saving Time ends or until the Agent is restarted after the Daylight Saving Time ends.

We highly recommend to upgrade to this version if your server is configured in local time.

# 5.0.4 (deb package, rpm package) / 10-17-2014

This is a security update regarding POODLE (CVE-2014-3566).

The Omnibus package will now bundle OpenSSL 1.0.1j without support of SSLv3 (no-ssl3 flag) and Python 2.7.8 with a patch that disables SSLv3 unless explicity asked http://bugs.python.org/issue22638.

This Omnibus package also adds support of the sqlite3 library for Python.

# 5.0.3 (Windows only)

vSphere check:

* [FEATURE] Batching jobs to cache the infrastructure of vCenter when autodiscovering Hosts/VMs is configurable
* [BUGFIX] Fix ESXi host tags not being correctly set
* [BUGFIX] Fix metadata reset so that metrics processing is not stopped when refreshing metadata
* [BUGFIX] Fix thread pool crash when one thread would not terminate gracefully

# 5.0.2 (Windows only)

vSphere check:

* [FEATURE] Changed the event filter to remove login events by default
* [BUGFIX] Duplicate tags on VMs and host
* [BUGFIX] Ignore duplicate events about VM migrations

# 5.0.1 (Windows only)

[FEATURE] Releasing the vSphere check. This is a new integration able to fetch metrics and events from vCenter.

# 5.0.0 / 08-22-2014

### Notes

This is a major version of the Datadog-Agent.

* On Linux:
Packaging of the Agent has changed for RPM and DEB packages.

* On Windows:
This release has multiple fixes, see the list below.
Warning: The way CPU metrics are collected has changed and will be more accurate, you might see some changes in the graphs.

### What will break ?
* MySQL integration: If you see this error: ```OperationalError(2003, 'Can\'t connect to MySQL server on \'localhost\' ((1045, u"Access denied for user \'datadog\'@\'127.0.0.1\'...)```
the Datadog user will need to be modified from ```'datadog'@'localhost'``` to ``` 'datadog'@'127.0.0.1' ``` (your host IP). You can do this by running:

       ```
           $ mysql -p mysql
           # UPDATE user SET Host = '127.0.0.1' WHERE User = 'datadog';
           # FLUSH PRIVILEGES;
       ```
* If you were using a custom check that needed python dependencies you will have to reinstall them using the bundled pip:

       ```
sudo /opt/datadog-agent/embedded/bin/pip install YOUR_DEPENDENCY
       ```
* Configuring checks in datadog.conf for checks.d is deprecated and won't work anymore. Please configure your checks by editing the yaml files in the conf.d directory.

### How to upgrade?

See this Wiki page https://github.com/DataDog/dd-agent/wiki/Upgrade-to-Agent-5.x

### New and updated integrations

* Docker
* ElasticSearch
* Kafka
* Kafka consumer
* NTP
* HDFS
* Postgres
* Process
* Redis
* SNMP
* SQL Server

### Changes
* [FEATURE] Add support of Centos 7 and Fedora Core 19-20
* [FEATURE] Add a NTP check. See [#971][]
* [FEATURE] Add an option to instrument check runs time. See [#1013][]
* [FEATURE] Add derived Redis metrics. See [#1015][]
* [FEATURE] Add an SNMP Check. See [#299][]
* [FEATURE] Redis: Adds support for checking length of more types. See [#996][]
* [FEATURE] Let the possibility to exclude some disks for Windows disks check. See [#1008][]
* [FEATURE] Collect more Docker metrics. See [#1027][]
* [FEATURE] Docker check: work inside a Docker container. CoreOS support. See [#1001][]
* [FEATURE] HDFS: Add support for HA mode. See [#1018][]. Warning: It requires snakebite >= 2.2.0
* [BUGFIX] Support Windows EOL \r character. See [#1023][]
* [BUGFIX] Fix the collection of cpu metrics (>100%) on Windows. See [#653][]
* [BUGFIX] Fix connection error on Windows 2008 SP2. See [#1014][]
* [BUGFIX] Dogstreams on windows: Allow to specify custom parser. See [#887][]
* [BUGFIX] ElasticSearch: Fix elasticsearch metrics according to different ES versions: See [#1024][]
* [BUGFIX] Process check: Fix check on some version of psutil. See [#958][]
* [BUGFIX] Fix init script on Centos/RHEL when dogstatsd is disabled. See [#1002][]
* [BUGFIX] Fix kafka metrics by sending them as gauges instead of rate. See [#1029][]
* [BUGFIX] Kafka consumer: Support version 0.9 of python-kafka. See [#1028][]
* [BUGFIX] Postgres: fix columns to retrieve when two different postgres version on the same host. See [#1035][]
* [BUGFIX] Fix multiple Docker check bugs. See [#1017][] [#1031][]
* [BUGFIX] Lets the possibility to override curl behavior when using a proxy that returns a 302. See [#1036][]
* [BUGFIX] SQL Server: Detect automatically counter types to report them correctly. See [#1069][]
* [BUGFIX] Report Docker memory page metrics as rates.

# 4.4.0 / 06-24-2014

### Integrations affected

* Docker
* Redis
* Memcached
* MySQL
* PostgreSQL

### Changes
* [BUGFIX] Docker: Don't raise Exception if we fail to get some Docker croup info. See [#981][]
* [BUGFIX] Docker: Don't raise Exception if no Docker containers are running. See [#980][]
* [BUGFIX] Docker: Fix integration timeout issue. See [#963][]
* [ENHANCEMENT] Let the possibility to disable metadata collection from 169.254.169.254. See [#975][]
* [FEATURE] Redis: Add a metric to track key length. See [#962][]
* [FEATURE] MySQL: Collect more metrics. See [#972][]
* [BUGFIX] MySQL: Only collect metrics from /proc on linux machines. See [#984][]
* [BUGFIX] PostgreSQL: Handle negative replication delay. See [#977][]
* [ENHANCEMENT] Collect more Memcached stats. See [#982][]
* [BUGFIX] Remove Content-Length header in CONNECT HTTP Requests (when using a proxy), as CONNECT Requests shouldn't have that header and some proxies don't support it.


# 4.3.1 / 06-03-2014

**Linux or Source Install only**

### Integrations affected
* Docker
* HAProxy

### Changes
* [IMPROVEMENT] Don't collect Docker total_ metrics by default. See [#964][]
* [BUGFIX] Report Docker CPU metrics as rate. See [#964][]
* [BUGFIX] Add HAProxy reporter name in HAProxy event's titles. See [#960][]

# 4.3.0 / 05-22-2014

### Integrations affected
* MongoDB
* Process
* CouchDB
* Docker
* HAProxy
* Marathon
* Memcached
* Mesos
* MySQL
* TokuMX
* ElasticSearch
* Network

#### Changes
* [BUGFIX] Fix incorrect open file descriptors metric name in process check: See [#904][]. Warning: As the metric name will be changed. Your dashboards will have to be updated.
* [FEATURE] Add some mongo2.2+ metrics to check: See [#951][] (Thanks to [@ckrough][])
* [FEATURE] Collect checks statuses: See [#922]
* [FEATURE] CouchDB: Support basic authentication: See [#930]
* [FEATURE] Docker: Support Docker 0.11
* [FEATURE] Docker: Collect events from the events api
* [FEATURE] HAProxy: Allow collection of metrics per host with the option `collect_status_metrics_by_host`: See [#935]
* [BUGFIX] HAProxy: Fix inaccuracy of count_per_status metric: See [#940]
* [BUGFIX] HAProxy: Update event's titles: See [#935]
* [FEATURE] Add Marathon integration: See [#921][] (Thanks to [@graemej][])
* [FEATURE] Add Mesos integration: See [#919][] (Thanks to [@graemej][])
* [FEATURE] Memcached: Add delete_misses/delete_hits: See [#928][] (Thanks to [@arthurnn][])
* [BUGFIX] MySQL: Only collect MySQL metrics from /proc on unix machines: See [#947]
* [BUGFIX] MySQL: Fix duplicate metric bug: See [#899]
* [BUGFIX] Varnish: Fix a bug that was causing tags to be continuously added in some cases.
* [FEATURE] Add an option to disable Dogstastsd: See [#927]
* [FEATURE] Memcached: Add support for local unix socket connections: See [#891][] (Thanks to [@mike-lerch][])
* [FEATURE] Add TokuMX integration: See [#933][] (Thanks to [@leifwalsh][])
* [BUGFIX] ElasticSearch: Added correct GC metrics for ES 1.x: See [#900][] (Thanks to [@joningle][])
* [FEATURE] Network: Add additional metrics for TCP: See [#949][]

# 4.2.2 / 04-25-2014

**Windows Only**

### Integrations affected
* Redis

### Changes
* [FEATURE] Support Redis check on Windows: See [#917]

# 4.2.1 / 04-09-2014

### Integrations affected
* ElasticSearch
* Nginx
* Process
* Postgres

#### Changes
* [BUGFIX] Fix bug in Dogstatsd in the bucketing change: See [#894]
* [BUGFIX] Revert to the Simple HTTP Client by default in the forwarder as it's causing 599 in some cases. It's now configurable in datadog.conf
* [FEATURE] Support for OpenShift cartridges: See [#875]
* [PERFORMANCE] Compress Dogstatsd payloads: See [#893]
* [BUGFIX] Fix process check compatibility with psutil 2.0: See [#863]
* [FEATURE] Support additional NGINX Plus metrics: See [#876]
* [PERFORMANCE] Better handling of external clusters in Elasticsearch check: See [#883]
* [BUGFIX] Fix an issue that is causing a high number of tags for postgresql metrics when custom tags are enabled.


# 4.2.0 / 03-25-2014

### Integrations affected
* Couchbase
* Docker
* ElasticSearch
* HAProxy
* Kafka consumer
* Kafka server
* MongoDB
* MySQL
* PostgreSQL
* Process
* Google Compute Engine
* JMX Checks: Cassandra, Tomcat, Solr, ActiveMq, JMX, Kafka

#### Changes
* [PERFORMANCE] Disable pup by default
* [ENHANCEMENT] Use JMXFetch 0.3.0 ( [Changelog](https://github.com/DataDog/jmxfetch/blob/master/CHANGELOG.md) )
* [ENHANCEMENT] Metric limit for JMX Checks is raised to 350 metrics per instance
* [FEATURE] Add a "configtest" command alias of "configcheck": See [#838][]
* [FEATURE] Add a Docker integration: See [#844][] (Thanks to [@steeve][])
* [FEATURE] ElasticSearch: Support for newer versions (>= 0.90.10)
* [FEATURE] ElasticSearch: Add a metric to monitor cluster status: See [#827][] (Thanks to [@igor47][])
* [FEATURE] HAProxy: Add availability metrics: See [#834][] (Thanks to [@igor47][])
* [FEATURE] Add a Kafka consumer check (Requires python 2.6 or python 2.7): See [#810][]
* [FEATURE] Add a Kafka server check: See [#810][]
* [FEATURE] MongoDB: Support SSL connections to server: See [#848][]
* [FEATURE] Collect tags and hostname for Google Compute Engine hosts
* [FEATURE] PostgreSQL: Support check on Windows
* [ENHANCEMENT] Align the reporting of StatsD metrics to fixed time intervals for consistency in aggregation
* [PERFORMANCE] StatsD events are now batched: See [#852][]
* [PERFORMANCE] Add an optional timeout parameter to Couchbase integration: See [#826][]
* [PERFORMANCE] Use Tornado CurlAsyncHTTPClient by default over the SimpleHTTPClient
* [BUGFIX] MySQL: Fixed warning on SHOW SLAVE STATUS: See [#809][] (Thanks to [@ive][])
* [BUGFIX] PostgreSQL: Reset the connection if it seems broken: See [#784][]
* [BUGFIX] Process: Do not fail on older Linux Kernels: See [#849][]
* [BUGFIX]  Windows: Do not restart pup on windows if it's not enabled: See [#815][]
* [BUGFIX] JMX Checks: Properly ensure that only one instance of JMXFetch is running



# 4.1.0 / 2014-02-04

### Integrations affected
* PostgreSQL
* ElasticSearch
* Lighttpd
* Nginx
* HAProxy
* MongoDB
* Redis
* Varnish
* Couchbase

#### Changes
* [FEATURE] Support for older versions of psycopg2
* [FEATURE] New tool to help configuring JMX Checks: See http://docs.datadoghq.com/integrations/java/
* [FEATURE] Add basic authentication to Couchbase check [#787](https://github.com/DataDog/dd-agent/issues/787)
* [FEATURE] Add basic authentication to ElasticSearch check [#806](https://github.com/DataDog/dd-agent/issues/806)
* [FEATURE] Add basic authentication to Lighttpd check
* [FEATURE] Add basic authentication to Nginx check
* [FEATURE] Calculate used session percentage in HAProxy check [#752](https://github.com/DataDog/dd-agent/pull/752) (Thanks to [@walkeran](https://github.com/walkeran))
* [FEATURE] Add an HAProxy metric that counts the number of active backends [#729](https://github.com/DataDog/dd-agent/issues/729)
* [FEATURE] Turn SSL validation in http check into an option [#770](https://github.com/DataDog/dd-agent/issues/770)
* [FEATURE] Include tags in http service check [#780](https://github.com/DataDog/dd-agent/pull/780)
* [FEATURE] Add more metrics to MongoDB check for newer versions of MongoDB [#735](https://github.com/DataDog/dd-agent/issues/735)
* [FEATURE] Support multiple mongo instances in MongoDB check [08be06f4c](https://github.com/DataDog/dd-agent/commit/b860bdfa2d8e81131204a187bdd9c3908be06f4c)
* [FEATURE] Add more metrics to MySQL check [#72](https://github.com/DataDog/dd-agent/pull/726) (Thanks to [@skingry](https://github.com/skingry) and [@ronaldbradford](https://github.com/ronaldbradford))
* [FEATURE] Add per-table metrics to Postgresql check [#760](https://github.com/DataDog/dd-agent/pull/760)
* [FEATURE] Add more metrics in process check with newer version of psutil
* [FEATURE] Allow configuration of the Redis check using a unix socket path [#730](https://github.com/DataDog/dd-agent/issues/730)
* [FEATURE] Allow multiple instances of Varnish check [#490](https://github.com/DataDog/dd-agent/issues/490)
* [FEATURE] Add the ability to add tags to an elasticsearch instance [#790](https://github.com/DataDog/dd-agent/pull/790) (Thanks to [@clly](https://github.com/clly))
* [BUGFIX] Fix automatic start of the Agent on Windows [acf368c](https://github.com/DataDog/dd-agent/commit/5877fdf0f18911c9ead6c101d24b31f19acf368c)
* [BUGFIX] Fix Gunicorn check issue where it was failing to identify the process in some cases [#706](https://github.com/DataDog/dd-agent/issues/706)
* [BUGFIX] Don’t fail on archived builds in Jenkins check [#766](https://github.com/DataDog/dd-agent/pull/766) (Thanks [@imlucas](https://github.com/imlucas))

#### Details
https://github.com/DataDog/dd-agent/compare/4.0.2...4.1.0

# 4.0.2 / 2014-01-08

**Windows Only**

#### Changes
* [BUGFIX] Fix WMI Check

#### Details
https://github.com/DataDog/dd-agent/compare/4.0.0...4.0.2



# 4.0.1 / 2013-12-17

**Linux or Source Install only**

#### Changes
* [BUGFIX] Fix Postgresql check that was sending bad values in some cases.
* [BUGFIX] Fix replication lag calculation in MySql check.

#### Details
https://github.com/DataDog/dd-agent/compare/4.0.0...4.0.1

# 4.0.0 / 2013-12-16

**This is a major version. See platform-specific pages for detailed changes.**

#### Changes
- [FEATURE] Linux/Mac OS/Source install: Visit https://github.com/DataDog/dd-agent/wiki/Agent-4.0.0-for-Linux-,-Mac-OS-and-FreeBSD
- [FEATURE] Windows: Visit https://github.com/DataDog/dd-agent/wiki/Agent-4.0.0-for-Windows

#### Details
https://github.com/DataDog/dd-agent/compare/3.10.1...4.0.0

# 3.10.1 / 2013-11-06

**Linux or Source Install only**

#### Changes
* [BUGFIX] Fix Mongo Integration for newer versions of MongoDB [#677](https://github.com/DataDog/dd-agent/issues/677)
* [BUGFIX] Fix memory metrics for Mac Os X Mavericks
* [BUGFIX] Fix tagging issues for HTTP Check [8ab75](d1e09e3605f7c09177c5a6fb4f3e2b86a698ab75)
* [BUGFIX] Fix local issues  [4230](https://github.com/DataDog/dd-agent/commit/0d41c241a763bf8edbbb3419cda43f3ba1ad4230)

#### Details
https://github.com/DataDog/dd-agent/compare/3.10.0...3.10.1

# 3.11.0 / 2013-10-08

**Windows Only**

### Integrations Affected
* Cassandra
* Tomcat
* ActiveMQ
* SolR
* Java
* MySQL
* Riak

#### Changes
* [FEATURE] Make Cassandra, Tomcat, ActiveMQ, SolR, Java and MySQL integrations work on Windows
* [FEATURE] Make pup work on Windows
* [FEATURE] Add an additional metric to the Nginx integration [#665](https://github.com/DataDog/dd-agent/pull/665) (Thanks to [@dcrosta](https://github.com/dcrosta))
* [FEATURE] Add additional metrics to Riak metrics [#643](https://github.com/DataDog/dd-agent/pull/643) (Thanks to [@stefan-mees](https://github.com/stefan-mees))
* [BUGFIX] Fix Service checks on Windows  [#632](https://github.com/DataDog/dd-agent/issues/632)

#### Details
https://github.com/DataDog/dd-agent/compare/3.9.3...3.11.0

# 3.9.3 / 2013-09-11

**Windows Only**

### Integrations Affected
* SQL Server

#### Changes
* [FEATURE] Allow optional custom tags in SQL Server check ([#654](https://github.com/DataDog/dd-agent/pull/654))
* [BUGFIX] Fix log file location on Windows XP

#### Details
https://github.com/DataDog/dd-agent/compare/3.9.2...3.9.3


# 3.10.0 / 2013-09-06

**Linux or Source Install only**

### Integrations Affected
* HTTP Check
* Mongo
* MySQL
* Network
* Process

#### Changes
* [FEATURE] GUnicorn check [#619](https://github.com/DataDog/dd-agent/pull/619)
* [FEATURE] Dogstatsd Autorestart [#624](https://github.com/DataDog/dd-agent/pull/624)
* [FEATURE] Add tags to metrics collected by the HTTP Check  [#647](https://github.com/DataDog/dd-agent/pull/647) (Thanks to [@ordenull](https://github.com/ordenull))
* [FEATURE] Allow MySQL check configuration via a MySQL config file [#590](https://github.com/DataDog/dd-agent/pull/590) (Thanks to [@micktwomey](https://github.com/micktwomey))
* [FEATURE] Filter disk, io & network metrics by device [#615](https://github.com/DataDog/dd-agent/pull/615)
* [FEATURE] Collect metrics from the MongoDB database selected in the connection string [#657](https://github.com/DataDog/dd-agent/pull/657)
* [FEATURE] Add CPU and thread utilisation metrics to the Process check [#646](https://github.com/DataDog/dd-agent/pull/646) (Thanks to [@morskoyzmey](https://github.com/morskoyzmey))
* [BUGFIX] Add a timeout to the Mongo connection [#627](https://github.com/DataDog/dd-agent/issues/627)

#### Details
https://github.com/DataDog/dd-agent/compare/3.9.0...3.10.0


# 3.9.2 / 2013-08-29

**Windows Only**

### Integrations Affected
* SQL Server

#### Changes
* [FEATURE] Default SQL Server to integrated security if no username/password is provided ([#622](https://github.com/DataDog/dd-agent/pull/622
))(Thanks to [@jamescrowley](https://github.com/jamescrowley))
* [FEATURE] Allow skipping ssl certificate validation (useful when the agent runs behind haproxy)  ([#641](https://github.com/DataDog/dd-agent/issues/641))
* [BUGFIX] Fix proxy support on Windows
* [BUGFIX] Better management of config files with the GUI

#### Details
https://github.com/DataDog/dd-agent/compare/3.9.1...3.9.2

# 3.9.1 / 2013-08-19

**Windows Only**

### Integrations Affected
* SQL Server
* IIS

#### Changes
* [FEATURE] Add a Management GUI to the Windows Agent for service and check management
* [FEATURE] Log to a log file (located in C:\ProgramData\Datadog\logs )
* [FEATURE] Create shortcuts in the Start Menu
* [BUGFIX] Fix status page
* [BUGFIX] Fix logging in the event viewer and only logs errors ([#496](https://github.com/DataDog/dd-agent/issues/496))
* [BUGFIX] Add debug info in the sql server check ([#608](https://github.com/DataDog/dd-agent/issues/608))
* [BUGFIX]IIS: By default use _Total, but allow a configurable list of sites ([6885a97bc](https://github.com/DataDog/dd-agent/commit/00053a5397581d88f29803e3f3e01276885a97bc))

#### Details
https://github.com/DataDog/dd-agent/compare/3.9.0...3.9.1


# 3.9.0 / 2013-08-05

### Integrations Affected
* HDFS
* Postgres
* MySQL
* Jenkins
* Nginx
* RedisDB

#### Changes
* [FEATURE] New HDFS check added ([#551](https://github.com/DataDog/dd-agent/pull/551)) (thanks to [@dcrosta][])
* [FEATURE] New Directory check added ([#581](https://github.com/DataDog/dd-agent/pull/581)) (thanks to [@brettlangdon][])
* [FEATURE] Events can now be sent to the Agent DogStatsD server from supported client libraries ([#532](https://github.com/DataDog/dd-agent/pull/532))
* [FEATURE] HTTP check now supports custom headers ([#541](https://github.com/DataDog/dd-agent/issues/541)) (thanks to [@tomduckering][])
* [FEATURE] Optional `response_time` metric has been added to TCP and HTTP checks
* [FEATURE] `info` command will exit with a non-zero value when errors were displayed by the command
* [FEATURE] Basic Jenkins metrics are now collected by Jenkins check ([#567](https://github.com/DataDog/dd-agent/issues/567))
* [FEATURE] A non-default port can now be specified in the MySQL check ([#575](https://github.com/DataDog/dd-agent/issues/575))
* [FEATURE] Logs now follow The BSD syslog Protocol ([#577](https://github.com/DataDog/dd-agent/issues/577))
* [BUGFIX] Expat XML Parser dependency is now installed by SmartOS Agent installation script ([#450](https://github.com/DataDog/dd-agent/issues/450))
* [BUGFIX] Fix collection of Postgres `rollbacks` metric
* [BUGFIX] Fix Postgres integration crashing when tags are None
* [BUGFIX] Fix version detection in MySQL check ([#558](https://github.com/DataDog/dd-agent/issues/558))
* [BUGFIX] MySQL InnoDB metrics are now only collected with InnoDB is enabled ([#566](https://github.com/DataDog/dd-agent/issues/566))
* [BUGFIX] The source `status` and `info` commands will no longer attempt to start the Agent ([#512](https://github.com/DataDog/dd-agent/issues/512))
* [BUGFIX] Upon a failed EC2 metadata lookup, the last successfully collected metadata will now be report ([#554](https://github.com/DataDog/dd-agent/issues/554))
* [BUGFIX] Nginx check no longer asserts number of connections ([#569](https://github.com/DataDog/dd-agent/issues/569))
* [BUGFIX] Deb and RPM `start` command will now poll the Agent status when starting instead of waiting a fixed amount of time ([#582](https://github.com/DataDog/dd-agent/issues/582))
* [BUGFIX] RedisDB check will now cast a parsed port to an integer ([#600](https://github.com/DataDog/dd-agent/pull/600))
* [BUGFIX] `supervisord` location is no longer hardcoded on Debian ([#580](https://github.com/DataDog/dd-agent/issues/580)) (Thanks to [@mastrolinux][])

#### Details
https://github.com/DataDog/dd-agent/compare/3.8.0...3.9.0


# 3.8.0 / 2013-06-19

#### Changes
* [FEATURE] Add status command to Debian
* [FEATURE] Debian version now uses its own supervisor config instead of using the system config
* [FEATURE] Add `-v` option to info command, which currently gives stack traces for errors that occurred during checks
* [FEATURE] Add I/O metrics to OS X ([#131](https://github.com/DataDog/dd-agent/issues/131))
* [BUGFIX] Log exception when dogstatsd server fails to start ([#480](https://github.com/DataDog/dd-agent/issues/480))
* [BUGFIX] Fix `Error: Invalid user name dd-agent` appearing during source install ([#521](https://github.com/DataDog/dd-agent/issues/521))
* [BUGFIX] Debian and Red Hat init.d scripts now verify that `/etc/dd-agent/datadog.conf` is present before launching supervisor([#544](https://github.com/DataDog/dd-agent/issues/544))
* [BUGFIX] Fix AttributeErrors for `timeout_event` and `status_code_event` in Riak check ([#546](https://github.com/DataDog/dd-agent/pull/546))

#### Details
https://github.com/DataDog/dd-agent/compare/3.7.2...3.8.0

# 3.7.2 / 2013-05-22

* [FEATURE] Fix redis check when used with additional tags ([#515](https://github.com/DataDog/dd-agent/issues/515))

#### Details
https://github.com/DataDog/dd-agent/compare/3.7.1...3.7.2

# 3.7.1 / 2013-05-21

#### Changes
* [FEATURE] Add basic auth support for apache check ([#410](https://github.com/DataDog/dd-agent/issues/410))
* [FEATURE] Support any redis parameter during the connection ([#276](https://github.com/DataDog/dd-agent/issues/276))
* [FEATURE] Better launching script for source install
* [BUGFIX] Fix process check (Missing import and support version 0.4 of psutil) ([#502](https://github.com/DataDog/dd-agent/issues/502))
* [BUGFIX] Fix JVM Heap issue when launching java process ( Disable memory consumption watcher by default) ([#507](https://github.com/DataDog/dd-agent/issues/507))
* [BUGFIX] Info page shows errors when failing to initialize a check.d ([#427](https://github.com/DataDog/dd-agent/issues/427))
* [BUGFIX] Added file option to supervisorctl stop arg too ([#498](https://github.com/DataDog/dd-agent/pull/498)) (Thanks to [@mastrolinux](https://github.com/mastrolinux))
* [BUGFIX] Fix mysql version detection ([#501](https://github.com/DataDog/dd-agent/issues/501))

#### Details
https://github.com/DataDog/dd-agent/compare/3.7.0...3.7.1

# 3.7.0 / 2013-05-08

#### Changes
* [FEATURE] Restart the agent if it uses too much memory ([#426](https://github.com/DataDog/dd-agent/pull/429)) (Thanks to [@echohead](https://github.com/echohead))
* [FEATURE] Port Memcache to checks.d ([#390](https://github.com/DataDog/dd-agent/pull/439))
* [FEATURE] Add a process memory check ([#434](https://github.com/DataDog/dd-agent/pull/434)) (Thanks to [@mastrolinux](https://github.com/mastrolinux))
* [FEATURE] Add a gearman check ([#435](https://github.com/DataDog/dd-agent/pull/429)) (Thanks to [@CaptTofu](https://github.com/CaptTofu))
* [FEATURE] Add a Web Info Page to check the status of the agent (http://localhost:17125/status) ([#483](https://github.com/DataDog/dd-agent/pull/483))
* [FEATURE] Create an info page for the source install ([#481](https://github.com/DataDog/dd-agent/pull/481))
* [FEATURE] Add a “warning” method to the AgentCheck class that will display warnings in the info page
* [BUGFIX] Customizable Java directory for JMX Checks ([#472](https://github.com/DataDog/dd-agent/issues/472))
* [BUGFIX] Do not try to write logs in /var/log when using the source install ([#478](https://github.com/DataDog/dd-agent/issues/478))
* [BUGFIX] Use a Unix socket in supervisor for the source installation
* [BUGFIX]  Display more information when the agent stops because there is no valid hostname  ([#475](https://github.com/DataDog/dd-agent/issues/475))

#### Details
https://github.com/DataDog/dd-agent/compare/3.6.4...3.7.0

# 3.6.4 / 2013-04-25

**Windows only**

### Bug fixes
* IIS: Use Total metrics and calculate rates in the Agent instead of using PerSec metrics. ([#465](https://github.com/DataDog/dd-agent/pull/465))
* IIS: Optionally give a list of sites to pull metrics from, defaulting to all.

#### Details
https://github.com/DataDog/dd-agent/compare/3.6.3...3.6.4

# 3.6.3 / 2013-04-14

#### Changes
* [BUGFIX} Customizable field names for cacti check ([#404](https://github.com/DataDog/dd-agent/issues/404))
* [BUGFIX} Enable replication monitoring by default for old style check configuration for mysql
* [BUGFIX} Always collect metrics for config specified queues/nodes for rabbitmq

#### Details
https://github.com/DataDog/dd-agent/compare/3.6.2...3.6.3

# 3.6.2 / 2013-04-05

#### Changes
* [FEATURE] Port MySQL to checks.d ([#408](https://github.com/DataDog/dd-agent/pull/408)) (Thanks to [@CaptTofu](https://github.com/CaptTofu))
* [FEATURE] Add KyotoTycoon Check ([#426](https://github.com/DataDog/dd-agent/pull/426)) (Thanks to [@dcrosta](https://github.com/dcrosta))
* [FEATURE] Add command line option to run a particular agent check ([#408](https://github.com/DataDog/dd-agent/pull/417))
* [BUGFIX} Force include elementtree.ElementTree in Windows install ([#423](https://github.com/DataDog/dd-agent/issues/423))
* [BUGFIX} Fix elasticsearch check for version < 0.19 ([#419](https://github.com/DataDog/dd-agent/issues/419))
* [BUGFIX} Disable HAProxy events by default
* [BUGFIX} Aggregate RabbitMq Metrics over queues and nodes
* [BUGFIX} Better hostname detection
* [BUGFIX} Fix broken json serialization in centos5 ([#422](https://github.com/DataDog/dd-agent/issues/422))

#### Details
https://github.com/DataDog/dd-agent/compare/3.6.1...3.6.2

# 3.6.1 / 2013-03-21

#### Changes
* [FEATURE] Port Jenkins to checks.d
* [FEATURE] Lighttpd check now supports Lighttpd 2.0 ([#412](https://github.com/DataDog/dd-agent/pull/412)) (Thanks to [@brettlangdon](https://github.com/brettlangdon))
* [FEATURE]Additional configurable checks.d directory ([#413](https://github.com/DataDog/dd-agent/pull/413)) (Thanks to [@brettlangdon](https://github.com/brettlangdon))
* [BUGFIX] Better Jenkins check performance (reduce CPU consumption) ([#402](https://github.com/DataDog/dd-agent/issues/402))
* [BUGFIX] Fix Graphite listener ([#415](https://github.com/DataDog/dd-agent/issues/415))
* [BUGFIX] Less logging for pup ([#414](https://github.com/DataDog/dd-agent/issues/414))

#### Details
https://github.com/DataDog/dd-agent/compare/3.6.0...3.6.1

# 3.6.0 / 2013-03-13

#### Changes
* [FEATURE] The agent can now run behind a web proxy ([#377](https://github.com/DataDog/dd-agent/pull/377))
* [FEATURE] MongoDB now supports multiple instances running on the same host ([#397](https://github.com/DataDog/dd-agent/pull/397))
* [FEATURE] Additional network metrics ([#396](https://github.com/DataDog/dd-agent/pull/396))
* [FEATURE] lighttpd check ([#385](https://github.com/DataDog/dd-agent/pull/385))
* [FEATURE] Allow pup to bind to a specific interface ([#394](https://github.com/DataDog/dd-agent/pull/394)). Thanks to [@shamada-kuuluu][]
* [FEATURE] Add a partial response in HTTP Check ([#375](https://github.com/DataDog/dd-agent/pull/375)). Thanks to [@dcrosta][]
* [FEATURE] WMI checks support advanced configuration ([#359](https://github.com/DataDog/dd-agent/pull/359))
* [FEATURE] More reliable and consistent hostname detection ([84e715c](https://github.com/DataDog/dd-agent/commit/84e715c90d806f92667640d5647bc07194b36d71))
* [BUGFIX] Better retry handling for JMX checks ([#369](https://github.com/DataDog/dd-agent/issues/369))
* [BUGFIX]  Fix JMX Python 2.4 support ([#401](https://github.com/DataDog/dd-agent/issues/401))

#### Details
https://github.com/DataDog/dd-agent/compare/3.5.1...3.6.0

# 3.5.1
This is a **RedHat-only** release.

* [BUGFIX] Fix dogstatsd crash on RedHat 5.x and its derivatives ([#381](https://github.com/DataDog/dd-agent/pull/381))

#### Details
https://github.com/DataDog/dd-agent/compare/3.5.0...3.5.1

# 3.5.0

#### Changes
* [FEATURE] Logging overhaul: Consistent locations in `/var/log/datadog/`, defaults to INFO level ([#297](https://github.com/DataDog/dd-agent/pull/297))
* [FEATURE] Add more memcached metrics ([#283](https://github.com/DataDog/dd-agent/pull/283)). Thanks to [@jkoppe][]
* [FEATURE] RabbitMQ integration ([#330](https://github.com/DataDog/dd-agent/pull/330)). Thanks to [@brettlangdon][]
* [FEATURE] Riak integration ([#332](https://github.com/DataDog/dd-agent/pull/332)). Thanks to [@stefan-mees][]
* [FEATURE] Allow source file and line in Cassandra system.log. ([#307](https://github.com/DataDog/dd-agent/pull/307))
* [FEATURE] Port CouchDB and ElasticSearch to checks.d ([#311](https://github.com/DataDog/dd-agent/pull/311))
* [FEATURE] New System Metrics: `system.mem.pct_usable` and `system.swap.pct_free` ([#334](https://github.com/DataDog/dd-agent/pull/334))
* [FEATURE] SmartOS support (see [the agent setup page](https://app.datadoghq.com/account/settings#agent))
* [FEATURE] Invoke custom emitters from the forwarder, instead of the agent, to capture statsd output ([#271](https://github.com/DataDog/dd-agent/pull/272). Thanks to [@charles-dyfis-net][])
* [FEATURE] Allow strings to be elements in dogstatsd sets ([#300](https://github.com/DataDog/dd-agent/issues/326))
* [BUGFIX] Limit the number of threads used by service checks ([#351](https://github.com/DataDog/dd-agent/issues/351))
* [PERFORMANCE] Better JMX performance ([#313](https://github.com/DataDog/dd-agent/issues/313), [#348](https://github.com/DataDog/dd-agent/issues/348))
* [BUGFIX] Fix names of some Apache metrics ([#326](https://github.com/DataDog/dd-agent/issues/326))

#### Details
https://github.com/DataDog/dd-agent/compare/3.4.4...3.5.0

# 3.4.4

#### Changes
* [BUGFIX] Fix memory leaks in redis check, and potentially in custom checks.d checks that supply duplicate tags ([#325](https://github.com/DataDog/dd-agent/issues/325))
* [BUGFIX] Fix mongo auth issue ([#318](https://github.com/DataDog/dd-agent/issues/318))
* [BUGFIX] Add configurable socket timeout to zookeeper check ([#310](https://github.com/DataDog/dd-agent/issues/310))

# 3.4.3

#### Changes
* [BUGFIX] Fix memory leaks in memcache check ([#278](https://github.com/DataDog/dd-agent/issues/278))
* [BUGFIX] Fix umask issue ([#293](https://github.com/DataDog/dd-agent/issues/293))
* [BUGFIX] Fix bad error message in CentOS 5 installation ([#320](https://github.com/DataDog/dd-agent/issues/320))

#### Details
https://github.com/DataDog/dd-agent/compare/3.4.2...3.4.3

# 3.4.2

**If you're having issues upgrading, please read the [upgrade notes](https://github.com/DataDog/dd-agent/wiki/Upgrade-Notes)**

#### Changes
* [FEATURE] Check multiple Cassandra, Tomcat and Solr instances per host
* [FEATURE] Added a `JMXCheck` base class which can be used to easily track metrics from services that support JMX.
* [BUGFIX] Create `/etc/dd-agent/conf.d` on install
* [BUGFIX] Reduce verbosity of the logs

#### Details
https://github.com/DataDog/dd-agent/compare/3.4.1...3.4.2

# 3.4.1

#### Changes
* [FEATURE] Added an `info` command  (`sudo /etc/init.d/datadog-agent info`) which prints status info about the agent processes.
* [FEATURE] Added a check for [Zookeeper](http://zookeeper.apache.org/).
* [BUGFIX] Fixes packaging bugs introduced in 3.4.0.
* [BUGFIX] Agents installed with RPM will restart on upgrade (starting with the next version).
* [BUGFIX] Fixed normalized counter rounding error.
* [BUGFIX] By default, don't open ports other than localhost.

#### Details
https://github.com/DataDog/dd-agent/compare/3.4.0...3.4.1


## 3.4.0 / 2012-11-28

#### Changes
* [FEATURE] Added FreeBSD support, thanks to [@loris][].
* [FEATURE] Removed `datadog-agent` and `datadog-agent-base` dependencies. Now you only install one package per machine (instructions are the same).
* [FEATURE] The agent now compresses payloads sent over the wire.
* [FEATURE] Allow custom `PYTHONPATH` in checks.d config ([#227][])
* [FEATURE] Added new Redis metrics.
* [FEATURE] Added normalized load, that is load per cpu.
* [FEATURE] Port Apache, NginX and Varnish checks to checks.d.
* [BUGFIX] [#290][], [#291][] - disable non-local traffic by default, suppress stack traces in 404s
* [BUGFIX] [#257][] - More useful Apache rates not averaged from the beginning of time.
* [BUGFIX] [#277][] - Run dogstatsd on older debian boxes.
* [BUGFIX] [#245][] - Expire counter values.
* [BUGFIX] [#261][] - Fix Windows checks.d location lookup.
* [BUGFIX] [#253][] - Sum Dogstream counters.
* [PERFORMANCE] Improved dogstatsd performance.
* [ENHANCEMENT] Stylistic code improvements.

#### Details
https://github.com/DataDog/dd-agent/compare/3.3.0...3.4.0

## 3.3.0 / 2012-10-25

### New Features

#### Changes
* [FEATURE] Added HTTP and TCP Service Checks ([read the docs](http://docs.datadoghq.com/guides/services_checks/))
* [FEATURE] Added the Windows Event Log Integration
* [PERFORMANCE] Use the _much_ faster simplejson library, if it's available, otherwise use the standard json library.
* [BUGFIX] Fixed disk space metrics bug
* [BUGFIX] Run dogstatsd on older OS's as well.
* [BUGFIX] Fixed host aliasing issue.
* [BUGFIX] Use a better query to get the Cacti device name.
* [BUGFIX] Ensure pup uses the same JSON parsing library as the rest of the application.

#### Details
https://github.com/DataDog/dd-agent/compare/3.2.3...3.3.0

## 3.2.3 / 2012-10-15

#### Changes
* [FEATURE] Windows support is officially added.
* [FEATURE] Added a SQL Server check.
* [FEATURE] Added an IIS check.
* [FEATURE] Track request_rate in HAProxy.
* [FEATURE] Move DogstatsD to the `datadog-agent-base` package.

#### Details
https://github.com/DataDog/dd-agent/compare/3.2.2...3.2.3

# 3.2.2 / 2012-10-05

#### Changes
* [BUGFIX] Fixes an issue with events in checks.d where only events from the last instance would be sent.

#### Details
https://github.com/DataDog/dd-agent/compare/3.2.1...3.2.2

# 3.2.1 / 2012-10-05

#### Changes
* [BUGFIX] Fixes an issue with duplicate events being created in `checks.d` checks.

#### Details
https://github.com/DataDog/dd-agent/compare/3.2.0...3.2.1

## 3.2.0 / 2012-10-05

#### Changes
* [FEATURE] Add new AgentCheck interface for all future checks.
* [FEATURE] Split checks and configuration with `checks.d`/`conf.d`.

#### Details
https://github.com/DataDog/dd-agent/compare/3.1.7...3.2.0

# 3.1.7 / 2012-09-28

#### Changes
* [BUGFIX] Fixes the case where you have the `python-redis` module and the check will run with default host/port even if you don't have any redis configuration. Fixes case [#200](https://github.com/DataDog/dd-agent/issues/200).

#### Details
https://github.com/DataDog/dd-agent/compare/3.1.6...3.1.7

# 3.1.6 / 2012-09-27

#### Changes
* [BUGFIX] Fixes memcached integration bug running under Python 2.4 [#201](https://github.com/DataDog/dd-agent/issues/201)
* [BUGFIX] Removes token from the Cassandra Stats, because it is not always a number. Fixes case [#202](https://github.com/DataDog/dd-agent/issues/202)

#### Details
https://github.com/DataDog/dd-agent/compare/3.1.5...3.1.6

# 3.1.5 / 2012-09-21

#### Changes
* [BUGFIX] Fixes network traffic reporting bug introduced in 3.1.4. If you're running 3.1.4 we recommended that you upgrade.

#### Details
https://github.com/DataDog/dd-agent/compare/3.1.4...3.1.5

# 3.1.4 / 2012-09-21

#### Changes
* [FEATURE] memcached and nginx checks now support multiple instances per host.
* [FEATURE] Statsd: Added `sets` metric type. Read the [docs](http://docs.datadoghq.com/guides/metrics/#sets).
* [FEATURE] Statsd: Now supports multiple metrics per packet.
* [FEATURE] Some under the hood work to support more platforms.
* [FEATURE] Bug fixes
* [BUGFIX] Fixes invalid configuration parsing in the case of pure JVM metrics.

#### Details
https://github.com/DataDog/dd-agent/compare/3.1.3...3.1.4

# 3.1.3

#### Changes
* [BUGFIX] Fixes invalid configuration parsing in the case of pure JVM metrics.

# 3.1.2

#### Changes
* [FEATURE] Dogstream (parsing logs with dd-agent) supports parsing classes in addition to parsing functions.

# 3.1.1

#### Changes
* [FEATURE] Multi-instance JMX check
* [FEATURE] dogstatsd counters now send 0 for up to 10 minutes after the last increment(). They work with alerts.
* [BUGFIX] [part 1 of [#16][]5](https://github.com/DataDog/dd-agent/issues/165) dogstatsd's average is fixed
* [BUGFIX] HAProxy logging level was logging debug messages by default.

# 3.1.0

#### Changes
* [FEATURE] Deploy Pup along with the Agent (though Pup doesn't run on CentOS 5)
* [FEATURE] Added a one line install script
* [FEATURE] HAProxy integration
* [BUGFIX] Run the Agent on Redhat reboots
* [BUGFIX] [#150](https://github.com/DataDog/dd-agent/issues/150) - Fix Pexpect dependency
* [BUGFIX] Small fixes to the HAProxy and Elastic Search integrations.
* [BUGFIX] Fixed a couple of host aliasing issues.

### Notes

* This version depends on Supervisor version 3 instead of version 2.3.
* [changeset](https://github.com/DataDog/dd-agent/compare/3.0.5...3.1.0)

# 3.0.5

#### Changes
* [BUGFIX] Incorrect version dependencies between `datadog-agent` and `datadog-agent-base`.
* [BUGFIX] [#130](https://github.com/DataDog/dd-agent/issues/130) Fixes a crash when changing the listening port of the forwarder.

### How to upgrade from 3.0.4 on Debian and Ubuntu

When we released datadog-agent 3.0.4 we made a mistake and messed up the version dependency between packages. As a result, whenever you run `apt-get upgrade` or `apt-get dist-upgrade` and 3.0.4 is installed you may get the following error:

`E: Couldn't configure pre-depend datadog-agent-base for datadog-agent, probably a dependency cycle.`

If that's the case, don't panic: there is a simple fix. Simply run:

    sudo apt-get update
    sudo apt-get remove datadog-agent
    sudo apt-get install datadog-agent

to get the new versions up-and-running.

# 3.0.4

#### Changes
* [FEATURE] [#112](https://github.com/DataDog/dd-agent/issues/112) Thanks to [@charles-dyfis-net](https://github.com/charles-dyfis-net), the agent supports extra `emitters`. An emitter is an output for events and metrics.
* [FEATURE] [#117](https://github.com/DataDog/dd-agent/issues/117) Thanks to [@rl-0x0](https://github.com/rl-0x0), the agent can now parse supervisord logs and turn them into events and metrics.
* [FEATURE] [#121](https://github.com/DataDog/dd-agent/issues/121) Thanks to [@charles-dyfis-net](https://github.com/charles-dyfis-net), the agent supports custom checks. Check out our README for more details.

# 3.0.3

#### Changes
* [BUGFIX] [#82](https://github.com/DataDog/dd-agent/issues/82) Now proudly runs on Amazon Web Services Linux.
* [FEATURE] [#110](https://github.com/DataDog/dd-agent/issues/110) More ElasticSearch metrics

# 3.0.2

#### Changes
* [BUGFIX] [#105](https://github.com/DataDog/dd-agent/issues/105) Fix for ElasticSearch 0.18

# 3.0.1

#### Changes
* [BUGFIX] Support for ElasticSearch 0.18
* [BUGFIX] [#95](https://github.com/DataDog/dd-agent/issues/95) Fix for incorrect supervisord configuration on debian. More details [here](https://github.com/DataDog/dd-agent/wiki/How-to-fix-supervisor) to test whether you are affected.

# 3.0.0

* **This is a major version**
#### Changes
* [FEATURE] [dogstatsd](http://api.datadoghq.com/guides/dogstatsd), a drop-in replacement of statsd with tagging magic, bundled with the agent. Compatible with all statsd clients.
* [FEATURE] [#21](https://github.com/DataDog/dd-agent/issues/21) Support for ElasticSearch 0.19

# 2.2.28

#### Changes
* [FEATURE] [#83](https://github.com/DataDog/dd-agent/issues/83) Support authenticated connections to redis. Simply use the following stanza in `/etc/dd-agent/datadog.conf` to support multiple servers

    redis_urls: host:port, password[@host][]:port

# 2.2.27

#### Changes
* [BUGFIX] [#80](https://github.com/DataDog/dd-agent/issues/80) Agent now runs happily in locales with different radix separator
* [FEATURE] [#73](https://github.com/DataDog/dd-agent/issues/73) Allow checks to record tag metrics

# 2.2.26

#### Changes
* [BUGFIX][#76](https://github.com/DataDog/dd-agent/issues/76) Fixes nagios perfdata parsing (if templates contained brackets)

# 2.2.25

#### Changes
* [BUGFIX] [#68](https://github.com/DataDog/dd-agent/issues/68) Fixes off-by-one dog parsing error
* [BUGFIX] [#65](https://github.com/DataDog/dd-agent/issues/65) More robust uninstall script on Debian & Ubuntu
* [FEATURE] [#71](https://github.com/DataDog/dd-agent/issues/71) Supports for network metrics on Mac OS X
* [FEATURE] [#62](https://github.com/DataDog/dd-agent/issues/62) Sends instance-related EC2 metadata to Datadog to enable host aliases

# 2.2.24

#### Changes
* [BUGFIX] fixes used memory metric
* [BUGFIX] fixes mongo support on Ubuntu 11.10 (with pymongo 1.11)
* [BUGFIX] fixes IO metrics on Ubuntu 12.04 (thanks [@dcrosta][])

# 2.2.22

#### Changes
* [FEATURE] Supports Varnish 2.x

# 2.2.21

If you use ganglia, you want this version.

#### Changes
* [PERFORMANCE] major ganglia speedup, getting telnetlib out of the equation

# 2.2.20

#### Changes
* [BUGFIX] fixes MongoDB support, broken in 2.2.19.

# 2.2.19

#### Changes
* [BUGFIX] varnish support is now xml-based, to not break when reading bitmap values ([#42][])
* [BUGFIX] less verbose errors in dogstream ([#55][])
* [FEATURE] Now capturing master/slave changes in Mongo

# 2.2.18

#### Changes
* [BUGFIX] When using `use_ec2_instance_id: yes` on a non-ec2 box, don't hang! (introduced with 2.2.17)
* [FEATURE] Initial Varnish support

# 2.2.17

#### Changes
* [BUGFIX] On CentOS, pid was always saved in /tmp/dd-agent.pid ([#51][])
* **CONFIGURATION CHANGE**: When running on EC2, the instance id will be used in lieu of the hostname, unless `use_ec2_instance_id` is set no `no`.

# 2.2.16

#### Changes
* [FEATURE] Agent auto-detects the fact that it is running on Amazon EC2
* [FEATURE] Agent supports [custom event parsers](wiki/Log-Parsing)

# 2.2.15

#### Changes
* [BUGFIX] Fixes MongoDB configuration parsing.

# 2.2.14

#### Changes
* [BUGFIX] Used memory was not reported on 2.2.12 when running the agent on Debian Lenny.
* [BUGFIX] Cacti memory is reported in MB, not in bytes.

# 2.2.12

#### Changes
* [BUGFIX] Cacti check should fail gracefully if it cannot find RRD files.

# 2.2.11

#### Changes
* [BUGFIX] Prevent counters from wrapping ([#23](/DataDog/dd-agent/pull/30))
* [BUGFIX] Collect shared memory metric, accessible in Datadog via system.mem.shared.

# 2.2.10

#### Changes
* [BUGFIX] On CentOS5, when both `datadog-agent` and `datadog-agent-base` are installed, `datadog-agent-base` runs with the stock 2.4 python, which allows python modules that support integrations (e.g. mysql) to be installed with yum.

# 2.2.9 (minor)

#### Changes
* [FEATURE] Added support for [cacti](http://www.cacti.net)
* [FEATURE] Added support for new memory metrics: `system.mem.buffers`, `system.mem.cached`, `system.mem.buffers`, `system.mem.usable`, `system.mem.total`

#### Details
  https://github.com/DataDog/dd-agent/issues?milestone=1&state=closed

<!--- The following link definition list is generated by PimpMyChangelog --->
[#16]: https://github.com/DataDog/dd-agent/issues/16
[#21]: https://github.com/DataDog/dd-agent/issues/21
[#23]: https://github.com/DataDog/dd-agent/issues/23
[#30]: https://github.com/DataDog/dd-agent/issues/30
[#42]: https://github.com/DataDog/dd-agent/issues/42
[#51]: https://github.com/DataDog/dd-agent/issues/51
[#55]: https://github.com/DataDog/dd-agent/issues/55
[#62]: https://github.com/DataDog/dd-agent/issues/62
[#65]: https://github.com/DataDog/dd-agent/issues/65
[#68]: https://github.com/DataDog/dd-agent/issues/68
[#71]: https://github.com/DataDog/dd-agent/issues/71
[#72]: https://github.com/DataDog/dd-agent/issues/72
[#73]: https://github.com/DataDog/dd-agent/issues/73
[#76]: https://github.com/DataDog/dd-agent/issues/76
[#80]: https://github.com/DataDog/dd-agent/issues/80
[#82]: https://github.com/DataDog/dd-agent/issues/82
[#83]: https://github.com/DataDog/dd-agent/issues/83
[#95]: https://github.com/DataDog/dd-agent/issues/95
[#105]: https://github.com/DataDog/dd-agent/issues/105
[#110]: https://github.com/DataDog/dd-agent/issues/110
[#112]: https://github.com/DataDog/dd-agent/issues/112
[#117]: https://github.com/DataDog/dd-agent/issues/117
[#121]: https://github.com/DataDog/dd-agent/issues/121
[#130]: https://github.com/DataDog/dd-agent/issues/130
[#131]: https://github.com/DataDog/dd-agent/issues/131
[#150]: https://github.com/DataDog/dd-agent/issues/150
[#165]: https://github.com/DataDog/dd-agent/issues/165
[#200]: https://github.com/DataDog/dd-agent/issues/200
[#201]: https://github.com/DataDog/dd-agent/issues/201
[#202]: https://github.com/DataDog/dd-agent/issues/202
[#227]: https://github.com/DataDog/dd-agent/issues/227
[#245]: https://github.com/DataDog/dd-agent/issues/245
[#253]: https://github.com/DataDog/dd-agent/issues/253
[#257]: https://github.com/DataDog/dd-agent/issues/257
[#261]: https://github.com/DataDog/dd-agent/issues/261
[#271]: https://github.com/DataDog/dd-agent/issues/271
[#276]: https://github.com/DataDog/dd-agent/issues/276
[#277]: https://github.com/DataDog/dd-agent/issues/277
[#278]: https://github.com/DataDog/dd-agent/issues/278
[#283]: https://github.com/DataDog/dd-agent/issues/283
[#290]: https://github.com/DataDog/dd-agent/issues/290
[#291]: https://github.com/DataDog/dd-agent/issues/291
[#293]: https://github.com/DataDog/dd-agent/issues/293
[#297]: https://github.com/DataDog/dd-agent/issues/297
[#299]: https://github.com/DataDog/dd-agent/issues/299
[#300]: https://github.com/DataDog/dd-agent/issues/300
[#307]: https://github.com/DataDog/dd-agent/issues/307
[#310]: https://github.com/DataDog/dd-agent/issues/310
[#311]: https://github.com/DataDog/dd-agent/issues/311
[#313]: https://github.com/DataDog/dd-agent/issues/313
[#318]: https://github.com/DataDog/dd-agent/issues/318
[#320]: https://github.com/DataDog/dd-agent/issues/320
[#325]: https://github.com/DataDog/dd-agent/issues/325
[#326]: https://github.com/DataDog/dd-agent/issues/326
[#330]: https://github.com/DataDog/dd-agent/issues/330
[#332]: https://github.com/DataDog/dd-agent/issues/332
[#334]: https://github.com/DataDog/dd-agent/issues/334
[#348]: https://github.com/DataDog/dd-agent/issues/348
[#351]: https://github.com/DataDog/dd-agent/issues/351
[#359]: https://github.com/DataDog/dd-agent/issues/359
[#369]: https://github.com/DataDog/dd-agent/issues/369
[#375]: https://github.com/DataDog/dd-agent/issues/375
[#377]: https://github.com/DataDog/dd-agent/issues/377
[#381]: https://github.com/DataDog/dd-agent/issues/381
[#385]: https://github.com/DataDog/dd-agent/issues/385
[#390]: https://github.com/DataDog/dd-agent/issues/390
[#394]: https://github.com/DataDog/dd-agent/issues/394
[#396]: https://github.com/DataDog/dd-agent/issues/396
[#397]: https://github.com/DataDog/dd-agent/issues/397
[#401]: https://github.com/DataDog/dd-agent/issues/401
[#402]: https://github.com/DataDog/dd-agent/issues/402
[#404]: https://github.com/DataDog/dd-agent/issues/404
[#408]: https://github.com/DataDog/dd-agent/issues/408
[#410]: https://github.com/DataDog/dd-agent/issues/410
[#412]: https://github.com/DataDog/dd-agent/issues/412
[#413]: https://github.com/DataDog/dd-agent/issues/413
[#414]: https://github.com/DataDog/dd-agent/issues/414
[#415]: https://github.com/DataDog/dd-agent/issues/415
[#419]: https://github.com/DataDog/dd-agent/issues/419
[#422]: https://github.com/DataDog/dd-agent/issues/422
[#423]: https://github.com/DataDog/dd-agent/issues/423
[#426]: https://github.com/DataDog/dd-agent/issues/426
[#427]: https://github.com/DataDog/dd-agent/issues/427
[#434]: https://github.com/DataDog/dd-agent/issues/434
[#435]: https://github.com/DataDog/dd-agent/issues/435
[#450]: https://github.com/DataDog/dd-agent/issues/450
[#465]: https://github.com/DataDog/dd-agent/issues/465
[#472]: https://github.com/DataDog/dd-agent/issues/472
[#475]: https://github.com/DataDog/dd-agent/issues/475
[#478]: https://github.com/DataDog/dd-agent/issues/478
[#480]: https://github.com/DataDog/dd-agent/issues/480
[#481]: https://github.com/DataDog/dd-agent/issues/481
[#483]: https://github.com/DataDog/dd-agent/issues/483
[#490]: https://github.com/DataDog/dd-agent/issues/490
[#496]: https://github.com/DataDog/dd-agent/issues/496
[#498]: https://github.com/DataDog/dd-agent/issues/498
[#501]: https://github.com/DataDog/dd-agent/issues/501
[#502]: https://github.com/DataDog/dd-agent/issues/502
[#507]: https://github.com/DataDog/dd-agent/issues/507
[#512]: https://github.com/DataDog/dd-agent/issues/512
[#515]: https://github.com/DataDog/dd-agent/issues/515
[#521]: https://github.com/DataDog/dd-agent/issues/521
[#532]: https://github.com/DataDog/dd-agent/issues/532
[#541]: https://github.com/DataDog/dd-agent/issues/541
[#544]: https://github.com/DataDog/dd-agent/issues/544
[#546]: https://github.com/DataDog/dd-agent/issues/546
[#551]: https://github.com/DataDog/dd-agent/issues/551
[#554]: https://github.com/DataDog/dd-agent/issues/554
[#558]: https://github.com/DataDog/dd-agent/issues/558
[#566]: https://github.com/DataDog/dd-agent/issues/566
[#567]: https://github.com/DataDog/dd-agent/issues/567
[#569]: https://github.com/DataDog/dd-agent/issues/569
[#575]: https://github.com/DataDog/dd-agent/issues/575
[#577]: https://github.com/DataDog/dd-agent/issues/577
[#580]: https://github.com/DataDog/dd-agent/issues/580
[#581]: https://github.com/DataDog/dd-agent/issues/581
[#582]: https://github.com/DataDog/dd-agent/issues/582
[#590]: https://github.com/DataDog/dd-agent/issues/590
[#600]: https://github.com/DataDog/dd-agent/issues/600
[#608]: https://github.com/DataDog/dd-agent/issues/608
[#615]: https://github.com/DataDog/dd-agent/issues/615
[#619]: https://github.com/DataDog/dd-agent/issues/619
[#622]: https://github.com/DataDog/dd-agent/issues/622
[#624]: https://github.com/DataDog/dd-agent/issues/624
[#627]: https://github.com/DataDog/dd-agent/issues/627
[#632]: https://github.com/DataDog/dd-agent/issues/632
[#641]: https://github.com/DataDog/dd-agent/issues/641
[#643]: https://github.com/DataDog/dd-agent/issues/643
[#646]: https://github.com/DataDog/dd-agent/issues/646
[#647]: https://github.com/DataDog/dd-agent/issues/647
[#653]: https://github.com/DataDog/dd-agent/issues/653
[#654]: https://github.com/DataDog/dd-agent/issues/654
[#657]: https://github.com/DataDog/dd-agent/issues/657
[#665]: https://github.com/DataDog/dd-agent/issues/665
[#677]: https://github.com/DataDog/dd-agent/issues/677
[#706]: https://github.com/DataDog/dd-agent/issues/706
[#729]: https://github.com/DataDog/dd-agent/issues/729
[#730]: https://github.com/DataDog/dd-agent/issues/730
[#735]: https://github.com/DataDog/dd-agent/issues/735
[#752]: https://github.com/DataDog/dd-agent/issues/752
[#760]: https://github.com/DataDog/dd-agent/issues/760
[#766]: https://github.com/DataDog/dd-agent/issues/766
[#770]: https://github.com/DataDog/dd-agent/issues/770
[#780]: https://github.com/DataDog/dd-agent/issues/780
[#784]: https://github.com/DataDog/dd-agent/issues/784
[#787]: https://github.com/DataDog/dd-agent/issues/787
[#790]: https://github.com/DataDog/dd-agent/issues/790
[#806]: https://github.com/DataDog/dd-agent/issues/806
[#809]: https://github.com/DataDog/dd-agent/issues/809
[#810]: https://github.com/DataDog/dd-agent/issues/810
[#815]: https://github.com/DataDog/dd-agent/issues/815
[#826]: https://github.com/DataDog/dd-agent/issues/826
[#827]: https://github.com/DataDog/dd-agent/issues/827
[#834]: https://github.com/DataDog/dd-agent/issues/834
[#838]: https://github.com/DataDog/dd-agent/issues/838
[#844]: https://github.com/DataDog/dd-agent/issues/844
[#848]: https://github.com/DataDog/dd-agent/issues/848
[#849]: https://github.com/DataDog/dd-agent/issues/849
[#852]: https://github.com/DataDog/dd-agent/issues/852
[#863]: https://github.com/DataDog/dd-agent/issues/863
[#875]: https://github.com/DataDog/dd-agent/issues/875
[#876]: https://github.com/DataDog/dd-agent/issues/876
[#883]: https://github.com/DataDog/dd-agent/issues/883
[#887]: https://github.com/DataDog/dd-agent/issues/887
[#891]: https://github.com/DataDog/dd-agent/issues/891
[#893]: https://github.com/DataDog/dd-agent/issues/893
[#894]: https://github.com/DataDog/dd-agent/issues/894
[#899]: https://github.com/DataDog/dd-agent/issues/899
[#900]: https://github.com/DataDog/dd-agent/issues/900
[#904]: https://github.com/DataDog/dd-agent/issues/904
[#917]: https://github.com/DataDog/dd-agent/issues/917
[#919]: https://github.com/DataDog/dd-agent/issues/919
[#921]: https://github.com/DataDog/dd-agent/issues/921
[#922]: https://github.com/DataDog/dd-agent/issues/922
[#927]: https://github.com/DataDog/dd-agent/issues/927
[#928]: https://github.com/DataDog/dd-agent/issues/928
[#930]: https://github.com/DataDog/dd-agent/issues/930
[#933]: https://github.com/DataDog/dd-agent/issues/933
[#935]: https://github.com/DataDog/dd-agent/issues/935
[#940]: https://github.com/DataDog/dd-agent/issues/940
[#947]: https://github.com/DataDog/dd-agent/issues/947
[#949]: https://github.com/DataDog/dd-agent/issues/949
[#951]: https://github.com/DataDog/dd-agent/issues/951
[#958]: https://github.com/DataDog/dd-agent/issues/958
[#960]: https://github.com/DataDog/dd-agent/issues/960
[#962]: https://github.com/DataDog/dd-agent/issues/962
[#963]: https://github.com/DataDog/dd-agent/issues/963
[#964]: https://github.com/DataDog/dd-agent/issues/964
[#971]: https://github.com/DataDog/dd-agent/issues/971
[#972]: https://github.com/DataDog/dd-agent/issues/972
[#975]: https://github.com/DataDog/dd-agent/issues/975
[#977]: https://github.com/DataDog/dd-agent/issues/977
[#980]: https://github.com/DataDog/dd-agent/issues/980
[#981]: https://github.com/DataDog/dd-agent/issues/981
[#982]: https://github.com/DataDog/dd-agent/issues/982
[#984]: https://github.com/DataDog/dd-agent/issues/984
[#996]: https://github.com/DataDog/dd-agent/issues/996
[#1001]: https://github.com/DataDog/dd-agent/issues/1001
[#1002]: https://github.com/DataDog/dd-agent/issues/1002
[#1008]: https://github.com/DataDog/dd-agent/issues/1008
[#1013]: https://github.com/DataDog/dd-agent/issues/1013
[#1014]: https://github.com/DataDog/dd-agent/issues/1014
[#1015]: https://github.com/DataDog/dd-agent/issues/1015
[#1016]: https://github.com/DataDog/dd-agent/issues/1016
[#1017]: https://github.com/DataDog/dd-agent/issues/1017
[#1018]: https://github.com/DataDog/dd-agent/issues/1018
[#1019]: https://github.com/DataDog/dd-agent/issues/1019
[#1023]: https://github.com/DataDog/dd-agent/issues/1023
[#1024]: https://github.com/DataDog/dd-agent/issues/1024
[#1027]: https://github.com/DataDog/dd-agent/issues/1027
[#1028]: https://github.com/DataDog/dd-agent/issues/1028
[#1029]: https://github.com/DataDog/dd-agent/issues/1029
[#1031]: https://github.com/DataDog/dd-agent/issues/1031
[#1035]: https://github.com/DataDog/dd-agent/issues/1035
[#1036]: https://github.com/DataDog/dd-agent/issues/1036
[#1041]: https://github.com/DataDog/dd-agent/issues/1041
[#1060]: https://github.com/DataDog/dd-agent/issues/1060
[#1065]: https://github.com/DataDog/dd-agent/issues/1065
[#1068]: https://github.com/DataDog/dd-agent/issues/1068
[#1069]: https://github.com/DataDog/dd-agent/issues/1069
[#1073]: https://github.com/DataDog/dd-agent/issues/1073
[#1080]: https://github.com/DataDog/dd-agent/issues/1080
[#1101]: https://github.com/DataDog/dd-agent/issues/1101
[#1105]: https://github.com/DataDog/dd-agent/issues/1105
[#1115]: https://github.com/DataDog/dd-agent/issues/1115
[#1116]: https://github.com/DataDog/dd-agent/issues/1116
[#1117]: https://github.com/DataDog/dd-agent/issues/1117
[#1123]: https://github.com/DataDog/dd-agent/issues/1123
[#1124]: https://github.com/DataDog/dd-agent/issues/1124
[#1141]: https://github.com/DataDog/dd-agent/issues/1141
[#1152]: https://github.com/DataDog/dd-agent/issues/1152
[#1153]: https://github.com/DataDog/dd-agent/issues/1153
[#1155]: https://github.com/DataDog/dd-agent/issues/1155
[#1162]: https://github.com/DataDog/dd-agent/issues/1162
[#1163]: https://github.com/DataDog/dd-agent/issues/1163
[#1164]: https://github.com/DataDog/dd-agent/issues/1164
[#1165]: https://github.com/DataDog/dd-agent/issues/1165
[#1171]: https://github.com/DataDog/dd-agent/issues/1171
[#1173]: https://github.com/DataDog/dd-agent/issues/1173
[#1175]: https://github.com/DataDog/dd-agent/issues/1175
[#1181]: https://github.com/DataDog/dd-agent/issues/1181
[#1187]: https://github.com/DataDog/dd-agent/issues/1187
[#1188]: https://github.com/DataDog/dd-agent/issues/1188
[#1192]: https://github.com/DataDog/dd-agent/issues/1192
[#1200]: https://github.com/DataDog/dd-agent/issues/1200
[#1201]: https://github.com/DataDog/dd-agent/issues/1201
[#1202]: https://github.com/DataDog/dd-agent/issues/1202
[#1203]: https://github.com/DataDog/dd-agent/issues/1203
[#1205]: https://github.com/DataDog/dd-agent/issues/1205
[#1207]: https://github.com/DataDog/dd-agent/issues/1207
[#1208]: https://github.com/DataDog/dd-agent/issues/1208
[#1210]: https://github.com/DataDog/dd-agent/issues/1210
[#1211]: https://github.com/DataDog/dd-agent/issues/1211
[#1213]: https://github.com/DataDog/dd-agent/issues/1213
[#1214]: https://github.com/DataDog/dd-agent/issues/1214
[#1218]: https://github.com/DataDog/dd-agent/issues/1218
[#1219]: https://github.com/DataDog/dd-agent/issues/1219
[#1221]: https://github.com/DataDog/dd-agent/issues/1221
[#1222]: https://github.com/DataDog/dd-agent/issues/1222
[#1225]: https://github.com/DataDog/dd-agent/issues/1225
[#1226]: https://github.com/DataDog/dd-agent/issues/1226
[#1227]: https://github.com/DataDog/dd-agent/issues/1227
[#1235]: https://github.com/DataDog/dd-agent/issues/1235
[#1236]: https://github.com/DataDog/dd-agent/issues/1236
[#1238]: https://github.com/DataDog/dd-agent/issues/1238
[#1240]: https://github.com/DataDog/dd-agent/issues/1240
[#1255]: https://github.com/DataDog/dd-agent/issues/1255
[#1260]: https://github.com/DataDog/dd-agent/issues/1260
[#1267]: https://github.com/DataDog/dd-agent/issues/1267
[#1269]: https://github.com/DataDog/dd-agent/issues/1269
[#1272]: https://github.com/DataDog/dd-agent/issues/1272
[#1273]: https://github.com/DataDog/dd-agent/issues/1273
[#1274]: https://github.com/DataDog/dd-agent/issues/1274
[#1275]: https://github.com/DataDog/dd-agent/issues/1275
[#1278]: https://github.com/DataDog/dd-agent/issues/1278
[#1279]: https://github.com/DataDog/dd-agent/issues/1279
[#1281]: https://github.com/DataDog/dd-agent/issues/1281
[#1282]: https://github.com/DataDog/dd-agent/issues/1282
[#1284]: https://github.com/DataDog/dd-agent/issues/1284
[#1285]: https://github.com/DataDog/dd-agent/issues/1285
[#1297]: https://github.com/DataDog/dd-agent/issues/1297
[#1310]: https://github.com/DataDog/dd-agent/issues/1310
[#1318]: https://github.com/DataDog/dd-agent/issues/1318
[#1326]: https://github.com/DataDog/dd-agent/issues/1326
[#1332]: https://github.com/DataDog/dd-agent/issues/1332
[#1343]: https://github.com/DataDog/dd-agent/issues/1343
[#1345]: https://github.com/DataDog/dd-agent/issues/1345
[#1350]: https://github.com/DataDog/dd-agent/issues/1350
[#1370]: https://github.com/DataDog/dd-agent/issues/1370
[#1377]: https://github.com/DataDog/dd-agent/issues/1377
[#1379]: https://github.com/DataDog/dd-agent/issues/1379
[#1380]: https://github.com/DataDog/dd-agent/issues/1380
[#1383]: https://github.com/DataDog/dd-agent/issues/1383
[#1388]: https://github.com/DataDog/dd-agent/issues/1388
[#1389]: https://github.com/DataDog/dd-agent/issues/1389
[#1390]: https://github.com/DataDog/dd-agent/issues/1390
[#1391]: https://github.com/DataDog/dd-agent/issues/1391
[#1393]: https://github.com/DataDog/dd-agent/issues/1393
[#1395]: https://github.com/DataDog/dd-agent/issues/1395
[#1396]: https://github.com/DataDog/dd-agent/issues/1396
[#1399]: https://github.com/DataDog/dd-agent/issues/1399
[#1400]: https://github.com/DataDog/dd-agent/issues/1400
[#1401]: https://github.com/DataDog/dd-agent/issues/1401
[#1408]: https://github.com/DataDog/dd-agent/issues/1408
[#1414]: https://github.com/DataDog/dd-agent/issues/1414
[#1415]: https://github.com/DataDog/dd-agent/issues/1415
[#1416]: https://github.com/DataDog/dd-agent/issues/1416
[#1422]: https://github.com/DataDog/dd-agent/issues/1422
[#1429]: https://github.com/DataDog/dd-agent/issues/1429
[#1435]: https://github.com/DataDog/dd-agent/issues/1435
[#1436]: https://github.com/DataDog/dd-agent/issues/1436
[#1438]: https://github.com/DataDog/dd-agent/issues/1438
[#1441]: https://github.com/DataDog/dd-agent/issues/1441
[#1442]: https://github.com/DataDog/dd-agent/issues/1442
[#1443]: https://github.com/DataDog/dd-agent/issues/1443
[#1444]: https://github.com/DataDog/dd-agent/issues/1444
[#1446]: https://github.com/DataDog/dd-agent/issues/1446
[#1447]: https://github.com/DataDog/dd-agent/issues/1447
[#1454]: https://github.com/DataDog/dd-agent/issues/1454
[#1457]: https://github.com/DataDog/dd-agent/issues/1457
[#1459]: https://github.com/DataDog/dd-agent/issues/1459
[#1461]: https://github.com/DataDog/dd-agent/issues/1461
[#1476]: https://github.com/DataDog/dd-agent/issues/1476
[#1487]: https://github.com/DataDog/dd-agent/issues/1487
[#1490]: https://github.com/DataDog/dd-agent/issues/1490
[#1503]: https://github.com/DataDog/dd-agent/issues/1503
[#1507]: https://github.com/DataDog/dd-agent/issues/1507
[#1509]: https://github.com/DataDog/dd-agent/issues/1509
[#1511]: https://github.com/DataDog/dd-agent/issues/1511
[#1512]: https://github.com/DataDog/dd-agent/issues/1512
[#1518]: https://github.com/DataDog/dd-agent/issues/1518
[#1535]: https://github.com/DataDog/dd-agent/issues/1535
[#1549]: https://github.com/DataDog/dd-agent/issues/1549
[#1550]: https://github.com/DataDog/dd-agent/issues/1550
[#1558]: https://github.com/DataDog/dd-agent/issues/1558
[#1559]: https://github.com/DataDog/dd-agent/issues/1559
[#1561]: https://github.com/DataDog/dd-agent/issues/1561
[#1565]: https://github.com/DataDog/dd-agent/issues/1565
[#1569]: https://github.com/DataDog/dd-agent/issues/1569
[#1570]: https://github.com/DataDog/dd-agent/issues/1570
[#1577]: https://github.com/DataDog/dd-agent/issues/1577
[#1579]: https://github.com/DataDog/dd-agent/issues/1579
[#1582]: https://github.com/DataDog/dd-agent/issues/1582
[#1586]: https://github.com/DataDog/dd-agent/issues/1586
[#1589]: https://github.com/DataDog/dd-agent/issues/1589
[#1590]: https://github.com/DataDog/dd-agent/issues/1590
[#1592]: https://github.com/DataDog/dd-agent/issues/1592
[#1594]: https://github.com/DataDog/dd-agent/issues/1594
[#1595]: https://github.com/DataDog/dd-agent/issues/1595
[#1596]: https://github.com/DataDog/dd-agent/issues/1596
[#1611]: https://github.com/DataDog/dd-agent/issues/1611
[#1612]: https://github.com/DataDog/dd-agent/issues/1612
[#1613]: https://github.com/DataDog/dd-agent/issues/1613
[#1614]: https://github.com/DataDog/dd-agent/issues/1614
[#1616]: https://github.com/DataDog/dd-agent/issues/1616
[#1617]: https://github.com/DataDog/dd-agent/issues/1617
[#1618]: https://github.com/DataDog/dd-agent/issues/1618
[#1619]: https://github.com/DataDog/dd-agent/issues/1619
[#1621]: https://github.com/DataDog/dd-agent/issues/1621
[#1623]: https://github.com/DataDog/dd-agent/issues/1623
[#1630]: https://github.com/DataDog/dd-agent/issues/1630
[#1631]: https://github.com/DataDog/dd-agent/issues/1631
[#1633]: https://github.com/DataDog/dd-agent/issues/1633
[#1640]: https://github.com/DataDog/dd-agent/issues/1640
[#1642]: https://github.com/DataDog/dd-agent/issues/1642
[#1643]: https://github.com/DataDog/dd-agent/issues/1643
[#1644]: https://github.com/DataDog/dd-agent/issues/1644
[#1645]: https://github.com/DataDog/dd-agent/issues/1645
[#1650]: https://github.com/DataDog/dd-agent/issues/1650
[#1651]: https://github.com/DataDog/dd-agent/issues/1651
[#1655]: https://github.com/DataDog/dd-agent/issues/1655
[#1657]: https://github.com/DataDog/dd-agent/issues/1657
[#1664]: https://github.com/DataDog/dd-agent/issues/1664
[#1666]: https://github.com/DataDog/dd-agent/issues/1666
[#1679]: https://github.com/DataDog/dd-agent/issues/1679
[#1700]: https://github.com/DataDog/dd-agent/issues/1700
[#1701]: https://github.com/DataDog/dd-agent/issues/1701
[#1709]: https://github.com/DataDog/dd-agent/issues/1709
[#1710]: https://github.com/DataDog/dd-agent/issues/1710
[#1757]: https://github.com/DataDog/dd-agent/issues/1757
[#1792]: https://github.com/DataDog/dd-agent/issues/1792
[@AirbornePorcine]: https://github.com/AirbornePorcine
[@CaptTofu]: https://github.com/CaptTofu
[@Osterjour]: https://github.com/Osterjour
[@PedroMiguelFigueiredo]: https://github.com/PedroMiguelFigueiredo
[@adriandoolittle]: https://github.com/adriandoolittle
[@arosenhagen]: https://github.com/arosenhagen
[@arthurnn]: https://github.com/arthurnn
[@bpuzon]: https://github.com/bpuzon
[@brettlangdon]: https://github.com/brettlangdon
[@charles-dyfis-net]: https://github.com/charles-dyfis-net
[@chrissnel]: https://github.com/chrissnel
[@ckrough]: https://github.com/ckrough
[@clly]: https://github.com/clly
[@dcrosta]: https://github.com/dcrosta
[@djensen47]: https://github.com/djensen47
[@donalguy]: https://github.com/donalguy
[@echohead]: https://github.com/echohead
[@etrepum]: https://github.com/etrepum
[@glickbot]: https://github.com/glickbot
[@gphat]: https://github.com/gphat
[@graemej]: https://github.com/graemej
[@gtaylor]: https://github.com/gtaylor
[@handigarde]: https://github.com/handigarde
[@host]: https://github.com/host
[@igor47]: https://github.com/igor47
[@igroenewold]: https://github.com/igroenewold
[@imlucas]: https://github.com/imlucas
[@ipolishchuk]: https://github.com/ipolishchuk
[@ive]: https://github.com/ive
[@jamescrowley]: https://github.com/jamescrowley
[@jkoppe]: https://github.com/jkoppe
[@jonaf]: https://github.com/jonaf
[@joningle]: https://github.com/joningle
[@jzoldak]: https://github.com/jzoldak
[@leifwalsh]: https://github.com/leifwalsh
[@loris]: https://github.com/loris
[@mastrolinux]: https://github.com/mastrolinux
[@micktwomey]: https://github.com/micktwomey
[@mike-lerch]: https://github.com/mike-lerch
[@mms-gianni]: https://github.com/mms-gianni
[@morskoyzmey]: https://github.com/morskoyzmey
[@mutemule]: https://github.com/mutemule
[@nambrosch]: https://github.com/nambrosch
[@ordenull]: https://github.com/ordenull
[@oremj]: https://github.com/oremj
[@orenmazor]: https://github.com/orenmazor
[@patrickbcullen]: https://github.com/patrickbcullen
[@pbitty]: https://github.com/pbitty
[@polynomial]: https://github.com/polynomial
[@rl-0x0]: https://github.com/rl-0x0
[@ronaldbradford]: https://github.com/ronaldbradford
[@shamada-kuuluu]: https://github.com/shamada-kuuluu
[@sirlantis]: https://github.com/sirlantis
[@skingry]: https://github.com/skingry
[@slushpupie]: https://github.com/slushpupie
[@squaresurf]: https://github.com/squaresurf
[@steeve]: https://github.com/steeve
[@stefan-mees]: https://github.com/stefan-mees
[@takus]: https://github.com/takus
[@tomduckering]: https://github.com/tomduckering
[@walkeran]: https://github.com/walkeran
[@warnerpr-cyan]: https://github.com/warnerpr-cyan
[@yyamano]: https://github.com/yyamano
