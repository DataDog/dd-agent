Datadog Agent 6 has been officially released and the release notes can be found [here](https://github.com/DataDog/datadog-agent/releases). Agent 5 will continue to see releases.

Changes
=======

# 5.24.0 / 05-11-2018

**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.23.0...5.24.0

### Changes
Please refer to the [Integrations Core Checks 6.2.0 tag](https://github.com/DataDog/integrations-core/releases/tag/6.2.0) for the list of changes on the core checks.

Please refer to the [Trace Agent 6.2.0 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/6.2.0) for more information on the Trace Agent.

Please refer to the [Process Agent 6.2.0 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/6.2.0) for more information on the Process Agent.

* [IMPROVEMENT] Windows: Add pdh data to flare. See [#3719][]
* [IMPROVEMENT] JMXFetch: Bump to `0.20.0`. See [#3726][] and [jmxfetch 0.20.0 tag](https://github.com/DataDog/jmxfetch/releases/tag/0.20.0)
* [OTHER] subprocess_output: Add compatibility layer with `datadog_checks_base`. See [#3723][]
* [OTHER] Windows: Use PDH libs provided in `datadog_checks_base`. See [#3691][]

# 5.23.0 / 03-21-2018

**Linux, Windows, Docker**

### Details
https://github.com/DataDog/dd-agent/compare/5.22.3...5.23.0

### Changes
Please refer to the [Integrations Core Checks 5.23.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.23.0) for the list of changes on the core checks.

Please refer to the [Process Agent 5.23.0 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.23.0) for more information on the Process Agent.

* [BUGFIX] Windows: Fix pdh counters on localized versions of windows. See [#3713][]
* [BUGFIX] Remove API key if included in processes metadata payload. See [#3712][]
* [BUGFIX] Avoid failing the configcheck command if the instances is empty. See [#3704][]
* [BUGFIX] Kuernetes: fix logic to collect ownerreference for k8 1.9. See [#3667][]
* [BUGFIX] Fix an error when the agent failed to find the name of a docker image. See [#3669][]
* [BUGFIX] pause-container: update the list of the pause containers. See [#3670][]
* [IMPROVEMENT] jmxfetch: include version 0.19.0. See [#3711][]
* [IMPROVEMENT] Logs an INFO message instead of an ERROR when the host is deemed as Dockerless. See [#3657][]
* [IMPROVEMENT]  Windows: change default datatype for pdh queries to double. See [#3703][]
* [OTHER] Remove the deprecated option `skip_event` in network checks. See [#3643][]


# 5.22.3 / 03-08-2018

**Linux, Windows, Docker**

### Details
This release only ships changes to the process-agent.
https://github.com/DataDog/dd-agent/compare/5.22.1...5.22.3

### Changes
Please refer to the [Process Agent 5.22.3 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.22.3) for more information on the Process Agent.

# 5.22.1 / 02-26-2018

**Linux, Windows, Docker**

### Details
This release only ships changes to the process-agent.
https://github.com/DataDog/dd-agent/compare/5.22.0...5.22.1

### Changes
Please refer to the [Process Agent 5.22.1 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.22.1) for more information on the Process Agent.

# 5.22.0 / 02-13-2018

**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.21.2...5.22.0

### Changes
Please refer to the [Integrations Core Checks 5.22.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.22.0) for the list of changes on the core checks.

Please refer to the [Process Agent 5.22.0 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.22.0) for more information on the Process Agent.

Datadog will be rotating the GPG key used to sign our APT repositories on Feb 28 2018. More details and the new key can be found in our [knowledge base](https://help.datadoghq.com/hc/en-us/articles/360000886852).

* [IMPROVEMENT] Collect total system memory for Mac OS X. See [#3169][]
* [IMPROVEMENT] JMXFETCH: include version 0.18.1. See [#3543][]
* [BUGFIX] Fix prometheus check summary and histogram. See [#3617][]
* [IMPROVEMENT] Prometheus Check: add generic label joins and node to hostname. See [#3623][]
* [BUGFIX] Fixes issue with auto-discovery and wheels. See [#3629][]
* [IMPROVEMENT] Add "process_agent_enabled" to example datadog.conf. See [#3630][]
* [BUGFIX] Fix issue with creating tags from conf in IIS. See [#3635][]
* [IMPROVEMENT] Prometheus Check: add SSL support. See [#3640][]
* [IMPROVEMENT] Deduplicate tags on metrics, events and service_checks. See [#3641][]
* [BUGFIX] Fix "no_proxy" option when using requests. See [#3644][] and [#3645][]
* [IMPROVEMENT] Adding "jmx_custom_jars" option to datadog.yaml. See [#3648][]
* [IMPROVEMENT] Windows: the agent service is no longer responsible for starting the APM service. See [#3655][]
* [DEPRECATE] Bundled "checks.d" is now a deprecated location as checks are shipped as wheels. See [#3661][]
* [IMPROVEMENT] Windows: Start subservices (trace/process) if they're configured on service start. See [#3663][]
* [IMPROVEMENT] Extend pause-container list. See [#3674][]

# 5.21.2 / 01-31-2018

**Linux, Windows, Docker**

### Details
This release only ships changes to the process-agent.
https://github.com/DataDog/dd-agent/compare/5.21.0...5.21.2

### Changes
Please refer to the [Process Agent 5.21.2 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.21.2) for more information on the Process Agent.

# 5.21.1 / 01-31-2018

**Linux, Windows, Docker**

### Details
This release only ships changes to the trace-agent.
https://github.com/DataDog/dd-agent/compare/5.21.0...5.21.1

### Changes
Please refer to the [Trace Agent 5.21.1 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.21.1) for the list of changes on the Trace Agent.

# 5.21.0 / 01-10-2018

**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.20.2...5.21.0

### Changes
Please refer to the [Integrations Core Checks 5.21.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.21.0) for the list of changes on the core checks.

Please refer to the [Process Agent 5.21.0 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.21.0) for more information on the Process Agent.

* [BUGFIX] Configuration: Use : instead of = in APM config. See [#3599][] (Thanks [@brianwolfe][])
* [BUGFIX] PDH: Return with metric list empty if can't connect to host. See [#3612][]
* [IMPROVEMENT] Source install: Add host tagging to install_agent.sh. See [#3551][] (Thanks [@iancward][])
* [IMPROVEMENT] Kubernetes: get nodeName and nodeIP even if the agent isn't inside a Pod. See [#3614][]
* [IMPROVEMENT] Docker: add flag to image_name_extractor to return short image name. See [#3622][]
* [IMPROVEMENT] WMI: Skip properties in WMI query results if not in arguments. See [#3618][]
* [IMPROVEMENT] Log metadata payload as debug to be added to flares. See [#3625][]
* [IMPROVEMENT] Don't spam logs with exceptions when checks aren't wheels. See [#3620][]
* [IMPROVEMENT] bump protobuf to 3.5.1. See [#3619][]
* [IMPROVEMENT] Aggregator: ignore all dist metrics (metric type starting with 'd'). See [#3611][]
* [IMPROVEMENT] Auto-Discovery: add kube container name in service discovery containers. See [#3609][]
* [IMPROVEMENT] Windows: change restart to stop/start with deps. See [#3565][]
* [FEATURE] Allow running checks packaged as wheels. See [#3555][]
* [FEATURE] Filehandles: include allocated, allocated but unused, used, and max filehandler metrics. See [#3608][] (Thanks [@kennydo][])
* [FEATURE] Adds an option to disable IPv6. See [#3603][]
* [FEATURE] Windows: update pdh library to support generic pdh based checks. See [#3581][]
* [FEATURE] Windows: update base libraries for PDH based checks. See [#3607][]
* [FEATURE] Collect OpenStack metadata and tags community. See [#3411][] (Thanks [@mtougeron][])

# 5.20.2 / 12-06-2017

**Linux, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.20.1...5.20.2

### Changes
Please refer to the [Integrations Core Checks 5.20.2 tag](https://github.com/DataDog/integrations-core/releases/tag/5.20.2) for the list of changes on the core checks.

Please refer to the [Process Agent 5.20.2 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.20.2) for more information on the Process Agent.

# 5.20.1 / 11-29-2017

**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.20.0...5.20.1

### Changes
Please refer to the [Integrations Core Checks 5.20.1 tag](https://github.com/DataDog/integrations-core/releases/tag/5.20.1) for the list of changes on the core checks.

Please refer to the [Trace Agent 5.20.0 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.20.0) for the list of changes on the Trace Agent.

Please refer to the [Process Agent 5.20.1 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.20.1) for more information on the Process Agent.


* [BUGFIX] Windows: fixing flakes, stubbing WinPDHCounter [#3596][]

# 5.20.0 / 11-21-2017

**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.19.0...5.20.0

### Changes
Please refer to the [Integrations Core Checks 5.20.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.20.0) for the list of changes on the core checks.

Please refer to the [Trace Agent 5.20.0 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.20.0) for the list of changes on the Trace Agent.

Please refer to the [Process Agent 5.20.0 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.20.0) for more information on the Process Agent.

* [BUGFIX] Audo Configuration: Fix AD port parsing. See [#3553][]
* [BUGFIX] Core: Fixes normalization of metric names, removing `@`. See [#3529][]
* [BUGFIX] Core: Only start trace agent on windows if its enabld. See [#3554][]
* [BUGFIX] Kubernetes: fix tagging on k8s 1.8+ clusters. See [#3563][], [#3586][]
* [BUGFIX] System Checks: Fixes grabbing of file handles. See [#3539][] (Thanks [@matlockx][])
* [BUGFIX] Audo Configuration: Fix enabling condition. See [#3589][]
* [IMPROVEMENT] Core: Won't start if API Key is too short. See [#3546][]
* [IMPROVEMENT] Core: Won't start agent on windows if API Key invalid. See [#3547][]
* [IMPROVEMENT] Kubernetes: Adds more tags to events. See [#3548][]
* [IMPROVEMENT] Core: Decrease log noise at startup. See [#3547][]
* [IMPROVEMENT] Kubernetes: Filter kubernetes events based on timestamp. See [#3549][]
* [IMPROVEMENT] Audo Configuration: Adds docker labels as tags. See [#3564][]
* [IMPROVEMENT] Containers: Move most container tags to metadata. See [#3557][]
* [IMPROVEMENT] Kubernetes: Allow overriding the pod name. See [#3571][] (Thanks [@darnaut][])
* [IMPROVEMENT] Windows: Remove check for pidfile. See [#3574][]
* [IMPROVEMENT] Windows: Change restart to start/stop with deps. See [#3565][]
* [FEATURE] Windows: Add a PDH base check. See [#3581][]


# 5.19.0 / 11-03-2017
**Linux, Windows, Docker and Source Install**

_Windows released on 11-03-2017_

_Linux, Docker and Source Install released on 11-08-2017_

### Details

This release includes:

* the `trace-agent` on Windows, as a Beta feature, and related changes on the Windows service management
* features and bugfixes for the `trace-agent` and `process-agent` on Linux, Docker and Source Install - please check
their respective changelogs for more details
* changes on Autodiscovery & container support
* bugfixes on some core checks

https://github.com/DataDog/dd-agent/compare/5.18.1...5.19.0

### Changes
Please refer to the [Integrations Core Checks 5.19.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.19.0) for the list of changes on the core checks.

Please refer to the [Trace Agent 5.19.0 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.19.0) for the list of changes on the Trace Agent.

Please refer to the [Process Agent 5.19.0 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.19.0) for more information on the Process Agent.

* [FEATURE] Autodiscovery: Add docker labels as tags in autodiscovery. See [#3564][]
* [FEATURE] Windows: Enable the apm service based on the configuration file. See [#3554][]
* [FEATURE] Windows: Include the trace agent as part of the Datadog Agent. See [dd-agent-omnibus-203](https://github.com/DataDog/dd-agent-omnibus/pull/203) & [dd-agent-omnibus-204](https://github.com/DataDog/dd-agent-omnibus/pull/204)
* [IMPROVEMENT] Switch most of container host tags to host metadata. See [#3557][]
* [IMPROVEMENT] Windows: Tighten permissions on `datadog.conf` to only be readable by admins and local system. See [dd-agent-omnibus-202](https://github.com/DataDog/dd-agent-omnibus/pull/202)

# 5.18.1 / 10-13-2017
**Linux, Docker and Source Install**

### Details
This release includes bugfixes for the `trace-agent` and `process-agent` only - please check
their respective changelogs for more details.
https://github.com/DataDog/dd-agent/compare/5.18.0...5.18.1

### Changes
Please refer to the [Trace Agent 5.18.1 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.18.1) for the list of changes on the Trace Agent.
Please refer to the [Process Agent 5.18.1 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.18.1) for more information on the Process Agent.

# 5.18.0 / 10-10-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.17.0...5.18.0

### Dependency Changes

* Python (Linux only) `2.7.14` (previously `2.7.13`). See [omnibus-software-169](https://github.com/DataDog/omnibus-software/pull/169)
* CAcerts updated to latest certificate bundle. See [omnibus-software-167](https://github.com/DataDog/omnibus-software/pull/167)
* JMXFetch updated to `0.17.0` (previously `0.16.0`). See [omnibus-software-166](https://github.com/DataDog/omnibus-software/pull/166), [#3527][]
* Nfsiostat added `2.1.1`. See [omnibus-software-162](https://github.com/DataDog/omnibus-software/pull/162), [dd-agent-omnibus-196](https://github.com/DataDog/dd-agent-omnibus/pull/196)

### Changes
Please refer to the [Integrations Core Checks 5.18.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.18.0) for the list of changes on the core checks.
Please refer to the [Trace Agent 5.18.0 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.18.0) for the list of changes on the Trace Agent.
Please refer to the [Process Agent 5.18.0 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.18.0) for more information on the Process Agent.

* [FEATURE] JMXFetch: add canonical rate. See [#3494][], [jmxfetch-156](https://github.com/DataDog/jmxfetch/pull/154) (Thanks [@arrawatia][])
* [IMPROVEMENT] Core: adding docker inspect to flare. See [#3536][]
* [IMPROVEMENT] Windows: enhanced PDH counter support. See [#3536][]
* [BUGFIX] RHEL/CentOS7[systemd]: enable datadog-agent service on post-install. See [dd-agent-omnibus-201](https://github.com/DataDog/omnibus-software/pull/201)
* [BUGFIX] Windows: fix PDH counter i18n issues. See [#3536][]
* [BUGFIX] Kubernetes: fix image lookup. See [#3532][]
* [BUGFIX] Mesos: do not crash if `ENV` in `CONF` is none. See [#3528][]
* [SANITY] WMI: renamed library from wmi_check to winwmi_check. See [#3521][]
* [SECURITY] Core: Redact sensistive information in config dumps. See [#3534][]
* [SECURITY] Core: fix potential leak of API key into collector/dogstatsd logs. See [#3537][]
* [DEPRECATE] deprecate `read_config`. See [#3508][]
* [DEPRECATE] Docker: remove access to deprecated top-level `NetworkSettings`. See [#3538][]

# 5.17.2 / 09-18-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.17.1...5.17.2

### Changes
Please refer to the [Integrations Core Checks 5.17.2 tag](https://github.com/DataDog/integrations-core/releases/tag/5.17.2) for the list of changes on the core checks.
Please refer to the [Process Agent 5.17.2 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.17.2) for more information on the Process Agent.

### Dependency changes
* `supervisor` `3.3.3` (previously `3.3.0`), see [omnibus-software-165](https://github.com/DataDog/omnibus-software/pull/165)

### Changes

* [REGRESSION] Kubernetes: partially revert `_locate_kubelet` from [#3497][]. See [#3523][]

# 5.17.1 / 09-12-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.17.0...5.17.1

### Changes
Please refer to the [Integrations Core Checks 5.17.1 tag](https://github.com/DataDog/integrations-core/releases/tag/5.17.1) for the list of changes on the core checks.
Please refer to the [Trace Agent 5.17.1 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.17.1) for the list of changes on the Trace Agent.
Please refer to the [Process Agent 5.17.1 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.17.1) for more information on the Process Agent.

* [IMPROVEMENT] Autodiscovery: Make Autodiscovery wait on docker/kubelet. See [#3497][]
* [IMPROVEMENT] Docker: catch `docker.errors.NotFound` for nonexisting images. See [#3507][]
* [BUGFIX] Autodiscovery: Rework Autodiscovery image name extractor to support new swarm format. See [#3511][]
* [BUGFIX] Dogstreams: Retry reading files that could't be read on agent startup. See [#2815][], thanks [@jalaziz][]
* [BUGFIX] Flare: Update api key regex to support more formats. See [#3509][]
* [BUGFIX] Kubernetes: Add image_name_resolver to kubeutil wrapping dockerutil. See [#3505][]
* [BUGFIX] Kubernetes: Fix leader election's lease parameter and node name. See [#3506][]

# 5.17.0 / 08-28-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.16.0...5.17.0

### Dependency changes
* `kafka-python` `1.3.4` (previously `1.3.3`), see [omnibus-software-155](https://github.com/DataDog/omnibus-software/pull/155)
* `kazoo` `2.4.0` (previously `2.2.1`), see [omnibus-software-154](https://github.com/DataDog/omnibus-software/pull/154)

### Changes
Please refer to the [Integrations Core Checks 5.17.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.17.0) for the list of changes on the core checks.
Please refer to the [Trace Agent 5.17.0 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.17.0) for the list of changes on the Trace Agent.
Please refer to the [Process Agent 5.17.0 tag](https://github.com/DataDog/datadog-process-agent/releases/tag/5.17.0) for more information on the Process Agent.

* [FEATURE] Autodiscovery: Allow autoconf templates in docker labels. See [#3451][]
* [FEATURE] JMXFetch: Add `list_jvms` command on `dd-agent`. See [#2962][]
* [IMPROVEMENT] Azure: Use VM ID as a host alias. See [#3402][]
* [IMPROVEMENT] Collector: Split check runs from main agent payload. See [#3446][]
* [IMPROVEMENT] Collector: Split metric payloads larger than 2MB into smaller payloads. See [#3454][]
* [IMPROVEMENT] Collector: On info page, display `unknown` version if module load fail, `custom` if custom check. See [#3488][]
* [IMPROVEMENT] Debian packaging: Add `gnupg` as dependency, and suggest `dirmngr`. See [#3492][] and [dd-agent-omnibus-191](https://github.com/DataDog/dd-agent-omnibus/issues/191)
* [IMPROVEMENT] Docker: Add openshift/origin-pod to default docker ignore list. See [#3460][]
* [IMPROVEMENT] Dogstatsd: Add support for `SO_RCVBUF` socket option. See [#3429][], thanks [@jnewland][]
* [IMPROVEMENT] JMXFetch: Touch JMXFetch launch file on boot-up. See [jmxfetch-143](https://github.com/DataDog/jmxfetch/issues/143)
* [IMPROVEMENT] Kubernetes: Add option to import node labels as host tags. See [#3445][]
* [IMPROVEMENT] Kubernetes: Automatically collect events from one agent only, with leader election among agents. See [#3476][]
* [IMPROVEMENT] Kubernetes: Tag pods with `kube_stateful_set` tag. See [#3443][], thanks [@erkolson][]
* [IMPROVEMENT] Packaging: Allow disabling datadog-agent service via sysconfig/default file. See [#3301][], [#3483][] and [#3489][], thanks [@generica][]
* [IMPROVEMENT] Packaging: On CentOS, add systemd service definition and add LSB dependency in sysvinit script. See [#3477][]
* [IMPROVEMENT] Prometheus: Allow metric type overrides in `PrometheusCheck` class. See [#3463][]
* [IMPROVEMENT] Windows packaging: Allow configuration of proxy on the installer CLI. See [#3470][] and [dd-agent-omnibus-192](https://github.com/DataDog/dd-agent-omnibus/issues/192)
* [IMPROVEMENT] Windows system checks: Use `win32pdh` instead of WMI. See [#3294][]
* [BUGFIX] Autodiscovery: Fix instance-level tags when multi instances are configured. See [#3478][]
* [BUGFIX] Autodiscovery: Re-pipe configurations after JMXFetch restart. See [#3415][]
* [BUGFIX] Collector: Only add service check fields if non-null. See [#3487][]
* [BUGFIX] Core: Make `configcheck` command exit with meaningful exit code. See [#3481][]
* [BUGFIX] Core: Make test on stored PID more accurate on Windows. See [#3468][]
* [BUGFIX] Core: Remove occurences where the full api key could be logged. See [#3466][]
* [BUGFIX] Forwarder: Make payload rejection log entry more explicit. See [#3486][]
* [BUGFIX] JMXFetch: Increase maximum length of instance configs pulled from Auto-Discovery pipe. See [jmxfetch-147](https://github.com/DataDog/jmxfetch/issues/147)
* [BUGFIX] JMXFetch: Fix Agent crash when JMXFetch pipe is broken. See [#3461][]
* [BUGFIX] Packaging: On CentOS, fix duplicate and unwanted service restarts at the end of installs. See [dd-agent-omnibus-194](https://github.com/DataDog/dd-agent-omnibus/issues/194)
* [BUGFIX] WMI: Convert UINT32 WMI type to positive integer instead of negative integer. See [#3467][]
* [SANITY] Autodiscovery: Avoid calling kubeutil if it's not initialized. See [#3479][]
* [SANITY] Collector: Downgrade docker warning message to debug on dockerless hosts. See [#3485][]
* [SANITY] Collector: Remove deprecated `run_check` method on Windows. See [#3448][]
* [SANITY] Dogstatsd: Parse distribution metrics and ignore them. See [#3458][]
* [SANITY] Gohai: Swallow python error for python version. See [gohai-51](https://github.com/DataDog/gohai/pull/51)
* [SANITY] Packaging: Remove unneded chown on `/usr/bin/dd-agent`. See [dd-agent-omnibus-193](https://github.com/DataDog/dd-agent-omnibus/issues/193)

# 5.16.0 / 07-26-2017
**Linux, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.15.0...5.16.0

### Changes
Please refer to the [Integrations Core Checks 5.16.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.16.0) for the list of changes on the core checks.
Please refer to the [Process Agent](https://github.com/DataDog/datadog-process-agent/) for more information on this new binary.

* [FEATURE][BETA] [process-agent] adding process-agent See [#3449][] and [omnibus-software-181](https://github.com/DataDog/omnibus-software/pull/181)

# 5.15.0 / 07-18-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.14.1...5.15.0

### Changes
Please refer to the [Integrations Core Checks 5.15.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.15.0) for the list of changes on the core checks.
Please refer to the [Trace Agent 5.15.0 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.15.0) for the list of changes on the Trace Agent.

* [FEATURE] [kube] Allow to run agent on the node [#3401][]
* [FEATURE] [core] Adds fraction of file handles in use over system limit [#3395][]
* [FEATURE] [PrometheusCheck] add ignore_metrics array [#3394][]
* [FEATURE] pkg: Add process-agent to supervisor and flares [#3409][]
* [FEATURE] Get real host aliases for Cloud Foundry [#3406][]
* [FEATURE] [docker] add docker and orchestrator (ECS/Mesos/Nomad/Kubernetes/Swarm) version host tags. See [#3383][], [#3386][] and [#3403][]
* [FEATURE] [Windows] add additional calculator types [#3378][]
* [FEATURE] Mesos: extract marathon_app, chronos_job and chronos_job_owner tags. See [#3375][], [#3414][] and [#3417][]
* [FEATURE] [kubernetes] add kubernetes container name to metric tags [#3368][]
* [FEATURE] Add support for user/password authentication for the etcd autodiscovery store [#3357][]
* [FEATURE] Add support for %%pid%% template variables [#3404][], thanks [@sophaskins][] and [@jnewland][]
* [IMPROVEMENT] constant for container name label [#3405][], thanks [@sophaskins][]
* [IMPROVEMENT] Add container name tag in auto discovery [#3421][], thanks [@subuk][]
* [IMPROVEMENT] Disable kube_service tagging on four 403 errors from apiserver [#3413][]
* [IMPROVEMENT] Update Mac restart command [#3390][]
* [IMPROVEMENT] Try both 4001 and 2379 etcd ports in SD if not configured [#3351][]
* [SANITY] Moves common wait_for_async network function out to the Agent [#3408][]
* [SANITY] [util] Move `Timer` to its own `utils.timer` module [#3391][]
* [SANITY] [checks] Deprecate `AgentCheck.set` [#3385][]
* [SANITY] Remove manifest.in - no more use to us. [#3364][]

# 5.14.1 / 06-15-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.14.0...5.14.1

### Changes
Please refer to the [Integrations Core Checks 5.14.1 tag](https://github.com/DataDog/integrations-core/releases/tag/5.14.1) for the list of changes on the core checks.

* [IMPROVEMENT] Kubernetes: Reduce apiserver request count for pod_service_mapper. See [#3387][] and [integrations-core-476](https://github.com/DataDog/integrations-core/pull/476)
* [IMPROVEMENT] CentOS: Make sure we start the last and stop first. See [#3376][]
* [IMPROVEMENT] Docker: Make TLS settings more intuitive. See [#3373][]
* [BUGFIX] Autodiscovery: Fix multi-instance autodiscovery. See [#3341][]
* [BUGFIX] Network checks: Fix typo in the network exception log. See [#3374][]

# 5.14.0 / 06-05-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.13.2...5.14.0

### Dependency changes

* `paramiko` `2.1.2` (previously `1.15.2`), see [omnibus-software-141](https://github.com/DataDog/omnibus-software/pull/141)
* `pysnmp` `4.3.5` (previously `4.2.5`), see [omnibus-software-141](https://github.com/DataDog/omnibus-software/pull/141)

### Changes
Please refer to the [Integrations Core Checks 5.14.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.14.0) for the list of changes on the core checks.
Please refer to the [Trace Agent 5.14.0 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.14.0) for the list of changes on the Trace Agent.

* [IMPROVEMENT] Autodiscovery metrics have new tags when available:
  * Docker image name and tag ([#3350][])
  * ECS task name ([#3349][] and [#3358][])
  * Nomad task, group and job names ([#3289][])
  * Kubernetes service and creator (deployment/daemon_set/replica_set/job). See [#3300][] and [#3348][]
* [IMPROVEMENT] New PrometheusCheck base class to enable simpler development of integrations pulling Prometheus format metrics. See [#3317][], [#3344][] and [#3359][], thanks [@aerostitch][]
* [IMPROVEMENT] Autodiscovery: allow multiple instances per check. See [#3311][]
* [IMPROVEMENT] AWS: bump `boto` version to `2.46.1`. See [#3307][] and [omnibus-software-137](https://github.com/DataDog/omnibus-software/pull/137)
* [IMPROVEMENT] JMXFetch: Add support for `min_collection_interval`. See [jmxfetch-135](https://github.com/DataDog/jmxfetch/pull/135) and [jmxfetch-140](https://github.com/DataDog/jmxfetch/pull/140)
* [IMPROVEMENT] JMXFetch packaging: build JMXFetch with omnibus and store the jar on S3 bucket. See [dd-agent-omnibus-100](https://github.com/DataDog/dd-agent-omnibus/pull/100) and [#3220][]
* [IMPROVEMENT] Packaging: remove dependency on `pycrypto`. See [dd-agent-omnibus-175](https://github.com/DataDog/dd-agent-omnibus/pull/175)
* [IMPROVEMENT] Packaging: bump libxml2 version to `2.9.4`. See [omnibus-software-142](https://github.com/DataDog/omnibus-software/pull/142)
* [IMPROVEMENT] Utils, Proxy: add a utility function to deal with proxy configs and skipping. See [#3331][] and [#3356][]
* [BUGFIX] Alpine: make supervisor socket consistent with default. See [#3335][], thanks [@jonchiu][]
* [BUGFIX] Collector: fix misattribution of check instance warning. See [#3339][]
* [BUGFIX] Core: respect `ssl_skip_validation` when checking API key. See [#3346][], thanks [@jeffwidman][]
* [BUGFIX] GCE: Exclude `bosh_settings` from tags, as it frequently includes passwords. See [#3320][]
* [BUGFIX] Packaging: remove `agent/checks` from `PYTHONPATH`. See [#3315][]
* [BUGFIX] Packaging: Fix `==` bashism in package scripts. See [dd-agent-omnibus-174](https://github.com/DataDog/dd-agent-omnibus/pull/174)
* [BUGFIX] Packaging: Fix dependency on windows DLLs on Windows 2008R2 by duplicating them into the embedded path. See [dd-agent-omnibus-169](https://github.com/DataDog/dd-agent-omnibus/pull/169)
* [SANITY] Dogstatsd: Log hostname on initialization. See [#3332][]
* [SANITY] JMXFetch: Add warnings of breaking change coming with agent 6. See [#3318][]
* [SANITY] Packaging: Remove checks deps in `requirements.txt`. See [#3298][]

# 5.13.2 / 05-11-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.13.1...5.13.2

### Changes
Please refer to the [Integrations Core Checks 5.13.2 tag](https://github.com/DataDog/integrations-core/releases/tag/5.13.2) for the list of changes on the Integrations Core checks repository.

* [IMPROVEMENT] Flare: add `auto_conf` templates. See [#3330][]
* [BUGFIX] Dockerutil: use DockerUtil.image_name_extractor for all code paths. See [#3334][]
* [BUGFIX] Dockerutil: fix exception when image name is `None`. See [#3329][]
* [BUFGIX] Dockerutil: support systemd slices in cgroup paths. See [#3328][]
* [BUGFIX] Dockerutil: fix image name when using sha256 for specs. See [#3326][]
* [BUGFIX] Packaging: fix os detection for "exotic" distributions. See [dd-agent-omnibus-171](https://github.com/DataDog/dd-agent-omnibus/pull/171)
* [SANITY] Packaging: Remove reliance on `pedump` fork. See [dd-agent-omnibus-167](https://github.com/DataDog/dd-agent-omnibus/pull/167)

# 5.13.1 / 05-02-2017
**Docker Alpine and Source Install Only**

### Details
https://github.com/DataDog/dd-agent/compare/5.13.0...5.13.1

### Changes

* [BUGFIX] Redis: Fixes a bug where the redis python library would not install using the source install. See [integrations-core-389](https://github.com/DataDog/integrations-core/pull/389)


# 5.13.0 / 04-24-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.12.3...5.13.0

On this release the APM tracing agent is now enabled by *default* on supported platforms (linux).
Should you wish to disable it please set:
```
apm_enabled: no
```
in the relevant section in `datadog.conf` and restart the agent.

### Changes
Please refer to the [Integrations Core Checks 5.13.0 tag](https://github.com/DataDog/integrations-core/releases/tag/5.13.0) for the list of changes on the Integrations Core checks repository.
Please refer to the [Trace Agent 5.13.0 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.13.0) for the list of changes on the Trace Agent.

* [FEATURE] Docker, Service Discovery: Add ability to get docker IP address from Rancher labels for Rancher 1.3. See [#3265][]
* [FEATURE] Docker: improve network tagging. See [#3272][]
* [IMPROVEMENT] Kubeutil: catch errors from kubeutil init. See [#3310][]
* [BUGFIX] JMXFetch: fix race condition preventing SD initialization. See [jmxfetch-135](https://github.com/DataDog/jmxfetch/pull/135)
* [BUGFIX] Kubernetes_state: refactor gauge submission, fix `container.restarts`. See [#3297][]
* [BUGFIX] Dockerutil: fix net metrics in host mode. See [#3313][] and [#3314][]
* [SANITY] Windows: Remove system network check (metrics already reported by [integrations-core](https://github.com/DataDog/integrations-core/blob/master/network/check.py)). See [#3096][]
* [SANITY] Kafka: adding Kafka to list of JMX checks (NOP). See [#3304][]
* [REVERT] Core: SpooledTemporaryFile for subprocess output. See [#3291][]


# 5.12.3 / 03-31-2017
**Linux, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.12.2...5.12.3

### Changes
Please refer to the [Trace Agent 5.12.3 tag](https://github.com/DataDog/datadog-trace-agent/releases/tag/5.12.3) for the list of changes on the Trace Agent.

* [BUGFIX] Docker: Fix CGroup parsing. See [#3293][]

# 5.12.2 / 03-29-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.12.1...5.12.2

### Changes

* [BUGFIX] Cloud Metadata: Use Metadata-Flavor to ensure that tags are properly collected on GCE. See [#3288][]
* [BUGFIX] Forwarder: Fix error on removal of transactions. See [#3287][]
* [BUGFIX] Docker: Fix cgroup parsing on RancherOS. See [#3274][]

# 5.12.1 / 03-23-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.12.0...5.12.1

### Changes

* [BUGFIX] Source Install: Fixes a bug in the source install where the integrations wouldn't be properly installed. See [#3281][]
* [BUGFIX] Emitter: Force source type to system for legacy payload. See [#3280][]
* [BUGFIX] MySQL: Allow for configurable collection of replica statuses [integrations-core-288](https://github.com/DataDog/integrations-core/pull/288)
* [BUGFIX] MySQL: Slaves_connected should be a gauge. [integrations-core-291](https://github.com/DataDog/integrations-core/pull/291)

# 5.12.0 / 03-22-2017
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.11.3...5.12.0

### Integrations SDK
In all agents, we are now able to release independent check packages, so that we can update checks independently and also release 3rd party packages from the community. To aid in this, we now have three repos: the [agent repo](https://github.com/datadog/dd-agent), the [core integrations repo](https://github.com/datadog/integrations-core), and the [extras integrations repo](https://github.com/datadog/integrations-extras). Core integrations are officially supported by Datadog, extras are supported by the community.

### Windows packaging changes
The Windows agent is now always installed as a "per-machine"; previous versions installed as "per-user" by default.  Upgrades from "per-user" to "per-machine" are performed using the executable (.exe) distribution.
Please refer to the [dedicated page on the wiki](https://github.com/DataDog/dd-agent/wiki/Windows-Agent-Installation) for detailed upgrade instructions.

The Windows agent is now compatible with 64-bit platforms only.

The Windows agent is now built with Omnibus. It now ships a full python interpreter, easing the [install of additional python libraries](https://github.com/DataDog/dd-agent/wiki/Install-additional-pip-dependencies-in-the-agent-env) for custom checks.

The Windows agent is now digitally signed.

### New Integrations

* Twemproxy. See [integrations-core-15](https://github.com/datadog/integrations-core/pull/15)

### Updated integrations

* ActiveMQ
* Consul
* Couchbase
* Disk
* DNS Check
* Docker
* Docker Daemon
* Elasticsearch
* Etcd
* JMXFetch
* Http Check
* HAProxy
* IIS
* Kubernetes
* Marathon
* Mesos
* Mongo
* MySQL
* Network
* OpenStack
* PowerDNS
* PGBouncer
* PHP FPM
* Postgres
* Process
* Redis
* Spark
* SQLServer
* Riak
* TCP Check
* TokuMX
* VSphere
* Windows
* Yarn
* Zookeeper

### Dependency Upgrades

* docker-py `1.10.6` (previously `1.8.1`). See [docker-py's changelog](https://github.com/docker/docker-py/blob/master/docs/change-log.md)
* kafka-python `1.3.1` (previously `1.2.5`). See [kafka-python's changelog](https://github.com/dpkp/kafka-python/blob/master/CHANGES.md)
* psycopg2 `2.6.2` (previously `2.6`). See [psycopg2's changelog](http://initd.org/psycopg/docs/news.html)
* pyro4 `4.36` (previously `4.35`, Thanks [@jeffwidman][]). See [pyro4's changelog](https://pythonhosted.org/Pyro4/changelog.html)
* scandir `1.5` (previously `1.2`)
* requests `2.11.1` (previously `2.6.2`). See [requests's changelog](https://github.com/kennethreitz/requests/blob/master/HISTORY.rst)
* Python (Linux only) `2.7.13` (previously `2.7.11`). See [omnibus-software-93](https://github.com/DataDog/omnibus-software/pull/93), [omnibus-software-126](https://github.com/DataDog/omnibus-software/pull/126), [omnibus-software-127](https://github.com/DataDog/omnibus-software/pull/127)
* OpenSSL `1.0.2k` (previously `1.0.2j`). See [omnibus-software-124](https://github.com/DataDog/omnibus-software/pull/124)

### Changes

* [FEATURE] Core: Adds a local DNS cache. See [#3197][]
* [FEATURE] JMXFetch: Add `histogram` metric type. See [jmxfetch-115](https://github.com/DataDog/jmxfetch/issues/115)
* [FEATURE] JMXFetch: Add `list_jvms` command to list available JVMs when using the Attach API. See [jmxfetch-100](https://github.com/DataDog/jmxfetch/issues/100), [jmxfetch-112](https://github.com/DataDog/jmxfetch/issues/112) (Thanks [@cslee00][])
* [FEATURE] JMXFetch: Add tag blacklisting. See [jmxfetch-116](https://github.com/DataDog/jmxfetch/issues/116)
* [FEATURE] JMXFetch: Add user tags definition for MBeans. See [jmxfetch-117](https://github.com/DataDog/jmxfetch/issues/117).
* [FEATURE] JMXFetch: Enable service discovery via a named pipe. See [jmxfetch-113](https://github.com/DataDog/jmxfetch/issues/113)
* [FEATURE] JMXFetch: Support `javax.management.openmbean.TabularData` attribute types. See [jmxfetch-111](https://github.com/DataDog/jmxfetch/issues/111), [jmxfetch-128](https://github.com/DataDog/jmxfetch/issues/128) (Thanks [@brothhaar][])
* [FEATURE] JMXFetch: Support user tag value substitution by attribute name. See [jmxfetch-117](https://github.com/DataDog/jmxfetch/issues/117).
* [FEATURE] Service Discovery, JMX: Allows JMX Checks to use Service Discovery. See [#3010][], [#3150][]
* [FEATURE] Service Discovery: Add a Zookeeper backend. See [#3038][]
* [FEATURE] Service Discovery: Use a template cache to reduce calls to template store. See [#3060][]
* [FEATURE] Service Discovery: Add namespace, daemon_set and replica_set tags for kubernetes. See [#3176][]
* [FEATURE] Windows: Adds new service and packaging. See [#2417][], [#3244][]
* [IMPROVEMENT] Core: Allows developer mode to be used without profiling. See [#2898][] (Thanks [@cberry777][])
* [IMPROVEMENT] Core: Better EC2 detection. See [#3174][]
* [IMPROVEMENT] Core: Splits the payload into a legacy payload and a metrics payload. See [#3180][], [#3240][]
* [IMPROVEMENT] Forwarder: Validate API Key against any endpoint. See [#3256][]
* [IMPROVEMENT] JMXFetch: Print exception messages on Attach API connection failures. See [jmxfetch-122](https://github.com/DataDog/jmxfetch/issues/122) (Thanks [@aoking][])
* [IMPROVEMENT] Packaging: Don't require pgp key to be added on every install. [dd-agent-omnibus-143](https://github.com/DataDog/dd-agent-omnibus/pull/143)
* [IMPROVEMENT] Windows: Better pagefile memory on Windows. See [#3072][]
* [BUGFIX] Aggregator: Parse tags even if sample rate is bad. See [#3073][]
* [BUGFIX] Core: Fix config parsing when variable is missing. See [#3041][]
* [BUGFIX] Core: Exclude sensitive data from Google Cloud metadata. See [#3076][]
* [BUGFIX] Core: Stops agent from dying when no proc table is returned. See [#3043][] (Thanks [@ahamilton55][])
* [BUGFIX] Flare: Fix config file parsing. See [#3040][], [#3059][]
* [BUGFIX] JMXFetch: Allow specifying no alias on detailed attribute. See [jmxfetch-133](https://github.com/DataDog/jmxfetch/issues/133)
* [BUGFIX] JMXFetch: Fix connectivity loss when multiple instances are assigned to a same JVM. See [jmxfetch-124](https://github.com/DataDog/jmxfetch/issues/124)
* [BUGFIX] JMXFetch: Parse string-defined ports to integers in user configurations. See [jmxfetch-121](https://github.com/DataDog/jmxfetch/issues/121)
* [BUGFIX] JMXFetch: Support `java.util.Map` attribute types. See [jmxfetch-130](https://github.com/DataDog/jmxfetch/issues/130)
* [BUGFIX] JMXFetch: Support list-defined user tags at instance level. See [jmxfetch-132](https://github.com/DataDog/jmxfetch/issues/132)
* [BUGFIX] Windows GUI: Better detection and termination of old processes on startup. See [#3125][]
* [DEPRECATE] Core: hard-deprecate start/stop/restart/status commands. See [#3004][]

### Integration Changes

* [FEATURE] DNS Check: Change to a network check. See [#2924][]
* [FEATURE] Docker Daemon: Add a number of new metrics for container and volume counts. See [#2740][], [#3077][]. (Thanks [@parkr][])
* [FEATURE] Docker Daemon: Tag container metrics with swarm if available. See [#3182][], [#3243][]
* [FEATURE] Http Check: Mark the Service Check as down if result matches content match option. See [#3069][]
* [FEATURE] HAProxy: Allow the use of Unix Socket URLs. See [#3005][] (Thanks [@sj26][])
* [FEATURE] HAProxy: Add support for haproxy.backend.uptime. See [#2639][]
* [FEATURE] Kubernetes: Allow kublet host to be specified from environment. See [#3051][] (Thanks [@stonith][])
* [FEATURE] Kubernetes: Add image_name and image_tag to container metrics. See [#2990][] (Thanks [@tarvip][])
* [FEATURE] Kubernetes State: Add State metrics for pods and containers. See [#3070][]. (Thanks [@therc][])
* [FEATURE] Marathon: Add token auth. See [#3208][], [#3037][]. (Thanks [@jkorzekwa-atlassian][])
* [FEATURE] Mongo: Add metric with number of databases. See [#3124][]. (Thanks [@mpidlisnyi][])
* [FEATURE] Network: Add InCsumErrors to UDP metrics. See [#3117][]. (Thanks [@diver-in-sky][])
* [FEATURE] Network: Adds an option to split apart connection states. See [#3158][], [#2856][]. (Thanks [@joewilliams][])
* [FEATURE] PowerDNS: Add support for v4. See [#3166][], [#3066][]. (Thanks [@jimmystewpot][])
* [FEATURE] Redis: Add some additional metrics. See [#2749][]
* [FEATURE] SQLServer: Allow connection through pyodbc as well as adodbapi. See [integrations-core-259](https://github.com/DataDog/integrations-core/pull/259), [integrations-core-264](https://github.com/DataDog/integrations-core/pull/264), [omnibus-software-129](https://github.com/DataDog/omnibus-software/pull/129), [dd-agent-omnibus-154](https://github.com/DataDog/dd-agent-omnibus/pull/154)
* [FEATURE] Riak: Add support for Riak Security. See: [#2389][], [#3168][]. (Thanks [@hamano][])
* [FEATURE] Riak: Add support for Riak 2.0 LTS. See: [#3189][], [#2762][]. (Thanks [@jcapricebasho][])
* [FEATURE] VSphere: Improve tagging, v6 compatibility, infrastructure reporting and performance. See [#3055][]
* [IMPROVEMENT] Consul: Add configuration parameter that overrides `MAX_SERVICES`. See [integrations-core-140](https://github.com/DataDog/integrations-core/pull/140)
* [IMPROVEMENT] Couchbase: Add user specified tags to service checks. See [#3079][]. (Thanks [@arzarif][])
* [IMPROVEMENT] DNS Check: Support monitoring performance of NXDOMAIN queries. See [#2849][]. (Thanks [@jnewland][])
* [IMPROVEMENT] Docker: Improved Hostname logic for containers. See [#3116][]
* [IMPROVEMENT] Docker: Better detection and handling of incorrect PIDs. See [#3218][], [integrations-core-237](https://github.com/DataDog/integrations-core/pull/237)
* [IMPROVEMENT] Docker Daemon: Make Docker Healthcheck a Service Check. See [#2859][]
* [IMPROVEMENT] Etcd: Report errors connecting to etcd endpoint. See [#3007][] (Thanks [@pbitty][])
* [IMPROVEMENT] HTTP Check: Adds optiont to disable default http headers. See [integrations-core-182](https://github.com/DataDog/integrations-core/pull/182). (Thanks [@eredjar][])
* [IMPROVEMENT] HTTP Check: Remove noisy debug logging. See [integrations-core-267](https://github.com/DataDog/integrations-core/pull/267)
* [IMPROVEMENT] Kubernetes: handle multiple namespaces. See [#3028][]
* [IMPROVEMENT] Kubernetes: Support api server auth with a cert. See [#3145][]
* [IMPROVEMENT] Kubernetes: Allow configurable custom certs. See [#3160][]
* [IMPROVEMENT] Kubernetes: Add support for kublet auth when the read-only port is disabled. See [#3142][], [integrations-core-242](https://github.com/DataDog/integrations-core/pull/242)
* [IMPROVEMENT] Kubernetes: Updates the path to grab certs. See [#3210][]. (Thanks [@dturn][])
* [IMPROVEMENT] Marathon: Add option to disable SSL validation and support groups. See [#3140][]. (Thanks [@Carles-Figuerola][])
* [IMPROVEMENT] Mesos: Adds `mesos.registrar.log.recovered` to metrics. [integrations-core-260](https://github.com/DataDog/integrations-core/pull/260)
* [IMPROVEMENT] MySQL: Add another format for innodb writes innodb. See [#3148][]
* [IMPROVEMENT] Network: Use a global counter for thread pool size. See [#3095][], [#3080][]
* [IMPROVEMENT] OpenStack: Support regex for Network ID exclusion. See [integrations-core-181](https://github.com/DataDog/integrations-core/pull/181)
* [IMPROVEMENT] PHP-FPM: Include Custom Tags in Service Check. See [#3109][]
* [IMPROVEMENT] PHP-FPM: Add http_host tag to metrics. See [#3165][], [#3074][]. (Thanks [@toksvaeth][])
* [IMPROVEMENT] Postgres: Makes db size collection optional. See [#3035][] (Thanks [@jstotzs][])
* [IMPROVEMENT] Spark: No events on job status change. See [#3194][]. This is a potentially breaking change, but it was flooding event streams with what, for most people, was useless information.
* [IMPROVEMENT] TCP Check: add instance tags to respose_time metric. See [#3118][], [#3206][]. (Thanks [@mberner-ch][])
* [IMPROVEMENT] TokuMX: Skip dbs that aren't accessible. See [#3093][]. (Thanks [@pbrisbin][])
* [IMPROVEMENT] Yarn: Add configurable application tags. See [#3041][], [integrations-core-261](https://github.com/DataDog/integrations-core/pull/261)
* [IMPROVEMENT] Zookeeper: Include user specified tags. See [#3078][]. (Thanks [@arzarif][])
* [IMPROVEMENT] Trace Agent: Watchdog restarts trace agent if it consumes too much memory or opens too many network connections. [trace-trace-agent-182](https://github.com/DataDog/datadog-trace-agent/pull/182)
* [IMPROVEMENT] Trace Agent: Reduce sampler log verbosity and expose internal state with Go expvar. [datadog-trace-agent-248](https://github.com/DataDog/datadog-trace-agent/pull/248)
* [IMPROVEMENT] Trace Agent: Adaptive sampling. [datadog-trace-agent-228](https://github.com/DataDog/datadog-trace-agent/pull/228)
* [IMPROVEMENT] Trace Agent: Weight spans using their sample rate. [datadog-trace-agent-226](https://github.com/DataDog/datadog-trace-agent/pull/226)
* [IMPROVEMENT] Trace Agent: Stream decoding. [datadog-trace-agent-227](https://github.com/DataDog/datadog-trace-agent/pull/227)
* [IMPROVEMENT] Trace Agent: Quantize SQL AS aliases. [trace-trace-agent-225](https://github.com/DataDog/datadog-trace-agent/pull/225)
* [IMPROVEMENT] Trace Agent: Updated the output of trace-agent info. [datadog-trace-agent-219](https://github.com/DataDog/datadog-trace-agent/pull/219)
* [BUGFIX] Disk: Tag metrics with filesystem tag key instead of filesystem itself. See [integrations-core-252](https://github.com/DataDog/integrations-core/pull/252)
* [BUGFIX] Docker: Fix whitelist pattern matching. See [#3048][]
* [BUGFIX] Docker: Fix image tag extraction. See [#3172][]
* [BUGFIX] Docker Daemon: Report as many cgroup metrics as possible. See [#3134][]
* [BUGFIX] Elasticsearch: Fix autoconf to use the correct port. See [#3129][]
* [BUGFIX] Http Check: Fix content match for non ascii characters. See [#3100][]
* [BUGFIX] IIS: Fix is_2008 option. See [#3039][]
* [BUGFIX] Kubernetes: Only use annotations for service discovery once per pod. See [#2901][] (Thanks [@mikekap][])
* [BUGFIX] Kubernetes: Fix tags param in example config file. See [#3044][]
* [BUGFIX] Kubernetes: Remove potentially sensitive information from logs. See [integrations-core-254](https://github.com/DataDog/integrations-core/pull/254)
* [BUGFIX] Marathon: Catch nodata found errors and report them properly. See [#3127][]
* [BUGFIX] MySQL: Use `information_schema` in versions below 5.6.0. See [#3196][]
* [BUGFIX] MySQL: Fix version comparison operator. See [integrations-core-231](https://github.com/DataDog/integrations-core/pull/231)
* [BUGFIX] OpenStack: Fallback to v2 endpoint if v2.1 fails. See [#3154][]
* [BUGFIX] PGBouncer: Disable PGBouncer on Windows, as it doesn't work. See [#3252][]
* [BUGFIX] Process: No longer errors when process is down. See [#3052][] and [#3049][] (Thanks [@Radstake][])
* [BUGFIX] Process: Send all configured tags with process check. See [#2976][] (Thanks [@jdavisp3][])
* [BUGFIX] Spark: Properly report job IDs. See [#3111][]
* [BUGFIX] Spark: Fix event source name. See [#3193][]
* [BUGFIX] SQLServer: Stops passwords from leaking into logs. See [#3053][]
* [BUGFIX] SQLServer: Collect metric list if SQLServer is not up during check init. See [#3067][]
* [BUGFIX] Trace Agent: Now shells out to dd-agent to retrieve hostname. [datadog-trace-agent-242](https://github.com/DataDog/datadog-trace-agent/pull/242)
* [BUGFIX] Trace Agent: Normalize environment strings in spans and in the configuration [datadog-trace-agent-233](https://github.com/DataDog/datadog-trace-agent/pull/233)
* [BUGFIX] Trace Agent: Fixed race issue between concentrator and sampler. [datadog-trace-agent-229](https://github.com/DataDog/datadog-trace-agent/pull/229)
* [DEPRECATE] ActiveMQ: Remove old JMX config file. See [#3141][]


# 5.11.3 / 02-27-2017
**Mac OS only**

### Details

There was an issue with Gohai on Mac OS >= 10.11 leading to high CPU utilization. As a short term solution, Gohai has been disabled on Mac OS.

### Changes

* [OTHER] Do not run Gohai on Mac OS. See [#3224][].


# 5.11.2 / 02-13-2017
**Linux and Docker only**

### Details

There was an issue releasing 5.11.1 by which the package shipped still contained the bugs reported in 5.11.0 plaguing the SNMP check. Only affected debian package and the docker release.

### Changes

* [RELEASE] Releasing actual bugfix expected with 5.11.1, with version bump to 5.11.2.


# 5.11.1 / 02-13-2017
**Linux and Docker only**

### Details

There was a regression in 5.11.0 due to an inadverted subdependency upgrade, breaking the SNMP check.

### Changes

* [REGRESSION] pinning of `pyasn1` to version 0.1.9. See [#3183][], [omnibus-software-111](https://github.com/DataDog/omnibus-software/pull/111), [omnibus-software-114](https://github.com/DataDog/omnibus-software/pull/114), [omnibus-software-115](https://github.com/DataDog/omnibus-software/pull/115).


# 5.11.0 / 02-08-2017
**Linux and Docker only**

### Details

This release bundles the datadog-trace-agent as part of Linux and Docker installs. The dd-agent codebase contains a minimal set of changes to ensure the new trace-agent process will plug neatly into existing agent installs. Beta customers of Datadog's tracing tool will have received an email detailing the steps to transition to dd-agent 5.11.0 from the deprecated dd-trace-agent package.

For more information:
- https://github.com/DataDog/dd-agent/compare/5.10.1...5.11.0
- https://github.com/DataDog/datadog-trace-agent
- https://github.com/DataDog/datadog-trace-agent/releases/tag/5.11.0

### Changes

* [IMPROVEMENT] Supervisor: Add trace-agent as an optional process managed by supervisor
* [IMPROVEMENT] Flare: Add trace-agent log file to flare output
* [IMPROVEMENT] Core: append the output of trace-agent -info to service datadog-agent info command


# 5.10.1 / 11-21-2016
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.10.0...5.10.1

### Updated Integrations

* RiakCS
* Mongo

### Changes
* [IMPROVEMENT] Core/Forwarder: stop flushing after 10s. See [#3018][].
* [IMPROVEMENT] Core: isolate system checks. See [#3011][].
* [IMPROVEMENT] RiakCS: support Riak CS 2.1+ stats format. See [#2920][]. (Thanks [@millerdev][])
* [IMPROVEMENT] Status: Silence requests exception. See [#3023][].
* [IMPROVEMENT] SpooledTemporaryFile for subprocess output. See [#3002][].

* [BUGFIX] Core: fix unintended subprocess_output empty output errors. See [#3024][].
* [BUGFIX] Core/Multiple Checks: Only set `psutil.PROCFS_PATH` once in the collector. See [#3013][].
* [BUGFIX] Core: use proxy for API key status check in info page. See [#3012][]. (Thanks [@2rs2ts][])
* [BUGFIX] Mongo: use db.current_op instead of manually querying. See [#3016][] (Thanks [@ebroder][])
* [BUGFIX] Mongo: use `currentOp` for monodb 3.1+. See [#3015][] (Thanks [@lattwood][])

* [DEPRECATE] Process: `procfs_path` is now deprecated, should be set in `datadog.conf`. See [#3013][].


# 5.10.0 / 11-09-2016
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.9.1...5.10.0

### Kubernetes: metrics from the Kube State API

The new `kubernetes_state` check pulls metrics from the Kubernetes State API.

See [#2890][], [#2984][] and [omnibus-software-85](https://github.com/DataDog/omnibus-software/pull/85) for more details.

### RPM package for SUSE
The Agent is now available as an RPM package for SUSE. Please follow the instructions on our
[Agent installation page](https://app.datadoghq.com/account/settings#agent) to use it.

For more details, see related PRs [#2900][], [#2937][], [omnibus-software-72](https://github.com/DataDog/omnibus-software/pull/72), [dd-agent-omnibus-90](https://github.com/DataDog/dd-agent-omnibus/pull/90)

### Linux packages: change of ownership of `/opt/datadog-agent` directory
The Linux packages (`deb` and `rpm`) now make the `dd-agent` user and group own the `/opt/datadog-agent` folder and
its contents when they're installed. This shouldn't cause any change on regular installations of the Agent,
but please take this change into account if you customize the ownership/permissions of the `/opt/datadog-agent` directory or
its contents.

For more details, see related PR: [dd-agent-omnibus-97](https://github.com/DataDog/dd-agent-omnibus/pull/97)

### Python dependencies upgrade
We have updated the following python dependencies shipped with the Agent. If you happen to run any
custom checks that rely on the former versions please make necessary amends:

* kazoo `2.2.1` (previously `1.3.1`). See [Kazoo's changelog](https://github.com/python-zk/kazoo/blob/master/CHANGES.rst).
* psutil `4.4.1` (previously `3.3.0`). See [psutil's changelog](https://github.com/giampaolo/psutil/blob/master/HISTORY.rst).
* curl `7.51.0` (previously `7.50.0`). See [curl's changelog](https://curl.haxx.se/changes.html[#7][]_51_0).

### Updated integrations

* Apache
* Ceph
* Consul
* Docker
* Elasticsearch
* FluentD
* Haproxy
* Http check
* Kafka
* Kubernetes
* Marathon
* Mesos
* Mongo
* MySQL
* Openstack
* PGBouncer
* Postgres
* Process
* RabbitMQ
* Redis
* Spark
* SSH check

### Changes
* [FEATURE] Core: Add support for `sum` `histogram_aggregates` type. See [#2780][] (Thanks [@ross][])
* [FEATURE] Core: Display api key status on the info page. See [#2947][]
* [FEATURE] Consul: Add net latency metrics. See [#2757][] (Thanks [@ross][])
* [FEATURE] Haproxy: Allow per-instance custom tags. See [#2649][], [#2951][] (Thanks [@theojulienne][])
* [FEATURE] Kubernetes: Add CPU and memory capacity reporting. See [#2935][] (Thanks [@markine][])
* [FEATURE] Mongo: Add metrics for fsyncLocked-ness, replset votes and vote fraction. See [#2975][] (Thanks [@ebroder][])
* [FEATURE] Process: Support pid file. See [#2607][] (Thanks [@n0ts][])
* [FEATURE] Spark: Support clusters provisioned using Apache Mesos. See [#2797][] (Thanks [@zachradtka][])
* [IMPROVEMENT] Ceph: Handle `HEALTH_WARNING` status. See [#2929][] (Thanks [@ccocsas][])
* [IMPROVEMENT] Consul: Remove warning when no whitelist is defined. See [#2955][]
* [IMPROVEMENT] Consul: Support multiple instances. See [#2948][]
* [IMPROVEMENT] Core: forwarder: Do not requeue all responses. See [#2840][]
* [IMPROVEMENT] Core: collector: Catch exceptions raised by system checks. See [#2973][]
* [IMPROVEMENT] Docker: Set `alert_type` to `error` for oom and kill events. See [#2866][]
* [IMPROVEMENT] Docker: Set exec events' priority to low. See [#2960][]
* [IMPROVEMENT] Docker/Kubernetes: Filter containers consistently. See [#2836][]
* [IMPROVEMENT] Elasticsearch: Add support for ES 5.x. See [#2989][] (Thanks [@ptinsley][] and [@alexef][])
* [IMPROVEMENT] FluentD: Add collection timeout. See [#2978][] (Thanks [@mattrobenolt][])
* [IMPROVEMENT] Kafka: Document specifying multiple Kafka / ZK nodes. See [#2956][] (Thanks [@jeffwidman][])
* [IMPROVEMENT] Kafka: Upgrade `kazoo` dep to `2.2.1`. See [#2964][], [omnibus-software-84](https://github.com/DataDog/omnibus-software/pull/84)
* [IMPROVEMENT] Kubernetes: Use the env var `KUBERNETES_SERVICE_HOST` if present. See [#2921][] (Thanks [@arohner][])
* [IMPROVEMENT] Kubernetes: Add `namespace` tag to `kubernetes.pods.running`. See [#2931][]
* [IMPROVEMENT] Kubernetes: Add some tags to events. See [#2926][]
* [IMPROVEMENT] Marathon: Count running/pending deployments. See [#2788][] (Thanks [@bradhe][])
* [IMPROVEMENT] Packaging: Upgrade `psutil` to 4.4.1. See [#2957][], [omnibus-software-82](https://github.com/DataDog/omnibus-software/pull/82)
* [IMPROVEMENT] Packaging: Upgrade version of `datadogpy` shipped with Linux packages. See [omnibus-software-80](https://github.com/DataDog/omnibus-software/pull/80)
* [IMPROVEMENT] PGBouncer: Support SSL connections to PGBouncer. See [#2885][], [#2967][] (Thanks [@dblackdblack][])
* [IMPROVEMENT] Postgres: Allow UNIX socket path as `host` config value. See [#2734][], [#2968][] (Thanks [@DylanFrese][])
* [IMPROVEMENT] RabbitMQ: Add option to skip SSL verification. See [#2991][] (Thanks [@iancward][])
* [IMPROVEMENT] Redis: Fix tags on `can_connect` service check. See [#2803][] (Thanks [@gphat][])
* [IMPROVEMENT] Redis: Enable monitoring of SSL-ified redis servers. See [#2674][] (Thanks [@dblackdblack][])
* [IMPROVEMENT] SSH Check: Support ECDSA keys (<= 256bits). See [#2965][] (Thanks [@n0ts][])
* [BUGFIX] Apache: Add timeout on connection to Apache status URL See [#2928][]
* [BUGFIX] Core: Avoid CPU spikes caused by subprocess calls. See [#2950][]
* [BUGFIX] Core: Catch `EOFError` when loading info page. See [#2972][]
* [BUGFIX] Core: Display expected service check count. See [#2938][]
* [BUGFIX] Core: Handle timezone encodings on Windows. See [#2942][]
* [BUGFIX] Core: Ignore all non-unicode-decodable characters in collector's emitter. See [#2941][]
* [BUGFIX] Core: In dev mode, fallback to `/tmp` to dump pstats. See [#2934][]
* [BUGFIX] Core: On the Windows UI, set color to white for background of info page. See [#2970][]
* [BUGFIX] Core: On Windows, retry on process restart failures. See [#2897][]
* [BUGFIX] Kubernetes: Fix kubelet health check request. See [#2887][] (Thanks [@yannrouillard][])
* [BUGFIX] Kubernetes: Fix parsing of units in Kubernetes resource quantities. See [#2908][] (Thanks [@therc][])
* [BUGFIX] Http Check: Fix SSL certificate parsing issue related to strptime. See [#2915][] (Thanks [@ghTravis][])
* [BUGFIX] Mesos Slave: Connect to master with same protocol as slave. See [#2910][] (Thanks [@mcclurmc][])
* [BUGFIX] Service Discovery: Fix single check reload on `auto_conf` templates and removed containers. See [#3006][]
* [BUGFIX] Mongo: Fix case when check would send password in clear. See [#2940][]
* [BUGFIX] Mongo: Fix hostname detection when username/password are part of the uri. See [#2894][] (Thanks [@ibwhite][])
* [BUGFIX] MySQL: Improve innodb engine status check on RDS Aurora. See [#2971][] (Thanks [@scottgeary][])
* [BUGFIX] MySQL: Cast password to string to avoid issues with number-only passwords. See [#2983][] (Thanks [@michalyao][])
* [BUGFIX] Openstack: Add missing SSL `verify` param to 2 `requests` calls. See [#2877][] (Thanks [@jcejohnson][])
* [BUGFIX] Windows packaging: Terminate `agent-manager.exe` on uninstall/upgrade. See [#2982][]

# 5.9.1 / 09-30-2016
**Linux, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.9.0...5.9.1

### Build/Packaging Issue in 5.9.0
A packaging issue led to issues with the Spark integration when running Agent 5.9.0. This release fixes the issue.

### Updated integrations
* Kubernetes
* Spark

### Changes
* [BUGFIX] Dogstatsd: fix ipv6 fallback to ipv4. See [#2879][]
* [BUGFIX] Kubernetes: Fix incorrect time conversion for Kubernetes events. See [#2873][] (Thanks [@yannrouillard][])
* [BUGFIX] Packaging: Build with the corresponding dd-agent-omnibus branch ( [5.9.x](https://github.com/DataDog/dd-agent-omnibus/tree/5.9.x) )
* [BUGFIX] Packaging: include latest repo keys. See above.
* [BUGFIX] Spark: fix missing libraries issue.


# 5.9.0 / 09-27-2016
**Linux, Windows, Docker and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.8.5...5.9.0

### Kafka-Python library update
Because we have bumped the library version for the `kafka-python` package, if you happen to run any custom
checks that rely on the former version please make necessary amends. We apologize for any inconvenience.
See [#2709][] for reference.

### Updated integrations
* Apache
* Cassandra
* Ceph
* Disk Check
* DNS
* Docker
* Elasticsearch
* Gearman
* HTTP Check
* IIS
* JMXFetch
* Kafka Consumer
* Kubernetes
* Linux Check
* Marathon
* Mesos
* Mongo
* MySQL
* Network Check
* OpenStack
* Php5_fpm
* Postgres
* Process
* RabbitMQ
* Redis
* Spark
* SSH
* vSphere
* Windows

### Deprecated integrations
* Jenkins - Replaced check with plug-in. Details below.

### Changes
* [ENHANCEMENT] Use JMXFetch 0.12.0 ( [Changelog](https://github.com/DataDog/jmxfetch/blob/master/CHANGELOG.md) )

* [SECURITY] The deb and rpm packages now bundle OpenSSL 1.0.2i. For more details, see the [security advisory](https://www.openssl.org/news/secadv/20160922.txt), [omnibus-software-76](https://github.com/DataDog/omnibus-software/pull/76)

* [FEATURE] Apache: add connection status metrics. See [#2622][] (Thanks [@gzysk8][])
* [FEATURE] Core: dogstatsd: Added support for IP agnostic connections. See [#2619][]
* [FEATURE] Curl: support for HTTP2. See [omnibus-software-65](https://github.com/DataDog/omnibus-software/pull/65)
* [FEATURE] Dns_check: Allow querying a custom record type. See [#2653][]
* [FEATURE] Docker_daemon: resolve hierarchy by looking at procfs <pid>/cgroup. See [#2537][]
* [FEATURE] Gearman: Add per-task gearman metrics. See [#2672][] (Thanks [@nyanshak][])
* [FEATURE] Http_check: Add allow_redirects parameter. See [#2586][] (Thanks [@n0ts][])
* [FEATURE] Http_check: Add ability to use post method. See [#2544][]
* [FEATURE] Http_check: SNI support for cert_expiration. See [#2521][]
* [FEATURE] Kubernetes: Improve service discovery to only reload checks that need it. See [#2551][]
* [FEATURE] Kubernetes: Ingest k8s events + limits and requests metrics. See [#2551][]
* [FEATURE] Linux: make /proc configurable. See [#2482][]
* [FEATURE] Mongo: Apply yaml-configured tags to service checks. See [#2575][] (Thanks [@avaughan89][])
* [FEATURE] Mysql: Allow `connection_timeout` to be set for MySQL checks. See [#2729][] (Thanks [@scottgeary][])
* [FEATURE] Process: Option to search processes by PID. See [#2119][] (Thanks [@handigarde][])
* [FEATURE] Spark: spark standalone support. See [#2752][] (Thanks [@zachradtka][]), [omnibus-software-73](https://github.com/DataDog/omnibus-software/pull/73), [dd-agent-omnibus](https://github.com/DataDog/dd-agent-omnibus/pull/91)

* [IMPROVEMENT] Cassandra: add read and write latency ColumnFamily metrics. See [#2483][]
* [IMPROVEMENT] Ceph: improve health metrics. See [#2852][]
* [IMPROVEMENT] Ceph: update to support 10.0.2.2. See [#2805][]
* [IMPROVEMENT] Core: avoid calls to service discovery from dogstatsd. See [#2798][]
* [IMPROVEMENT] Core: Add an HTTP timeout to many integrations. See [#2673][] (Thanks [@gphat][])
* [IMPROVEMENT] Core: expiration should adjust to longer collection intervals (>300s). See [#2541][]
* [IMPROVEMENT] Core: remove events & resources api_key. See [#2557][]
* [IMPROVEMENT] Core: remove noisy logs. See [#2715][] (Thanks [@ensonik][])
* [IMPROVEMENT] Disk: handle multilines df output. See [#2733][]
* [IMPROVEMENT] Docker: Improve service discovery to only reload checks that need it. See [#2702][]
* [IMPROVEMENT] Docker: Add CPU throttling stats to Docker metrics. See [#2724][] (Thanks [@ejholmes][])
* [IMPROVEMENT] Dogstatsd: fix server address when non_local_traffic is passed. See [#2691][]
* [IMPROVEMENT] Elasticsearch: Add missing metrics. See [#2758][] (Thanks [@mdelaney][])
* [IMPROVEMENT] Elasticsearch: Add elastic search cluster name to tags. See [#2744][], [#2820][] and [#2826][]
* [IMPROVEMENT] Flare: Close the tar file cleanly once upload is done. See [#2621][]
* [IMPROVEMENT] Gohai: Processes - simplify payload. See [#2600][]
* [IMPROVEMENT] Gohai: CPU - take into account environments with multiple physical processors. See [gohai-32](https://github.com/DataDog/gohai/issues/32)
* [IMPROVEMENT] Http_check: log exceptions 🔊. See [#2704][]
* [IMPROVEMENT] Kafka_consumer: bumping kafka-python package version to 1.2.5. See [#2709][], [omnibus-software-70](https://github.com/DataDog/omnibus-software/pull/70)
* [IMPROVEMENT] Kubernetes: Add ability to specify service discovery via kubernetes annotations. See [#2848][] (Thanks [@mikekap][])
* [IMPROVEMENT] Kubernetes: disable use_histogram. See [#2542][]
* [IMPROVEMENT] Kubernetes: Log URL in kubelet check failures and service checks. See [#2735][] (Thanks [@therc][])
* [IMPROVEMENT] Mesos: make SSL check optional. See [#2809][]
* [IMPROVEMENT] Mongo: Adds metrics for collections. See [#2739][]
* [IMPROVEMENT] Mongo: Support X.509 authentication. See [#2713][]
* [IMPROVEMENT] Multiple integrations: Add an HTTP timeout to many integrations. See [#2673][] (Thanks [@gphat][])
* [IMPROVEMENT] Network: implement check using psutil on Windows. See [#2499][]
* [IMPROVEMENT] Openstack: openstack should pick-up on proxy settings set on agent. See [#2572][]
* [IMPROVEMENT] Openstack: nova/neutron extend name search. See [#2627][]
* [IMPROVEMENT] Packaging: debian - only create dd-agent group if it doesn't already exist. See [dd-agent-omnibus-89](https://github.com/DataDog/dd-agent-omnibus/pull/89)
* [IMPROVEMENT] Packaging: linux - correctly silence configcheck. See [dd-agent-omnibus-86](https://github.com/DataDog/dd-agent-omnibus/pull/86)
* [IMPROVEMENT] Packaging: debian - remove configcheck output when upgrading. See [dd-agent-omnibus-85](https://github.com/DataDog/dd-agent-omnibus/pull/85)
* [IMPROVEMENT] Php5_fpm: Allow host header override. See [#2779][] (Thenks [@allixsenos][])
* [IMPROVEMENT] Postgres: Allow to use psycopg2. See [#2782][]
* [IMPROVEMENT] Process: Add metrics for avg, max, and min run times for processes. See [#2531][] (Thenks [@garnermccloud][])
* [IMPROVEMENT] Process: Add system.processes.mem.pct metric to process check. See [#2801][]
* [IMPROVEMENT] Python: Upgrade to 2.7.12. See [omnibus-software-63](https://github.com/DataDog/omnibus-software/pull/63)
* [IMPROVEMENT] RabbitMQ: Avoiding the extra double lookup for 'rabbitmq_api_url'. See [#2543][] (Thanks [@ParthKolekar][])
* [IMPROVEMENT] RabbitMQ: new health check. See [#2711][]
* [IMPROVEMENT] SSH: Be more specific when logging ssh errors. See [#2708][]
* [IMPROVEMENT] Util: remove LaconicFilter. See [#2605][]
* [IMPROVEMENT] Vsphere: Add optional vm include parameter. See [#2459][]

* [BUGFIX] Core: forwarder drop payloads when no valid endpoints. See [#2833][]
* [BUGFIX] Core: emitter would crash agent with some unicode control characters in payload. See [#2843][]
* [BUGFIX] Core: service discovery fix fallback IP address extraction. See [#2855][]
* [BUGFIX] Core: service discovery dont pass missing `config_store` reference to dockerutil. See [#2858][]
* [BUGFIX] Cloud metadata: Fail on non-2xx responses. See [#2844][]
* [BUGFIX] Disk: timeout on disk usage. See [#2714][] and [#2823][]
* [BUGFIX] Docker_daemon: ECS introspection resilience. See [#2745][] and [#2825][]
* [BUGFIX] Docker_daemon: Custom cgroups are per instance only. See [#2846][]
* [BUGFIX] Docker_daemon: Fix pid retrieval that could affect k8s. See [#2847][]
* [BUGFIX] Dockerutil: cpu subsys might be mistaken for cpuacct. See [#2829][]
* [BUGFIX] Http_check: Bring back include_content option. See [#2631][]
* [BUGFIX] IIS: Fix metrics tagging when multiple sites are specified on instance. See [#2677][]
* [BUGFIX] JMXFetch: Do not scope MBeans queries on `list_not_matching_attributes` action. See [jmxfetch-102](https://github.com/DataDog/jmxfetch/pull/102)
* [BUGFIX] Marathon: Fix a small problem that prevented marathon full path from being properly built. See [#2620][]
* [BUGFIX] Mongo: Repairing of mongodb.can_connect check. See [#2658][] (Thanks [@cryptspirit][])
* [BUGFIX] Mongo: Fixes a mistake in the mongo collections check. See [#2783][]
* [BUGFIX] MySQL: Check for null key_buffer_size before dividing by it. See [#2784][]
* [BUGFIX] Network Checks: Network check instance corrections. See [#2736][] (Thanks [@tschellhorn][])
* [BUGFIX] Packaging [linux]: Kernel 4+ won't error out on status now. See [#2640][]
* [BUGFIX] Packaging [osx]: Support GNU-Friendly sed. See [#2580][] (Thanks [@sha1sum][])
* [BUGFIX] Process: Use configured proc path when getting pagefault stats [#2727][] (Thanks [@rdxiang][])
* [BUGFIX] Redisdb: Avoid exception when slowlog query returns empty `command`. See [#2651][]
* [BUGFIX] Win32_event_log: Fix small regression on `msg_text` selection. See [#2591][]
* [BUGFIX] Win32_event_log: reset filters between iterations. See [#2796][]
* [BUGFIX] Wmi: set provider architecture when necessary. See [#2812][]

* [DEPRECATED] Core: clean debug logs and kill Dogstream-based DdForwarder. See [#2628][]
* [DEPRECATED] Jenkins: Deprecated check. Please use plugin. More information can be found on the Jenkins Integration panel under the Configuration tab (https://app.datadoghq.com/account/settings#integrations/jenkins) See [#2688][]
* [DEPRECATED] Nghttp2: remove python bindings. See [omnibus-software-71](https://github.com/DataDog/omnibus-software/pull/71)


# 5.8.5 / 07-27-2016
**Windows, Linux and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.8.4...5.8.5

### Future rotation of the APT signing key

In preparation for a future rotation of our package signing keys, the `5.8.5` DEB package will, on install, import a new
trusted APT key:

```
pub   4096R/382E94DE 2016-06-29 [expires: 2022-06-28]
uid                  Datadog, Inc <package[@datadoghq][].com>
```

During the package install, the DEB package will output the following:

```
Prepare Datadog Agent keys rotation
  Add the new 'Datadog, Inc <package[@datadoghq][].com>' key to the list of APT trusted keys. ... OK
```

The signing key of the Agent hasn't changed yet but will be switched to this new key in a future release.

See [dd-agent-omnibus-81](https://github.com/DataDog/dd-agent-omnibus/pull/81)

### Changes
* [IMPROVEMENT] Core: Upgrade embedded python to `2.7.12`. See [omnibus-software-63](https://github.com/DataDog/omnibus-software/pull/63)
* [IMPROVEMENT] Elasticsearch: Take into account node `name` for cluster stats. See [#2696][]
* [IMPROVEMENT] RPM package: Add runtime dependency on the `initscripts` package. See [dd-agent-omnibus-82](https://github.com/DataDog/dd-agent-omnibus/pull/82)
* [IMPROVEMENT] RPM package: Don't delete `dd-agent` user and group on uninstall. See [dd-agent-omnibus-84](https://github.com/DataDog/dd-agent-omnibus/pull/84)

* [BUGFIX] Core: Use flag to signal config reload to avoid race conditions. See [#2670][]
* [BUGFIX] Core: Don't use Docker hostname if it's an EC2 one. See [#2661][]
* [BUGFIX] Docker: Fix disk metrics rounding issue. See [#2626][]
* [BUGFIX] Haproxy: Fix `KeyError` when an unknown status is found. See [#2681][]
* [BUGFIX] IIS: Remove warnings on 'Name' property. See [#2633][]
* [BUGFIX] MongoDB: Fix case where optimeDate is not available. See [#2625][]
* [BUGFIX] Service Discovery: Introduce _get_image_ident and fix a bug that needed it. See [#2684][]
* [BUGFIX] Windows Event log: Support unicode messages. See [#2660][]


# 5.8.4 / 07-08-2016
**Windows, Linux and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.8.3...5.8.4

### Changes
* [IMPROVEMENT] Core: Upgrades supervisord to 3.3.0 See [#2667][], [#2669][]

* [BUGFIX] MySQL: Fixes MySQL slave detection. See [#2610][]
* [BUGFIX] MySQL: Fixes MySQL replication service check. See [#2603][]
* [BUGFIX] Core: Fixes a bug that caused the thread pool to leak threads. See [#2666][]


# 5.8.3 / 07-05-2016
**Windows, Linux and Source Install**

### Details
https://github.com/DataDog/dd-agent/compare/5.8.2...5.8.3

### Changes
* [FEATURE] Flare: Adds configcheck output to flare command. See [#2588][]

* [IMPROVEMENT] Docker: Bump docker-py to 1.8.1 for network features support. See [#2556][]

* [BUGFIX] HAProxy: Add `collate_status_tags_per_host` flag See [#2590][]
* [BUGFIX] Core: A bug prevented ipv6 from being used in some circumstances. This fixes that, and defaults to ipv6 and falls back to ipv4. See [#2592][]
* [BUGFIX] Docker: Handles buggy responses from docker api better. See [#2608][]
* [BUGFIX] MongoDB: Only collect ReplicationInfo when it's possible to do so, rather than erroring out. See [#2559][]
* [BUGFIX] Postgres: Adds a hard limit on postgres.table.count metric, as this can be very expensive. See [#2575][]
* [BUGFIX] PowerDNS Recursor: The configuration file needed to be renamed from `powerdns.conf` to `powerdns_recursor.conf`. See [#2538][]
* [BUGFIX] Service Discovery: Improvements for testing, logging and service variable interpolation. See [#2573][]
* [BUGFIX] Service Discovery: Yse docker hostname rather than default route to query cadvisor and kublet. See [#2609][]
* [BUGFIX] Service Discovery: Use get_identifier instead of buggy image name extraction. See [#2593][]
* [BUGFIX] SQLServer: Send service checks after every run, rather than only at the beginning. See [#2515][]
* [BUGFIX] vSphere: Enhances topology support, skip unknown metrics. See [#2560][]
* [BUGFIX] vSphere: The whole check shouldn't fail just because the check failed on a certain instance. See [#2548][]
* [BUGFIX] Win32: When memory check collection times out, it causes an error in the collector. Instead, it should recover from this. See [#2553][]
* [BUGFIX] WMI: Allows user to set a profider in request data. See [#2565][], [#2369][]


# 5.8.2 / 05-24-2016
**Windows only**

### Details
https://github.com/DataDog/dd-agent/compare/5.8.1...5.8.2

### Changes
* [BUGFIX] Windows: Revert a change introduced in the `5.8.0` release, causing hostnames to change on EC2 hosts when no hostname is defined in `datadog.conf`, leading to potential backwards compatibility issues. See [#2451][], [#2535][]


# 5.8.1 / 05-23-2016
**Windows only**

### Details
https://github.com/DataDog/dd-agent/compare/5.8.0...5.8.1

### Changes
* [BUGFIX] Windows: Fix an issue that was preventing checks from loading properly. See [#2528][]


# 5.8.0 / 05-23-2016
**All platforms**

### Details
https://github.com/DataDog/dd-agent/compare/5.7.4...5.8.0

### New integrations
* Kong
* PowerDNS Recursor
* Spark

### Updated integrations
* ActiveMQ
* Cassandra
* Directory
* Disk
* Docker
* Elasticsearch
* Ganglia
* Graphite
* HAProxy
* HTTP Check
* JMX
* Kubernetes
* MapReduce
* Marathon
* Memcached
* Mesos Master
* MongoDB
* MySQL
* Process
* RabbitMQ
* Riak
* TeamCity
* TokuMX
* Varnish
* vSphere
* Windows
* Windows Service
* WMI
* YARN

### Service Discovery
Starting with the 5.8 release, the Datadog Agent ships with service discovery. This feature works for Docker containers and can run on platforms such as Kubernetes, Docker Swarm, and Amazon ECS.

Service discovery makes it possible to define configuration templates for a given Docker image in a configuration store, and to dynamically apply them to new containers on the fly. The Agent will then use these configuration templates combined with container metadata to enable, disable and reconfigure checks dynamically in response to container start/stop events.

For more details on Datadog Agent's Service Discovery, check out the [wiki page](https://github.com/DataDog/dd-agent/wiki/Service-discovery).

See [#2008][], [#2424][], [#2426][], [#2514][].

### Kong integration
[Kong](https://getkong.org/) is an open-source management layer for APIs.

The checks collects metrics using `/status` endpoint part of Kong RESTful API. It retrieves usage information about the node, with some basic information about the connections being processed by the underlying NGINX process, and the number of entities stored in the datastore collections.
It also submits a service check to reflect the agent's ability to connect to the instance.

See [#2241][].

A big thank you [@shashiranjan84][] !

### Spark integration
The [Spark](https://spark.apache.org/) check runs from the Master Node and retrieves metrics from YARN's ResourceManager.
The collected metrics cover statistics about:
* Spark Jobs
* Spark Stages
* Spark Executors
* Spark Resilient Distributed Datasets (RDD)

See [#2407][].

### PowerDNS Recursor integration
The [PowerDNS Recursor](https://www.powerdns.com/) check retrieves metrics using the `/servers/localhost/statistics` endpoint part of [PowerDNS API](https://doc.powerdns.com/md/httpapi/README/) when the experimental web server is active.
The collected metrics cover the Recursor statistics: (outgoing) queries, answers, cache and cache entries.
A service check reflects the agent's ability to connect to the instance.

For more details about the metrics collected, check out the PowerDNS documentation about [Recursor Statistics](https://doc.powerdns.com/md/recursor/stats/).

See [#2108][], [#2490][].

A big thank you [@AntoCard][], [@janeczku][] !

### MapReduce & YARN updates
Hadoop MapReduce and YARN integrations have been updated to reduce and consolidate the metrics' tags.
In particular:
* `cluster_name` tag replaces `cluster_id`
* `app_name` tag replaces `app_id`

MapReduce metrics have received additional improvements and cleanups:
* Metric type `rate` replaces `gauge` when applicable
* The following metrics have been removed:
  * `mapreduce.job.map.task.progress`
  * `mapreduce.job.reduce.task.progress`

See [#2473][], [#2474][], [#2487][].

### Source install: end of Python 2.6 compatibility support
For source installation, the Datadog Agent uses system's Python. Starting with the 5.8.0 release, the Datadog Agent does not enforce compatibility with Python 2.6 anymore and requires Python 2.7. Tests and code sections used to maintain compability have been removed.

Users running a different version of Python on their system are advised to install a [packaged version of the Datadog Agent](https://app.datadoghq.com/account/settings#agent). If you have any questions, please contact our support team support(at)datadoghq(dot)com.

See [#2377][].

### Changes
* [FEATURE] ActiveMQ: Add monitoring for standby hosts. See [#2023][], [#2430][] (Thanks [@joelvanvelden][])
* [FEATURE] Directory: Add Windows support. See [#2410][], [#2508][]
* [FEATURE] Disk: Add an option to exclude disks based on their mountpoints. See [#2359][], [#2476][] (Thanks [@rhwlo][])
* [FEATURE] Docker: Add optional disk metrics. See [#2405][]
* [FEATURE] Docker: Add the possibility to tag by container ID. See [#2353][], [#2507][]
* [FEATURE] Elasticsearch: Add support for SSL and Elasticsearch Shield. See [#2195][] (Thanks [@pabrahamsson][])
* [FEATURE] Elasticsearch: Collect additional Thread Pool metrics. See [#2321][]
* [FEATURE] HAProxy: Add option to disable SSL validation. See [#2393][].
* [FEATURE] JMX: Add user tags to service checks. See [#96](https://github.com/DataDog/jmxfetch/pull/96)
* [FEATURE] JMX: Allow group name substitutions in attribute/alias parameters. See [#94](https://github.com/DataDog/jmxfetch/pull/94), [#97](https://github.com/DataDog/jmxfetch/pull/97) (Thanks [@alz][])
* [FEATURE] Kong: New check. See [#2241][], [Kong integration](#kong-integration) (Thanks [@shashiranjan84][])
* [FEATURE] Kubernetes: Allow to blacklist labels. See [#2512][]
* [FEATURE] Kubernetes: Tag pods metrics with replica sets. See [#2444][], [#2446][], [#2512][]
* [FEATURE] Memcached: Add "items" and "slabs" statistic metrics as reported by the `stats` command. See [#2491][]
* [FEATURE] PowerDNS Recursor: New check. See [#2108][], [#2490][], [PowerDNS Recursor integration](#powerdns-recursor-integration) (Thanks [@AntoCard][], [@janeczku][])
* [FEATURE] Process: Add pagefault statistics to process metrics. See [#2363][], [#2477][] (Thanks [@ovesh][])
* [FEATURE] RabbitMQ: Tag queue based metrics with the queue name as `queue_family`. See [#2259][], [#2468][] (Thanks [@rhwlo][])
* [FEATURE] Riak: Collect Riak Search metrics. See [#2243][] (Thanks [@gzysk8][])
* [FEATURE] Service Discovery: Define configuration templates for a given Docker image in a configuration store, and to dynamically apply them to new containers on the fly. See [#2008][], [#2424][], [#2426][], [#2514][], [Service Discovery](#service-discovery)
* [FEATURE] Spark: New check. See [#2407][], [#2479][], [Spark integration](#spark-integration)
* [FEATURE] TeamCity: Support basic HTTP authentication. See [#2266][] (Thanks [@mderomph-coolblue][])
* [FEATURE] vSphere: Add the ability to set a custom field from the vSphere PowerCLI to mark the VMs to monitor. See [#2459][]
* [FEATURE] Windows Event Log: Add an optional `event_format` parameter to instruct the check to generate Datadog's event bodies with the specified list of event properties. See [#2441][]
* [FEATURE] Windows: Add opened handles statistics to system metrics. See [#2403][]
* [FEATURE] Windows: Add swap -pagefile- statistics to system metrics. See [#2422][]

* [IMPROVEMENT] Core: Allow `AgentCheckTest` facilities to be used on SDK check modules. See [#2341][]
* [IMPROVEMENT] Core: Gracefully handle responses with HTTP status code 413. See [#2418][]
* [IMPROVEMENT] Core: Update the configuration logic to look for checks in a 3rd-party directory. See [#2273][], [#2467][]
* [IMPROVEMENT] Directory: Speed up the file count in a directory. See [#2245][] (Thanks [@tebriel][])
* [IMPROVEMENT] Gohai: Collect process resources and deprecate the corresponding Python check. See [#24](https://github.com/DataDog/gohai/pull/24), [#2218][]
* [IMPROVEMENT] Gohai: Improve logging. See [#30](https://github.com/DataDog/gohai/pull/30)
* [IMPROVEMENT] Kubernetes: Enable `kubelet` check by default. See [#2512][]
* [IMPROVEMENT] Kubernetes: Improve support for Kubernetes >= `1.2`. See [#2388][], [#2494][], [#2512][]
* [IMPROVEMENT] Kubernetes: Timeout on slow requests. See [#2345][]
* [IMPROVEMENT] MapReduce: Consolidate and reduce the number of tags produced. See [#2474][], [MapReduce & YARN updates](#mapreduce--yarn-updates)
* [IMPROVEMENT] MapReduce: Switch metric types from `gauge` to `rate` when applicable. See [#2487][], [MapReduce & YARN updates](#mapreduce--yarn-updates)
* [IMPROVEMENT] Marathon: Remove versions metric to decrease the check collection runtime. See [#1861][], [#2443][] (Thanks [@Zarkantho][])
* [IMPROVEMENT] MongoDB: Add additional tag on status change to make searching more precise. See [#2502][] (Thanks [@gphat][])
* [IMPROVEMENT] MongoDB: Improve metric tagging. See [#2457][]
* [IMPROVEMENT] MySQL: Improve accuracy for query run time averages. See [#2406][], [#2463][]
* [IMPROVEMENT] YARN: Consolidate and reduce the number of tags produced. See [#2473][], [MapReduce & YARN updates](#mapreduce--yarn-updates)

* [BUGFIX] Core: Fix DogStatsd's service check parsing when a tag key ends with `m`. See [#2373][], [#2472][]
* [BUGFIX] Core: Restart the forwarder when a "pathological" activity is detected. See [#2322][]
* [BUGFIX] Core: Retrieve EC2 instance ID on Windows. See [#2451][]
* [BUGFIX] Docker: Fix container ID extraction for RancherOS. See [#2454][], [#2466][] (Thanks [@ricky26][])
* [BUGFIX] Docker: Fix improper logging causing the check to raise an exception when excluding containers. See [#2464][] (Thanks [@yenif][])
* [BUGFIX] Docker: Ignore mountpoints not accessible by Datadog Agent `dd-agent` user. See [#2427][] (Thanks [@c960657][])
* [BUGFIX] Elasticsearch: Restrict the list of metrics to collect by version. See [#2186][], [#2232][] (Thanks [@bdharrington7][])
* [BUGFIX] HTTP Check: Support `no_proxy` environment variable. See [#2448][]
* [BUGFIX] JMX: Report properly beans with ':' in the name. See [#90](https://github.com/DataDog/jmxfetch/pull/90), [#91](https://github.com/DataDog/jmxfetch/pull/91), [#95](https://github.com/DataDog/jmxfetch/pull/95) (Thanks [@bluestix][])
* [BUGFIX] JMX: Sanitize metric names and tags, i.e. remove illegal characters. See [#89](https://github.com/DataDog/jmxfetch/pull/89)
* [BUGFIX] JMX: Support `javax.management.Attribute` attribute types. See [#92](https://github.com/DataDog/jmxfetch/pull/92) (Thanks [@nwillems][])
* [BUGFIX] JMX: Use `localhost` interface when StatsD is bound to all interfaces. See [#2516][]
* [BUGFIX] Kubernetes: Handle case where no pods are running. See [#2263][], [#2512][]
* [BUGFIX] Mesos Master: Fix key error when a metric is missing. See [#2500][] (Thanks [@gphat][])
* [BUGFIX] MongoDB: Attach the check's events with the integration in Datadog. See [#2456][]
* [BUGFIX] Packaging: Exclude an operating-system-specific `.dll` from the MSI installer that was causing installation and runtime failures on Windows Server 2008. See [#2486][]
* [BUGFIX] TokuMX: Fix `AttributeError` exceptions when collecting metrics from a replica. See [#2390][]
* [BUGFIX] TokuMX: Fix an issue among metrics collection causing rate metric values to be potentially wrong and `ZeroDivisionError` exceptions. See [#2510][]
* [BUGFIX] TokuMX: Support metric values with Int64 type. See [#2390][]
* [BUGFIX] Windows Service: Make Windows service names case-insensitive. See [#2492][]

* [OTHER] Cassandra: Remove deprecated options from the `datadog.conf` configuration file. See [#2447][]
* [OTHER] Core: Remove support of Python 2.6. See [#2377][], [Source install: end of Python 2.6 compatibility support](#source-install-end-of-python-26-compatibility-support)
* [OTHER] Core: Upgrade `boto` dependency from `2.36.0` to `2.39.0`. See [#2402][], [#3399](https://github.com/boto/boto/pull/3399)
* [OTHER] Disk: Remove deprecated options from the `datadog.conf` configuration file. See [#2447][]
* [OTHER] Ganglia: Remove deprecated options from the `datadog.conf` configuration file. See [#2447][]
* [OTHER] Graphite: Remove deprecated options from the `datadog.conf` configuration file. See [#2447][]
* [OTHER] HTTP Check: Remove the deprecated `threshold` and `window` parameters from the configuration file. See [#2400][]
* [OTHER] Memcached: Document usage for listening to a Unix socket. See [#2298][], [#2431][] (Thanks [@kzw][])
* [OTHER] TokuMX: Document usage for connecting to a MongoDB instance with a "full" URI. See [#2390][]
* [OTHER] Varnish: Document `varnish` group requirement. See [#2384][]
* [OTHER] WMI: Document wildcard usage in filters. See [#2368][], [#2469][] (Thanks [@mausch][])


# 5.7.4 / 04-21-2016
**All platforms**

### Details
https://github.com/DataDog/dd-agent/compare/5.7.3...5.7.4

### Changes
* [FEATURE] Core: Add Python architecture to the `info` command. See [#2413][]
* [FEATURE] MongoDB: Collect additional `WiredTiger` storage engine metrics. See [#1825][], [#2423][] (Thanks [@benmccann][])
* [FEATURE] MongoDB: Collect replication set information metrics. See [#2237][], [#2429][] (Thanks [@rhwlo][])

* [IMPROVEMENT] Cassandra: Exclude new `system_schema` keyspace in version 3.x. See [#2339][]
* [IMPROVEMENT] Kafka: Update the default configuration file to support collection of more metrics. See [#2371][], [#2425][]
* [IMPROVEMENT] MongoDB: Collect journaling, locks, `WiredTiger` storage engine metrics by default and deprecate the corresponding options. See [#2423][]
* [IMPROVEMENT] MongoDB: Improve messaging and tags on replication set member state events. See [#2409][], [#2432][] (Thanks [@antifuchs][])
* [IMPROVEMENT] Windows WMI-based checks (`wmi_check`, System check, IIS, Windows Service, Windows Event Log): gracefully time out WMI queries. See [#2185][], [#2228][], [#2278][], [#2366][] and [#2401][].

* [BUGFIX] Agent Metrics: Flush service metadata to avoid memory leaks. See [#2414][]

# 5.7.3 / 03-31-2016
**All platforms**

### Details
https://github.com/DataDog/dd-agent/compare/5.7.2...5.7.3

### Changes
* [IMPROVEMENT] Linux install script: Ignore `apt-get update` failures and use https for apt repo. See [#2378][]
* [IMPROVEMENT] WMI check: Make configuration of the metric types case-insensitive. See [#2392][]

* [BUGFIX] Consul: Enforce that `get_peers_in_cluster` returns a list. See [#2381][]
* [BUGFIX] Core: Fix Japanese tzname encoding issue on Windows. See [#2351][]
* [BUGFIX] Core: On RHEL, make the `stop` init command kill all the Agent processes properly. See [#2349][]
* [BUGFIX] Core: Fix Watchdog timeout duration on the forwarder. See [#2320][]
* [BUGFIX] IIS: Fix `CRITICAL` service check on the `_Total` site (e.g. when no `sites` are specified). See [#2387][]
* [BUGFIX] IIS: Deal with BytesTransfered vs BytesTransferred 2008sp2 typo. See [#2379][]
* [BUGFIX] JMXFetch: Take into account `bind_host`. See [#2372][] and [jmxfetch-85](https://github.com/DataDog/jmxfetch/pull/85)
* [BUGFIX] JMXFetch: Handle IOException gracefully at the instance level. See [jmxfetch-83](https://github.com/DataDog/jmxfetch/pull/83)
* [BUGFIX] Packaging: Fix the version of `requests` shipped with the packaged Linux Agent. See [omnibus-software-45](https://github.com/DataDog/omnibus-software/pull/45)
* [BUGFIX] MySQL: Avoid check failure when InnoDB is not available or disabled. See [#2385][]
* [BUGFIX] SNMP: Fix errors in multiple-instance configurations caused by thread-safety issues with pysnmp `cmd_generator`. See [#2357][]
* [BUGFIX] SQLServer: Fix connection to DB when no username or password are specified. See [#2311][]
* [BUGFIX] vSphere: Fix SSL config options feature by upgrading the packaged version of `pyvmomi`. See [omnibus-software-44](https://github.com/DataDog/omnibus-software/pull/44)
* [BUGFIX] Windows Event Log: Fix check when `tag_event_id:true` [#2397][]

# 5.7.2 / 03-17-2016
**Windows only**

### Details
https://github.com/DataDog/dd-agent/compare/5.7.1...5.7.2

### Changes
* [BUGFIX] WMI: Disable query timeout, cache and re-use connections to avoid memory leaks. See [#2366][]

# 5.7.1 / 03-09-2016
**All platforms**

NB: For Windows, please also refer to the `5.7.0` section. `5.7.0` was not released on Windows but the `5.7.1` Windows installer includes all the changes listed in the `5.7.0` section.

### Details
https://github.com/DataDog/dd-agent/compare/5.7.0...5.7.1

### Changes
* [BUGFIX] Core: Avoid python segfault when the ctypes module is imported on SELinux-enabled environments. See [omnibus-software-43](https://github.com/DataDog/omnibus-software/pull/43)
* [BUGFIX] MySQL: Fix check failure when no tag is provided. See [#2329][]
* [BUGFIX] Packaging: Fix RPM package for Amazon Linux EMR. See [omnibus-ruby-18](https://github.com/DataDog/omnibus-ruby/pull/18)

# 5.7.0 / 03-07-2016
**Linux, Mac OS and Source Install only**

### Details
https://github.com/DataDog/dd-agent/compare/5.6.3...5.7.0

### New integrations

* Ceph
* DNS
* HDFS
* MapReduce
* StatsD
* TCP RTT (`go-metro`)
* YARN

### Updated integrations
* Apache
* AWS
* Cassandra
* Consul
* Directory
* Docker
* Elasticsearch
* Go expvar
* Gunicorn
* HAProxy
* HTTP
* IIS
* Kafka
* Mesos
* MongoDB
* MySQL
* PgBouncer
* Postgres
* Process
* Redis
* SNMP
* SSH
* TeamCity
* Tomcat
* vSphere
* Windows Service
* Windows Event Log
* WMI
* Zookeeper

### Hadoop integrations (HDFS, MapReduce and YARN checks)
The Agent now includes 4 new checks to monitor Hadoop clusters:
* 2 HDFS checks (`hdfs_namenode` and `hdfs_datanode`) that collect metrics respectively from namenodes and datanodes using the JMX-HTTP API
* a MapReduce check that collects metrics on the running Mapreduce jobs from the Application Master's REST API
* a YARN check that collects metrics from YARN's ResourceManager REST API

The existing `hdfs` check is deprecated and will be removed in a future version of the Agent. Its metric scope is entirely covered by the new `hdfs_namenode` check.

### TCP RTT measurement with `go-metro`
**This new feature is in beta**

The Datadog Agent on 64-bit Linux is now bundled with a new component (`go-metro`) that passively calculates TCP RTT metrics between the agent's host and external hosts, and reports them as `system.net.tcp.rtt.avg`, `system.net.tcp.rtt.jitter` and `system.net.tcp.rtt` through StatsD.

`go-metro` follows TCP streams active within a certain period of time and estimates the RTT between any outgoing packet with data, and its corresponding TCP acknowledgement.

`go-metro` runs in its own process. It's disabled by default and can be enabled like a regular check by configuring an `/etc/dd-agent/conf.d/go-metro.yaml` file and restarting the agent.

For more details on `go-metro`, check out the [project's GitHub page](https://github.com/DataDog/go-metro).

### Ceph check
The [Ceph](http://ceph.com/) check retrieves metrics from Ceph's Administration Tool command (`ceph`).

The check collects metrics from `mon_status`, `status`, `df detail`, `osd pool stats` and `osd perf`, and sends a service check reflecting the overall health of the cluster.

See [#2264][]

### MySQL
Multiple community-contributed additions to the MySQL check have been consolidated and merged, including:
* metrics from the `performance_schema` table on MySQL >= 5.6 (thanks to [@ovaistariq][])
* extra metrics on the InnoDB and MyISAM engines, from the Binlog, and from the `SHOW STATUS` query (thanks to [@ovaistariq][])
* several schema-specific metrics, including schema size, schema average query runtime and 95th percentile query execution time (thanks again to [@ovaistariq][])
* metrics on the Handler (thanks to [@polynomial][])
* Galera-specific performance stats (thanks to [@zdannar][])
* Query Cache metrics (thanks to [@leucos][])
* a `mysql.replication.slave_running` service check reflecting the state of the slaves (thanks to [@c960657][])

Most of these additional metrics are not collected by default but can be enabled in the check's YAML file. See the [YAML conf example file](https://github.com/DataDog/dd-agent/blob/5.7.0/conf.d/mysql.yaml.example) for details.

Various bug fixes and improvements have also been implemented:
* the Agent's connections to MySQL are handled properly to prevent stale connections
* the replication status is implemented on both the master and the slaves. On the master this status is determined by the Binlog status and the number of slaves.
* the system metrics of MySQL are retrieved w/o errors on non-linux platforms by using the `psutil` library
* the parsing of the MySQL server version is improved

Huge thanks to all our contributors for all these improvements!

See [#2116][] and [#2242][]

### Potential backward incompatibilities
#### Docker
The dockerized Agent now uses the docker hostname (provided by the `Name` param from `docker info`) as its own hostname when available. This means that for hosts running the dockerized Agent the reported hostname may change to this docker-provided hostname.

For reference, the rules followed by the Agent for its `hostname` resolution are described on this [wiki page](https://github.com/DataDog/dd-agent/wiki/Agent-Hostname).

#### MongoDB
The `collect_tcmalloc_metrics` parameter in the YAML conf is replaced with the `tcmalloc` option under `additional_metrics`.
Please refer to the [example YAML conf file](https://github.com/DataDog/dd-agent/blob/5.7.0/conf.d/mongo.yaml.example) for more info on the usage of the `additional_metrics` option.

#### vSphere
Instead of sending all metrics as `gauge`s, the vSphere integration now checks the types of the metrics as reported by the VMWare module, and sends metrics as `rate`s when applicable.

If you haven't enabled the `all_metrics` option on the check, the only affected metrics are `cpu.usage`, `cpu.usagemhz`, `network.received` and `network.transmitted`.
If the option is enabled, the additional affected metrics are listed [here](https://gist.github.com/olivielpeau/f6b5df2ea7f83e53ef6f). The change will affect the values of these metrics.

#### WMI check
The `wmi_check` now only supports `%` as the wildcard character in the `filters`. The support of `*` as the wildcard character, which was undocumented, has been dropped.

### Changes
* [FEATURE] Ceph: New check collecting metrics from Ceph clusters. [#2264][]
* [FEATURE] Consul: Add SSL support. See [#2034][] (Thanks [@diogokiss][])
* [FEATURE] DNS: New check that sends a service check reflecting the status of a hostname's resolution on a nameserver. See [#2249][] and [#2289][]
* [FEATURE] Elasticsearch: Report additional metrics related to `fs`, `indices.segments` and `indices.translog`. See [#2143][] (Thanks [@bdharrington7][])
* [FEATURE] HDFS: 2 new checks (see description above). See [#2235][], [#2260][], [#2274][] and [#2287][]
* [FEATURE] Go-metro: New component that measures TCP RTT (in beta, see description above). See [#2208][]
* [FEATURE] Linux: Add memory metrics (slab, page tables and cached swap). See [#2100][] (Thanks [@gphat][])
* [FEATURE] Linux: New `linux_proc_extras` check collecting system-wide metrics on interrupts, context switches and processes. See [#2202][] (Thanks [@gphat][])
* [FEATURE] MapReduce: New check (see description above). See [#2236][]
* [FEATURE] MongoDB: Collect optional additional metrics, grouped by topic. These can be enabled with the new `additional_metrics` option in the check's YAML conf. Also, the underlying `pymongo` library has been upgraded from `2.8` to `3.2`. See [#2161][], [#2166][], [#2140][] and [#2160][] (Thanks [@scottbessler][] and [@benmccann][])
* [FEATURE] MySQL: Add tag parameter for custom MySQL queries. See [#2229][]
* [FEATURE] MySQL: Enhance the catalog of metrics reported, and add a service check on the replication state. See [#2116][], [#2242][] and [#2288][] (Thanks [@ovaistariq][], [@zdannar][], [@polynomial][], [@leucos][], [@Zenexer][], [@c960657][], [@nfo][], [@patricknelson][] and [@scottgeary][])
* [FEATURE] Postgres: Measure user functions. See [#2164][]
* [FEATURE] Process: Allow configuring the path to procfs (useful when the agent is run in a container), with a newer version of `psutil`. See [#2163][] and [#2134][] (Thanks [@sethp-jive][])
* [FEATURE] Redis: Optionally report metrics from `INFO COMMANDSTATS` as `calls`, `usec` and `usec_per_call` (prefixed with `redis.command.`). See [#2109][]
* [FEATURE] SNMP: Add support for forced SNMP data types to help w/ buggy devices. See [#2165][] (Thanks [@chrissnell][])
* [FEATURE] SSH: Add Windows support. See [#2072][]
* [FEATURE] StatsD: New check collecting metrics and service checks using StatsD's admin interface. See [#1978][] and [#2162][] (Thanks [@gphat][])
* [FEATURE] vSphere: Add SSL config options for certs. See [#2180][]
* [FEATURE] YARN: New check (see description above). See [#2147][] and [#2207][]
* [FEATURE] Zookeeper: Gather stats from `mntr` command and report `zookeeper.instances.<mode>` metrics as 0/1 gauge. See [#2156][] (Thanks [@jpittis][])

* [IMPROVEMENT] Apache: Allow disabling ssl validation. See [#2169][]
* [IMPROVEMENT] AWS: Incorporate security-groups into tags collected from EC2. See [#1951][]
* [IMPROVEMENT] Cassandra: Add YAML conf for Cassandra version > 2.2. See [#2142][] and [#2271][]
* [IMPROVEMENT] Directory: Show check on Windows. See [#2184][] (Thanks [@xkrt][])
* [IMPROVEMENT] Docker: Pass tags to events as well. See [#2182][]
* [IMPROVEMENT] Docker: Use the docker hostname as the agent's `hostname` when available. See [#2145][]
* [IMPROVEMENT] Elasticsearch: Apply custom tags to service checks too. See [#2148][]
* [IMPROVEMENT] Go expvar: Add configuration option for custom metric namespace. See [#2022][] (Thanks [@theckman][])
* [IMPROVEMENT] Go expvar: Add counter support. See [#2133][] (Thanks [@gphat][])
* [IMPROVEMENT] Gohai: Count number of logical processors. See [gohai-22](https://github.com/DataDog/gohai/pull/22)
* [IMPROVEMENT] HAProxy: Add option to count statuses by service. See [#2304][] and [#2314][]
* [IMPROVEMENT] HTTP: Add a `days_critical` option to the SSL certificate expiration feature. See [#2087][]
* [IMPROVEMENT] HTTP: Support unicode in content-matching. See [#2092][]
* [IMPROVEMENT] Kafka: Compute instant rates and capture more metrics in example configuration. See [#2079][] (Thanks [@dougbarth][])
* [IMPROVEMENT] Linux install script: Add custom provided hostname to `datadog.conf`. See [#2225][] (Thanks [@lowl4tency][])
* [IMPROVEMENT] Mesos: Improve checks' performance by preventing `requests` from using chardet. See [#2192][] (Thanks [@GregBowyer][])
* [IMPROVEMENT] MongoDB: Tag mongo instances by replset state. See [#2244][] (Thanks [@rhwlo][])
* [IMPROVEMENT] SNMP: Improve performance by running instances of the check in parallel. See [#2152][]
* [IMPROVEMENT] SNMP: Make MIB constraint enforcement optional and improve resilience. See [#2268][]
* [IMPROVEMENT] TeamCity: Allow disabling ssl validation. See [#2091][] (Thanks [@jslatts][])
* [IMPROVEMENT] Unix: Revamp source install script. See [#2198][] and [#2199][]
* [IMPROVEMENT] vSphere: Add `network.received` and `network.transmitted` to the basic metrics collected. See [#1824][]
* [IMPROVEMENT] vSphere: Check metric type to determine how to report (`rate` or `gauge`). See [#2115][]
* [IMPROVEMENT] Windows: Add uptime metric. See [#2135][], [#2292][] and [#2299][]
* [IMPROVEMENT] Windows WMI-based checks (`wmi_check`, System check, IIS, Windows Service, Windows Event Log): gracefully time out WMI queries. See [#2185][], [#2228][] and [#2278][]
* [IMPROVEMENT] Windows IIS, Service and Event Log checks: use the new WMI wrapper with increased performance. See [#2136][]
* [IMPROVEMENT] Windows packaging: Tighten permissions on `datadog.conf`. See [#2210][]

* [BUGFIX] AWS: Use proxy settings for EC2 tag collection. See [#2201][]
* [BUGFIX] AWS: During EC2 tags collection, log a warning when the instance is not associated with an IAM role. See [#2285][]
* [BUGFIX] Core: Do not log API keys. See [#2146][]
* [BUGFIX] Core: Fix cases of low/no disk space causing the Agent to crash when calling subprocesses. See [#2223][]
* [BUGFIX] Core: Make Dogstatsd recover gracefully from serialization errors. See [#2176][]
* [BUGFIX] Core: Set agent pid file and path from constants. See [#2128][] (Thanks [@urosgruber][])
* [BUGFIX] Core: Log check starts with info level on first run only. See [#2772][]
* [BUGFIX] Development: Fix test of platform in `etcd` CI setup script. See [#2205][] (Thanks [@ojongerius][])
* [BUGFIX] Docker: Avoid event collection failure if an event has no ID param. See [#2308][]
* [BUGFIX] Docker: Catch exception when getting k8s labels fails. See [#2200][]
* [BUGFIX] Docker: Don't warn if process finishes before measuring. See [#2114][] (Thanks [@oeuftete][])
* [BUGFIX] Docker: Remove misleading warning on excluded containers. See [#2179][] (Thanks [@EdRow][])
* [BUGFIX] Documentation: Update link to dogstatsd guide in `datadog.conf`. See [#2181][]
* [BUGFIX] Elasticsearch: Optionally collect pending task stats. See [#2250][]
* [BUGFIX] Flare: Use ssl and proxy settings from `datadog.conf`. See [#2234][] (Thanks [@tebriel][])
* [BUGFIX] Flare: Mention path to tar file in Windows UI. See [#2084][]
* [BUGFIX] FreeBSD: Use correct log file for syslog. See [#2171][]
* [BUGFIX] Go expvar: Add timeout for requests to get go expvar metrics. See [#2183][] (Thanks [@gphat][])
* [BUGFIX] Gohai: Log unexpected OSError exceptions instead of re-raising them. See [#2309][]
* [BUGFIX] Gunicorn: Mention in YAML conf that the `setproctitle` module is required. See [#2215][]
* [BUGFIX] HTTP: Add an option to disable warnings when ssl validation is disabled. See [#2193][]
* [BUGFIX] HTTP: Improve log message when http code is incorrect. See [#2203][]
* [BUGFIX] HTTP: Rename `ssl_expire` to `check_certificate_expiration` in YAML comment. See [#2086][] (Thanks [@MiguelMoll][])
* [BUGFIX] HTTP: Use proxy settings from `datadog.conf`. See [#2112][]
* [BUGFIX] Kubernetes: Remove unused function. See [#2157][]
* [BUGFIX] OpenStack: Improve docs in YAML conf. See [#2094][]
* [BUGFIX] OpenStack: Remove recommendation for omitting trailing slashes in YAML conf. See [#2081][]
* [BUGFIX] Mac OS X: Fix `gohai` call by passing correct PATH to supervisor. See [#2206][]
* [BUGFIX] Mesos slave: Allow configuring mesos master port. See [#2189][]
* [BUGFIX] MySQL: Fix buggy tagging in service_checks on instances configured w/ unix socket. See [#2216][]
* [BUGFIX] PgBouncer: Avoid raising error when there are no results for a query. See [#2280][] (Thanks [@hjkatz][])
* [BUGFIX] SNMP: Fix bug when the requested oid is prefixed by another requested oid. See [#2246][] (Thanks [@xkrt][])
* [BUGFIX] Tomcat: Fix bad attribute in YAML conf file. See [#2153][]
* [BUGFIX] Unix: Fix URL of get-pip script in source install script. See [#2220][] (Thanks [@mooney6023][])
* [BUGFIX] Windows: Fix cases of collector getting wrongfully restarted by watchdog after one correct watchdog restart. See [#2175][]
* [BUGFIX] WMI check: Remove unnecessary warnings on `Name` property. See [#2291][]
* [BUGFIX] WMI check: Always add the `tag_by` parameter to the collected properties. See [#2296][]


# 5.6.3 / 12-10-2015

### Details
https://github.com/DataDog/dd-agent/compare/5.6.2...5.6.3

### Changes
* [FEATURE] Consul: More accurate nodes_* and services_* gauges (NB: `consul.check` service checks are now tagged by `consul_service_id` rather than `service-id`) See [#2130][] (Thanks [@mtougeron][])
* [FEATURE] Docker: Improve container name, image name and image tag extraction. See [#2071][]

* [BUGFIX] Core: Catch and log exceptions from the resources checks. See [#2029][]
* [BUGFIX] Core: Fix host tags sending when `create_dd_check_tags` is enabled. See [#2088][]
* [BUGFIX] Docker: Add one more cgroup location. See [#2139][] (Thanks [@bakins][])
* [BUGFIX] Flare: Remove proxy credentials from collected datadog.conf. See [#1942][]
* [BUGFIX] Marathon: Fix _disk_ typo in metric name. See [#2126][] (Thanks [@pidah][])
* [BUGFIX] OS X: Fix memory metrics. See [#2097][]
* [BUGFIX] Postgres: Fix metrics not reporting with multiple relations. See [#2111][]
* [BUGFIX] Windows: Bundle default CA certs of `requests`. See [#2098][]

# 5.6.2 / 11-16-2015
**Linux, Mac OS and Source Install only**

### Details
https://github.com/DataDog/dd-agent/compare/5.6.1...5.6.2

### Changes
* [FEATURE] Docker/Kubernetes: Collect Kubernetes labels as tags. See [#2075][], [#2082][]
* [FEATURE] HTTPCheck: Option to support -RSA, RC4, MD5- weak SSL/TLS ciphers. See [#1975][], [#2048][]

* [BUGFIX] Core: Improve detection of agent process from PID to avoid false positives. See [#2005][]

# 5.6.1 / 11-09-2015

### Details
https://github.com/DataDog/dd-agent/compare/5.6.0...5.6.1

### Changes
* [BUGFIX] Consul: Add the main tags to service checks. See [#2015][] (Thanks [@mtougeron][])
* [BUGFIX] Docker: Remove spurious proc root container warnings. See [#2055][] (Thanks [@oeuftete][])
* [BUGFIX] Flare: Restore missing JMXFetch information. See [#2062][]
* [BUGFIX] OpenStack: Fix false-critical on the network service check. See [#2063][]
* [BUGFIX] Windows: Restore missing JMXFetch service logs. See [#1852][], [#2065][]

* [OTHER] Upgrade `pymongo` dependency from `2.6.3` to `2.8` on Windows Datadog Agent 32-bit MSI Installer.
* [OTHER] Allow `supervisor.conf` to select Supervisor user. See [#2064][]

# 5.6.0 / 11-05-2015
**Linux, Mac OS and Source Install only**

### Details
https://github.com/DataDog/dd-agent/compare/5.5.2...5.6.0

### New integration(s)
* Kubernetes
* OpenStack

### Updated integrations
* ActiveMQ
* Cassandra
* Couchbase
* Docker
* Dogstream
* HAProxy
* HTTPCheck
* JMXFetch
* Memcached
* MongoDB
* Network
* Nginx
* Process
* Riak
* SNMP
* SQL Server
* Unix
* Windows
* Windows Event Viewer
* WMI

### Kubernetes check
The [Kubernetes](http://kubernetes.io/) check retrieves metrics from cAdvisor running under Kubelet.

See [#2031][]

### OpenStack check
The [OpenStack](https://www.openstack.org/) check is intended to run besides individual hypervisors. It can be scoped to any set of projects living on that host via instance-level config.

At the hypervisor-level it collects:

- [Hypervisor Uptime and Statistics](http://developer.openstack.org/api-ref-compute-v2.1.html#os-hypervisors-v2.1)

At the project-level it collects:
- [Diagnostics for guest servers within that project](http://developer.openstack.org/api-ref-compute-v2.1.html#diagnostics-v2.1)
- [Absolute limits for the project](http://developer.openstack.org/api-ref-compute-v2.1.html#limits-v2.1)

Additionally it sends service checks to register the UP/DOWN state of networks discovered by the agent,
the locally running hypervisor, and the outward-facing (`public || internal`) API services of Nova, Neutron and Keystone

#### Authentication
While the check will run without issues as an `admin` user, it is recommended to configure a read-only `datadog` user and configure the check with the corresponding user/password. Instructions on setting up the datadog user + role , as well as the changes required to the `policy.json` file can be found [here](https://gist.github.com/talwai/b8698e061795cec9f263#configure-a-datadog-user)

#### A note on compatibility
Authentication is performed via the password method, and requires Identity API v3
Nova API v2 and v2.1 are supported, with minor additional configuration necessary for v2.


A big thank you [@mtougeron][] !

See [#1864][]

### New WMI module wrapper

Datadog Agent 5.6.0 ships a new built-in lightweight Python WMI module wrapper, built on top of `pywin32` and `win32com` extensions.

**Specifications**
* Based on top of the `pywin32` and `win32com` third party extensions only
* Compatible with `Raw`* and `Formatted` Performance Data classes
    * Dynamically resolve properties' counter types
    * Hold the previous/current `Raw` samples to compute/format new values*
* Fast and lightweight
    * Avoid queries overhead
    * Cache connections and qualifiers
    * Use `wbemFlagForwardOnly` flag to improve enumeration/memory performance

*\* `Raw` data formatting relies on the avaibility of the corresponding calculator.
Please refer to `checks.lib.wmi.counter_type` for more information*

**Usage**<br/>
The new WMI module wrapper is used among the following checks to improve speed performances:
* System
* WMI


Other checks relying on WMI collection will follow in future versions of Datadog Agent.


See [#2011][]<br/>
Original discussion thread: [#1952][]<br/>
Credits to [@TheCloudlessSky][] (https://github.com/TheCloudlessSky)


### [Warning] JMXFetch false-positive bean match & potential backward incompatibilities issues
JMXFetch was illegitimately matching some MBeans attributes when the associated MBean had one of its parameter defined in an instance configuration.

The issue is addressed. As a result, please note that metrics related to false positive bean matches are not reported anymore.


*Potential affected checks*: ActiveMQ, Cassandra, JMX, Solr, Tomcat.



For more information, please get in touch with support(at)datadoghq(dot)com

See [#81](https://github.com/DataDog/jmxfetch/issues/81)

### Changes
* [FEATURE] Cassandra: Support Cassandra > 2.2 metric name structure (CASSANDRA-4009). See [#79](https://github.com/DataDog/jmxfetch/issues/79), [#2035][]
* [FEATURE] Core: Add service check count to the output of Dogstatsd 'info' section. See [#1799][]
* [FEATURE] Docker: Add container names as tags for events. See [#2026][]
* [FEATURE] HAProxy: Collect the number of available/unavailable backends. See [#1915][] (Thanks [@a20012251][])
* [FEATURE] JMXFetch: Option to add custom JARs to the classpath. See [#1996][]
* [FEATURE] JMXFetch: Support `float` and `java.lang.Float` attribute types as simple JMX attributes. See [#76](https://github.com/DataDog/jmxfetch/issues/76)
* [FEATURE] JMXFetch: Support Cassandra > 2.2 metric name structure (CASSANDRA-4009). See [#79](https://github.com/DataDog/jmxfetch/issues/79)
* [FEATURE] JMXFetch: Support custom JMX Service URL to connect to, on a per-instance basis. See [#80](https://github.com/DataDog/jmxfetch/issues/80)
* [FEATURE] Kubernetes: New check. See [#1919][], [#2031][], [#2038][], [#2039][]
* [FEATURE] Memcached: Collect `listen_disabled_num` timeout counter. See [#1995][] (Thanks [@alaz][])
* [FEATURE] MongoDB: Collect TCMalloc memory allocator metrics. See [#1979][] (Thanks @[@benmccann][])
* [FEATURE] MongoDB: Report `dbStats` metrics for all databases. See [#1855][], [#1961][] (Thanks [@asiebert][])
* [FEATURE] Network: Add UDP metrics from `/proc/net/snmp` in addition to the existing TCP metrics. See [#1974][], [#1986][] (Thanks [@gphat][])
* [FEATURE] OpenStack: New check. See [#1864][], [#2040][]
* [FEATURE] Riak: Add custom tags to service checks' tags. See [#1482][], [#1527][], [#1987][]
* [FEATURE] SNMP: Option to set the OID batch size. See [#1990][]
* [FEATURE] Unix: Collect `/proc/meminfo` `MemAvailable` metric when available. See [#1826][], [#1993][] (Thanks [@jraede][])
* [FEATURE] Windows Event Viewer: Option to tag events by `event_id`. See [#2009][]

* [IMPROVEMENT] Core: Deprecate 'use_dd' flag. See [#1856][], [#1860][] (Thanks [@ssbarnea][])
* [IMPROVEMENT] Core: Fix hanging `subprocess.Popen` calls caused by buffer limits. See [#1892][]
* [IMPROVEMENT] Core: Remove the uses of list comprehensions as looping constructs. See [#1939][] (Thanks [@jamesandariese][])
* [IMPROVEMENT] Core: Run Supervisor as `dd-agent` user. See [#1348][], [#1620][], [#1895][]
* [IMPROVEMENT] Core: Use user-defined NTP settings in 'info' command's status page. See [#1985][]
* [IMPROVEMENT] Dogstream: Add DEBUG logging to event collection. See [#1910][]
* [IMPROVEMENT] JMXFetch: Assign generic alias if not defined. See [#78](https://github.com/DataDog/jmxfetch/issues/78)
* [IMPROVEMENT] Network: Use `ss` instead of `netstat` on Linux systems. See [#1156][], [#1859][] (Thanks [@tliakos][])
* [IMPROVEMENT] Nginx: Add logging on check exceptions. See [#1813][], [#1914][] (Thanks [@clokep][])
* [IMPROVEMENT] Process: Improve sampling of `system.processes.cpu.pct` metric. See [#1660][], [#1928][]
* [IMPROVEMENT] Unix: Filter SunOS `memory_cap` `kstats` by module. See [#1959][] (Thanks [@pfmooney][])
* [IMPROVEMENT] Windows: New WMI module wrapper to improve speed performances. See [#1952][], [#2011][] (Thanks [@TheCloudlessSky][])
* [IMPROVEMENT] Windows: Switch to the built-in WMI core to improve system metric collection performances. See [#1952][], [#2011][] (Thanks [@TheCloudlessSky][])
* [IMPROVEMENT] WMI: Switch to the built-in WMI core to improve the check performances. See [#1952][], [#2011][] (Thanks [@TheCloudlessSky][])

* [BUGFIX] ActiveMQ: Limit metric collection to the queues specified in the configuration file. See [#1948][] (Thanks [@joelvanvelden][])
* [BUGFIX] Core: Normalize exit code of fallback `status` command. See [#1976][], [#1988][] (Thanks [@wyaeld][])
* [BUGFIX] Couchbase: Only send selected bucket-level metrics. See [#1936][]
* [BUGFIX] Docker: Do not run on initialization failures. See [#1984][]
* [BUGFIX] Docker: Improve container name extraction to avoid duplicates. See [#1965][]
* [BUGFIX] Flare: Obfuscate passwords encoded in URIs. See [#2010][]
* [BUGFIX] HTTPCheck: Fix SSL Certificate check when specifying a port in the URL. See [#1923][], [#1944][] (Thanks [@dmulter][])
* [BUGFIX] JMXFetch: Fix bean name matching logic: `OR`→`AND`. See [#81](https://github.com/DataDog/jmxfetch/issues/81)
* [BUGFIX] Process: Avoid refreshing `AccessDenied` PIDs cache at every run. See [#1928][]
* [BUGFIX] SQL Server: Close database connections so SQL Server Agent can stop. See [#1997][]
* [BUGFIX] Windows: Limit Datadog Agent Manager to a single instance. See [#1924][], [#1933][]


# 5.5.2 / 10-26-2015
### Details
https://github.com/DataDog/dd-agent/compare/5.5.1...5.5.2

### [WARNING] Datadog Agent not reporting metrics after Daylight Saving Time (DST) ends
This release fixes a bug on servers that **are configured in local time instead of UTC Time**. If your server's clock is configured to use Daylight Saving Time (DST), the Datadog Agent might stop sending metrics for up to one hour when the Daylight Saving Time ends or until it is restarted after the Daylight Saving Time ends.

We highly recommend to upgrade to this version if your server is configured in local time.

### Changes
* [BUGFIX] Consul: Send the health state service checks of all nodes. See [#1900][] (Thanks [@jgmchan][])
* [BUGFIX] Core: Use `utcnow` instead of `now` to avoid the forwarder to run into a locked state. See [#2000][]
* [BUGFIX] Fix `pycurl` dependency issue with Windows Datadog Agent 64-bit MSI Installer.


# 5.5.1 / 09-23-2015
### Details
https://github.com/DataDog/dd-agent/compare/5.5.0...5.5.1

### Changes
* [BUGFIX] Core: Fix `dd-agent` command-line interface on Linux. See [#49](https://github.com/DataDog/dd-agent-omnibus/pull/51), [#51](https://github.com/DataDog/dd-agent-omnibus/pull/49)
* [BUGFIX] Docker: Fix Amazon EC2 Container Service (ECS) tags collection. See [#1932][]
* [BUGFIX] Docker: Improve parsing of the `cpuacct` field and of the container ID. See [#1940][] (Thanks [@joshk0][])
* [BUGFIX] HTTP Check: Fix SSL certificate check when specifying a non-default port in the URL. See [#1923][] (Thanks [@dmulter][])
* [BUGFIX] Nginx: Fix 'application/json' content_type support. See [#1943][]

* [OTHER] Windows: Ship latest version of Gohai with Windows MSI Installer.


# 5.5.0 / 09-17-2015
### Details
https://github.com/DataDog/dd-agent/compare/5.4.7...5.5.0

### New integration(s)
* Consul

### Updated integrations
* Agent Metrics
* Amazon EC2
* Btrfs
* Couchbase
* CouchDB
* Disk
* Docker
* Elasticsearch
* etcd
* Google Compute Engine
* HTTP Check
* JMXFetch
* Mesos
* MongoDB
* MySQL
* Network
* Nginx
* PgBouncer
* PostgreSQL
* Process
* RabbitMQ
* Redis
* Supervisor
* System
* Unix
* Windows Event Viewer
* WMI

### Consul check
New [Consul](https://www.consul.io/) check.

Supported metrics:

* Number of Consul Agents in the Cluster
    `consul.peers`: tagged by `consul_datacenter` and mode (`leader` | `follower`)
* Consul Catalog Nodes Up by Service
    `consul.catalog.nodes_up`: tagged by `consul_datacenter` and `consul_service_id`
* Consul Catalog Services Up by Node
    `consul.catalog.services_up`: tagged by `consul_datacenter` and `consul_node_id`

Supported events:

* `consul.new_leader` events when a leader change is detected.

See [#1628][]

### New Docker check
Datadog agent 5.5.0 introduces a new Docker check: 'docker_daemon'.

In terms of features, it adds:

* Support for TLS connections to the daemon
* New metrics:
 * Network metrics
 * Memory limits
 * Container size (rootfs)
 * Image size
* Support for labels (convert them into tags). Off by default, uses a list of labels that should be converted.
* Support for ECS tags: task name and task version

Backward incompatible changes:

* `docker.disk.size metric` is renamed to `docker.container.size_rw`
* Old optional metrics: https://github.com/DataDog/dd-agent/blob/5.4.x/checks.d/docker.py#L29-L38 Are not collected anymore
* Old tags are not supported anymore (e.g. `name` instead of container_name)

As a consequence, the previous check 'Docker' is now deprecated and will not receive further support.

See [#1908][]

### Windows 64bit - Datadog Agent
The Datadog Agent is now available in a 64bit version on Windows.
For more information, please visit [our Integrations/Agent page](https://app.datadoghq.com/account/settings#agent/windows).

### Flare on Windows
Datadog Agent `flare` feature makes easy to ship a tarball with logs and configurations to ease agent troubleshooting. Previously exclusive to Linux, it's now available on Windows.
For more information, please visit [our wiki page](https://github.com/DataDog/dd-agent/wiki/Send-logs-to-support-using-flare).

### [Warning] JMX `host` tag issues & potential backward incompatibilities issues with service check monitors
JMX related checks -c.f. list below- were illegitimately submitting service checks tagged with the `host` value defined in the YAML configuration file. As it was overriding the agent hostname, with a value often equals to `localhost`, it was difficult to define and scope monitors based on these service checks.

The issue is addressed. JMX service checks have a new `jmx_server` tag which contains the YAML configuration host value so it does not replace the actual agent hostname in the `host` tag anymore.

**Warning**: these changes affect your JMX-service-checks related existing monitors scoped with the `host` tag. For more information, please get in touch with support[@datadoghq][].com

*JMX related checks*: ActiveMQ, Cassandra, JMX, Solr, Tomcat.


See [#66](https://github.com/DataDog/jmxfetch/pull/66)

### Deprecation notice

#### `datadog.conf` disk options
[Disk options](https://github.com/DataDog/dd-agent/blob/master/datadog.conf.example#L137-L146) in `datadog.conf` file are being deprecated to promote the new Disk check introduced in the 5.4.0 release. It will be removed in a future version of the Datadog Agent.
Please consider [conf.d/disk.yaml](https://github.com/DataDog/dd-agent/blob/master/conf.d/disk.yaml.default) instead to configure it.

See [#1758][]

#### Generic Mesosphere check
The previous generic Mesosphere check is deprecated, in favor of the Mesosphere master and slave specific checks introduced in the 5.4.0 release. It will be removed in a future version of the Datadog Agent.

See [#1535][]

#### Previous Docker check
The previous Docker check is deprecated, in favor of the new one introduced in the 5.5.0 release. It will be removed in a future version of the Datadog Agent.

See [#1908][]

### Changes
* [FEATURE] Consul: New check reporting cluster, service and node wide metrics and events for leader election. See [#1628][]
* [FEATURE] CouchDB: Allow blacklisting of specific databases. See [#1760][]
* [FEATURE] Docker: New Docker check. See [#1908][]
* [FEATURE] Elasticsearch: Collect common JVM metrics. See [#1865][]
* [FEATURE] Elasticsearch: Collect primary shard statistic metrics. See [#1875][]
* [FEATURE] etcd: SSL support. See [#1745][] (Thanks [@KnownSubset][])
* [FEATURE] Flare: Add JMXFetch-specific information. See [#1726][]
* [FEATURE] Flare: Log permissions on collected files. See [#1767][]
* [FEATURE] Flare: Windows support. See [#1773][]
* [FEATURE] HTTP Check: Add SSL certificate configuration and validation options. See [#1720][]
* [FEATURE] JMXFetch: Memory saving by limiting MBeans queries to certain scopes. See [#63](https://github.com/DataDog/jmxfetch/issues/63)
* [FEATURE] JMXFetch: Wildcard support on domains and bean names. See [#57](https://github.com/DataDog/jmxfetch/issues/57)
* [FEATURE] MongoDB: Collect active client connections metrics. Enhance `connections`, `dbStats`, `mem` and `rpl` metric coverage. See [#1798][]
* [FEATURE] MongoDB: Make timeout configurable and increase the default. See [#1823][] (Thanks [@benmccann][])
* [FEATURE] MySQL: Custom query metrics. See [#1793][] (Thanks [@obi11235][])
* [FEATURE] Nginx: Option to disable SSL validation. See [#1626][] [#1782][]
* [FEATURE] PostgreSQL: SSL support. See [#1696][] (Thanks [@bdotdub][])
* [FEATURE] PostgreSQL: Support for relation schemas. See [#1771][]
* [FEATURE] RabbitMQ: Collect the number of RabbitMQ partitions per node. See [#1715][] (Thanks [@ulich][])
* [FEATURE] Supervisor: Option to select processes to monitor by regex name match. See [#1747][] (Thanks [@ckrough][])
* [FEATURE] System: Collect [`%guest`](http://man.he.net/man1/mpstat) CPU time. See [#1845][]

* [IMPROVEMENT] Agent Metrics: Move stats log's level to `DEBUG`. See [#1885][]
* [IMPROVEMENT] Core: Log collector runs's exceptions. See [#1888][]
* [IMPROVEMENT] CouchDB: Fail gracefully when one or more individual databases are not readable by the configured user. See [#1760][]
* [IMPROVEMENT] Docker: Add an `image_repository` tag to the docker check. See [#1691][]
* [IMPROVEMENT] Windows Event Viewer: Better configuration YAML example file. See [#1734][]
* [IMPROVEMENT] Windows: Add Datadog agent version to MSI description. See [#1878][]

* [BUGFIX] Agent Metrics: Fix the configuration YAML example file rights. See [#1725][]
* [BUGFIX] Amazon EC2: Update metadata endpoint list to avoid redirections. See [#1750][] (Thanks [@dspangen][])
* [BUGFIX] Btrfs: Track usage based on used bytes instead of free bytes. See [#1839][] (Thanks [@pbitty][])
* [BUGFIX] Couchbase: Send service check tags on OK status. See [#1722][] [#1776][]
* [BUGFIX] Docker: Fallback when Docker Remote API `/events` returns an invalid JSON. See [#1757][]
* [BUGFIX] Docker: Kubernetes support -new cgroups path-. See [#1759][]
* [BUGFIX] Docker: Strip newlines from API responses to avoid parsing issues. See [#1727][]
* [BUGFIX] Google Compute Engine: Update hostname to be unique. See [#1736][], [#1737][]
* [BUGFIX] HTTP Check: Handle `requests` timeout exceptions to send the appropriate service check. See [#1761][]
* [BUGFIX] JMXFetch: Do not override service checks's `host` tag with JMX host. See [#66](https://github.com/DataDog/jmxfetch/issues/66)
* [BUGFIX] JMXFetch: Do not send service check warnings on metric limit violation. See [#73](https://github.com/DataDog/jmxfetch/issues/73)
* [BUGFIX] JMXFetch: Fix collector logs being duplicated to JMXFetch ones. See [#1852][]
* [BUGFIX] JMXFetch: Fix indentation in the configuration YAML example file. See [#1774][]
* [BUGFIX] Mesos: Do not fail if no cluster name is found. See [#1843][]
* [BUGFIX] Mesos: Fix `AttributeError` on non leader nodes. See [#1844][]
* [BUGFIX] MongoDB: Clean password from `state changed` events. See [#1789][]
* [BUGFIX] MySQL: Close connection when complete. See [#1777][] (Thanks [@nambrosch][])
* [BUGFIX] Network: Normalize `instance_name` tags to avoid mismatch and backward incompatiblity. See [#1811][]
* [BUGFIX] PgBouncer: Collected metrics were wrong. See [#1902][].
* [BUGFIX] Process: Restore Windows support. See [#1595][], [#1883][]
* [BUGFIX] RabbitMQ: Fix `ValueError` error when an absolute queue name is used. See [#1820][]
* [BUGFIX] Redis: Handle the exception when CONFIG command is disabled. See [#1755][]
* [BUGFIX] Redis: Switch `redis.stats.keyspace_*` metrics from gauge to rate type. See [#1891][]
* [BUGFIX] Unix: Fix incorrect conversion of `system.io.bytes_per_s` metric. See [#1718][], [#1912][]
* [BUGFIX] Windows Event Viewer: Fix indentation in the configuration YAML example file. See [#1725][]
* [BUGFIX] Windows: Fix developer mode configuration on Windows. See [#1717][]
* [BUGFIX] WMI: Fix errors when a property does not exist or has a non digit value. See [#1800][], [#1846][], [#1889][]

* [OTHER] Mesos: Deprecate previous generic check in favor of the Mesosphere master and slave specific checks introduced in the 5.4.0 release. See [#1822][]
* [OTHER] Mac OS X: Fix upgrade of the agent with DMG package. See [#48](https://github.com/DataDog/dd-agent-omnibus/pull/48)


# 5.4.7 / 09-11-2015
**Windows Only**
### Details
https://github.com/DataDog/dd-agent/compare/5.4.6...5.4.7

### Changes
* [BUGFIX] Fix `adodbapi` dependency issue with Windows MSI Installer. See [#1907][]

# 5.4.6 / 09-08-2015
### Details
https://github.com/DataDog/dd-agent/compare/5.4.5...5.4.6

### Changes
* [BUGFIX] Disk: Force CDROM (iso9660) exclusion. See [#1786][]
* [BUGFIX] Disk: Recalculate `disk.in_use` to make consistent with `df`'s 'Use% metric'. See [#1785][]
* [BUGFIX] Gohai: Improve signal handling for `df` timeout. See [#16](https://github.com/DataDog/gohai/pull/16)
* [BUGFIX] Process: Correctly handle disappearing PID. See [#1721][] [#1772][]


# 5.4.5 / 08-20-2015
**Datadog Agent container only**

### Details
https://github.com/DataDog/dd-agent/compare/5.4.4...5.4.5

### Changes
* [IMPROVEMENT] Docker: Support for Docker 1.8 version. See [#1831][]


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

### New integration(s)
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

### New integration(s)
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
* HTTPCheck
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
* [FEATURE] HTTPCheck: Check for SSL certificate expiration. See [#1152][]
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
### Details
https://github.com/DataDog/dd-agent/compare/5.1.0...5.1.1

### Updated integrations
* BTRFS
* MongoDB

### Changes

* [BUGFIX] MongoDB: Fix TypeError that was happening in some cases. See [#1222][]
* [BUGFIX] BTRFS: Handle "unknown" usage type. See [#1221][]
* [BUGFIX] Windows: When uninstalling the Agent, the uninstaller was mistakenly telling the user that the machine would reboot. This is fixed.


# 5.1.0 / 11-24-2014
### Details
https://github.com/DataDog/dd-agent/compare/5.0.5...5.1.0

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
### Details
https://github.com/DataDog/dd-agent/compare/5.0.4...5.0.5

This release fixes a bug on servers that are configured in local time instead of UTC Time.
If your server's clock is configured to use daylight saving time, your server might stop sending metrics for up to one hour when the Daylight Saving Time ends or until the Agent is restarted after the Daylight Saving Time ends.

We highly recommend to upgrade to this version if your server is configured in local time.

# 5.0.4 (deb package, rpm package) / 10-17-2014
### Details
https://github.com/DataDog/dd-agent/compare/5.0.3...5.0.4

This is a security update regarding POODLE (CVE-2014-3566).

The Omnibus package will now bundle OpenSSL 1.0.1j without support of SSLv3 (no-ssl3 flag) and Python 2.7.8 with a patch that disables SSLv3 unless explicity asked http://bugs.python.org/issue22638.

This Omnibus package also adds support of the sqlite3 library for Python.

# 5.0.3 (Windows only)
### Details
https://github.com/DataDog/dd-agent/compare/5.0.2...5.0.3

vSphere check:

* [FEATURE] Batching jobs to cache the infrastructure of vCenter when autodiscovering Hosts/VMs is configurable
* [BUGFIX] Fix ESXi host tags not being correctly set
* [BUGFIX] Fix metadata reset so that metrics processing is not stopped when refreshing metadata
* [BUGFIX] Fix thread pool crash when one thread would not terminate gracefully

# 5.0.2 (Windows only)
### Details
https://github.com/DataDog/dd-agent/compare/5.0.1...5.0.2

vSphere check:

* [FEATURE] Changed the event filter to remove login events by default
* [BUGFIX] Duplicate tags on VMs and host
* [BUGFIX] Ignore duplicate events about VM migrations

# 5.0.1 (Windows only)
### Details
https://github.com/DataDog/dd-agent/compare/5.0.0...5.0.1

[FEATURE] Releasing the vSphere check. This is a new integration able to fetch metrics and events from vCenter.

# 5.0.0 / 08-22-2014
### Details
https://github.com/DataDog/dd-agent/compare/4.4.0...5.0.0

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
### Details
https://github.com/DataDog/dd-agent/compare/4.3.1...4.4.0

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
### Details
https://github.com/DataDog/dd-agent/compare/4.3.0...4.3.1

**Linux or Source Install only**

### Integrations affected
* Docker
* HAProxy

### Changes
* [IMPROVEMENT] Don't collect Docker total_ metrics by default. See [#964][]
* [BUGFIX] Report Docker CPU metrics as rate. See [#964][]
* [BUGFIX] Add HAProxy reporter name in HAProxy event's titles. See [#960][]

# 4.3.0 / 05-22-2014
### Details
https://github.com/DataDog/dd-agent/compare/4.2.2...4.3.0

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
### Details
https://github.com/DataDog/dd-agent/compare/4.2.1...4.2.2

**Windows Only**

### Integrations affected
* Redis

### Changes
* [FEATURE] Support Redis check on Windows: See [#917]

# 4.2.1 / 04-09-2014
### Details
https://github.com/DataDog/dd-agent/compare/4.2.0...4.2.1

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
### Details
https://github.com/DataDog/dd-agent/compare/4.1.0...4.2.0

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
#### Details
https://github.com/DataDog/dd-agent/compare/4.0.2...4.1.0

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


# 4.0.2 / 2014-01-08
**Windows Only**
#### Details
https://github.com/DataDog/dd-agent/compare/4.0.0...4.0.2

#### Changes
* [BUGFIX] Fix WMI Check


# 4.0.1 / 2013-12-17
**Linux or Source Install only**
#### Details
https://github.com/DataDog/dd-agent/compare/4.0.0...4.0.1

#### Changes
* [BUGFIX] Fix Postgresql check that was sending bad values in some cases.
* [BUGFIX] Fix replication lag calculation in MySql check.


# 4.0.0 / 2013-12-16
**This is a major version. See platform-specific pages for detailed changes.**
#### Details
https://github.com/DataDog/dd-agent/compare/3.10.1...4.0.0

#### Changes
- [FEATURE] Linux/Mac OS/Source install: Visit https://github.com/DataDog/dd-agent/wiki/Agent-4.0.0-for-Linux-,-Mac-OS-and-FreeBSD
- [FEATURE] Windows: Visit https://github.com/DataDog/dd-agent/wiki/Agent-4.0.0-for-Windows


# 3.10.1 / 2013-11-06
**Linux or Source Install only**
#### Details
https://github.com/DataDog/dd-agent/compare/3.10.0...3.10.1

#### Changes
* [BUGFIX] Fix Mongo Integration for newer versions of MongoDB [#677](https://github.com/DataDog/dd-agent/issues/677)
* [BUGFIX] Fix memory metrics for Mac Os X Mavericks
* [BUGFIX] Fix tagging issues for HTTP Check [8ab75](d1e09e3605f7c09177c5a6fb4f3e2b86a698ab75)
* [BUGFIX] Fix local issues  [4230](https://github.com/DataDog/dd-agent/commit/0d41c241a763bf8edbbb3419cda43f3ba1ad4230)


# 3.11.0 / 2013-10-08
**Windows Only**
#### Details
https://github.com/DataDog/dd-agent/compare/3.9.3...3.11.0

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


# 3.9.3 / 2013-09-11
**Windows Only**
#### Details
https://github.com/DataDog/dd-agent/compare/3.9.2...3.9.3

### Integrations Affected
* SQL Server

#### Changes
* [FEATURE] Allow optional custom tags in SQL Server check ([#654](https://github.com/DataDog/dd-agent/pull/654))
* [BUGFIX] Fix log file location on Windows XP


# 3.10.0 / 2013-09-06
**Linux or Source Install only**
#### Details
https://github.com/DataDog/dd-agent/compare/3.9.0...3.10.0

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


# 3.9.2 / 2013-08-29
**Windows Only**
#### Details
https://github.com/DataDog/dd-agent/compare/3.9.1...3.9.2

### Integrations Affected
* SQL Server

#### Changes
* [FEATURE] Default SQL Server to integrated security if no username/password is provided ([#622](https://github.com/DataDog/dd-agent/pull/622
))(Thanks to [@jamescrowley](https://github.com/jamescrowley))
* [FEATURE] Allow skipping ssl certificate validation (useful when the agent runs behind haproxy)  ([#641](https://github.com/DataDog/dd-agent/issues/641))
* [BUGFIX] Fix proxy support on Windows
* [BUGFIX] Better management of config files with the GUI


# 3.9.1 / 2013-08-19
**Windows Only**
#### Details
https://github.com/DataDog/dd-agent/compare/3.9.0...3.9.1

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


# 3.9.0 / 2013-08-05
#### Details
https://github.com/DataDog/dd-agent/compare/3.8.0...3.9.0

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


# 3.8.0 / 2013-06-19
#### Details
https://github.com/DataDog/dd-agent/compare/3.7.2...3.8.0

#### Changes
* [FEATURE] Add status command to Debian
* [FEATURE] Debian version now uses its own supervisor config instead of using the system config
* [FEATURE] Add `-v` option to info command, which currently gives stack traces for errors that occurred during checks
* [FEATURE] Add I/O metrics to OS X ([#131](https://github.com/DataDog/dd-agent/issues/131))
* [BUGFIX] Log exception when dogstatsd server fails to start ([#480](https://github.com/DataDog/dd-agent/issues/480))
* [BUGFIX] Fix `Error: Invalid user name dd-agent` appearing during source install ([#521](https://github.com/DataDog/dd-agent/issues/521))
* [BUGFIX] Debian and Red Hat init.d scripts now verify that `/etc/dd-agent/datadog.conf` is present before launching supervisor([#544](https://github.com/DataDog/dd-agent/issues/544))
* [BUGFIX] Fix AttributeErrors for `timeout_event` and `status_code_event` in Riak check ([#546](https://github.com/DataDog/dd-agent/pull/546))


# 3.7.2 / 2013-05-22
#### Details
https://github.com/DataDog/dd-agent/compare/3.7.1...3.7.2

#### Changes
* [FEATURE] Fix redis check when used with additional tags ([#515](https://github.com/DataDog/dd-agent/issues/515))


# 3.7.1 / 2013-05-21
#### Details
https://github.com/DataDog/dd-agent/compare/3.7.0...3.7.1

#### Changes
* [FEATURE] Add basic auth support for apache check ([#410](https://github.com/DataDog/dd-agent/issues/410))
* [FEATURE] Support any redis parameter during the connection ([#276](https://github.com/DataDog/dd-agent/issues/276))
* [FEATURE] Better launching script for source install
* [BUGFIX] Fix process check (Missing import and support version 0.4 of psutil) ([#502](https://github.com/DataDog/dd-agent/issues/502))
* [BUGFIX] Fix JVM Heap issue when launching java process ( Disable memory consumption watcher by default) ([#507](https://github.com/DataDog/dd-agent/issues/507))
* [BUGFIX] Info page shows errors when failing to initialize a check.d ([#427](https://github.com/DataDog/dd-agent/issues/427))
* [BUGFIX] Added file option to supervisorctl stop arg too ([#498](https://github.com/DataDog/dd-agent/pull/498)) (Thanks to [@mastrolinux](https://github.com/mastrolinux))
* [BUGFIX] Fix mysql version detection ([#501](https://github.com/DataDog/dd-agent/issues/501))


# 3.7.0 / 2013-05-08
#### Details
https://github.com/DataDog/dd-agent/compare/3.6.4...3.7.0

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


# 3.6.4 / 2013-04-25
**Windows only**
#### Details
https://github.com/DataDog/dd-agent/compare/3.6.3...3.6.4

### Bug fixes
* IIS: Use Total metrics and calculate rates in the Agent instead of using PerSec metrics. ([#465](https://github.com/DataDog/dd-agent/pull/465))
* IIS: Optionally give a list of sites to pull metrics from, defaulting to all.


# 3.6.3 / 2013-04-14
#### Details
https://github.com/DataDog/dd-agent/compare/3.6.2...3.6.3

#### Changes
* [BUGFIX} Customizable field names for cacti check ([#404](https://github.com/DataDog/dd-agent/issues/404))
* [BUGFIX} Enable replication monitoring by default for old style check configuration for mysql
* [BUGFIX} Always collect metrics for config specified queues/nodes for rabbitmq


# 3.6.2 / 2013-04-05
#### Details
https://github.com/DataDog/dd-agent/compare/3.6.1...3.6.2

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


# 3.6.1 / 2013-03-21
#### Details
https://github.com/DataDog/dd-agent/compare/3.6.0...3.6.1

#### Changes
* [FEATURE] Port Jenkins to checks.d
* [FEATURE] Lighttpd check now supports Lighttpd 2.0 ([#412](https://github.com/DataDog/dd-agent/pull/412)) (Thanks to [@brettlangdon](https://github.com/brettlangdon))
* [FEATURE]Additional configurable checks.d directory ([#413](https://github.com/DataDog/dd-agent/pull/413)) (Thanks to [@brettlangdon](https://github.com/brettlangdon))
* [BUGFIX] Better Jenkins check performance (reduce CPU consumption) ([#402](https://github.com/DataDog/dd-agent/issues/402))
* [BUGFIX] Fix Graphite listener ([#415](https://github.com/DataDog/dd-agent/issues/415))
* [BUGFIX] Less logging for pup ([#414](https://github.com/DataDog/dd-agent/issues/414))


# 3.6.0 / 2013-03-13
#### Details
https://github.com/DataDog/dd-agent/compare/3.5.1...3.6.0

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


# 3.5.1
This is a **RedHat-only** release.
#### Details
https://github.com/DataDog/dd-agent/compare/3.5.0...3.5.1

#### Changes
* [BUGFIX] Fix dogstatsd crash on RedHat 5.x and its derivatives ([#381](https://github.com/DataDog/dd-agent/pull/381))


# 3.5.0
#### Details
https://github.com/DataDog/dd-agent/compare/3.4.4...3.5.0

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


# 3.4.4
#### Details
https://github.com/DataDog/dd-agent/compare/3.4.3...3.4.4

#### Changes
* [BUGFIX] Fix memory leaks in redis check, and potentially in custom checks.d checks that supply duplicate tags ([#325](https://github.com/DataDog/dd-agent/issues/325))
* [BUGFIX] Fix mongo auth issue ([#318](https://github.com/DataDog/dd-agent/issues/318))
* [BUGFIX] Add configurable socket timeout to zookeeper check ([#310](https://github.com/DataDog/dd-agent/issues/310))

# 3.4.3
#### Details
https://github.com/DataDog/dd-agent/compare/3.4.2...3.4.3

#### Changes
* [BUGFIX] Fix memory leaks in memcache check ([#278](https://github.com/DataDog/dd-agent/issues/278))
* [BUGFIX] Fix umask issue ([#293](https://github.com/DataDog/dd-agent/issues/293))
* [BUGFIX] Fix bad error message in CentOS 5 installation ([#320](https://github.com/DataDog/dd-agent/issues/320))


# 3.4.2
**If you're having issues upgrading, please read the [upgrade notes](https://github.com/DataDog/dd-agent/wiki/Upgrade-Notes)**
#### Details
https://github.com/DataDog/dd-agent/compare/3.4.1...3.4.2

#### Changes
* [FEATURE] Check multiple Cassandra, Tomcat and Solr instances per host
* [FEATURE] Added a `JMXCheck` base class which can be used to easily track metrics from services that support JMX.
* [BUGFIX] Create `/etc/dd-agent/conf.d` on install
* [BUGFIX] Reduce verbosity of the logs


# 3.4.1
#### Details
https://github.com/DataDog/dd-agent/compare/3.4.0...3.4.1

#### Changes
* [FEATURE] Added an `info` command  (`sudo /etc/init.d/datadog-agent info`) which prints status info about the agent processes.
* [FEATURE] Added a check for [Zookeeper](http://zookeeper.apache.org/).
* [BUGFIX] Fixes packaging bugs introduced in 3.4.0.
* [BUGFIX] Agents installed with RPM will restart on upgrade (starting with the next version).
* [BUGFIX] Fixed normalized counter rounding error.
* [BUGFIX] By default, don't open ports other than localhost.


## 3.4.0 / 2012-11-28
#### Details
https://github.com/DataDog/dd-agent/compare/3.3.0...3.4.0

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


## 3.3.0 / 2012-10-25
#### Details
https://github.com/DataDog/dd-agent/compare/3.2.3...3.3.0

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


## 3.2.3 / 2012-10-15
#### Details
https://github.com/DataDog/dd-agent/compare/3.2.2...3.2.3

#### Changes
* [FEATURE] Windows support is officially added.
* [FEATURE] Added a SQL Server check.
* [FEATURE] Added an IIS check.
* [FEATURE] Track request_rate in HAProxy.
* [FEATURE] Move DogstatsD to the `datadog-agent-base` package.


# 3.2.2 / 2012-10-05
#### Details
https://github.com/DataDog/dd-agent/compare/3.2.1...3.2.2

#### Changes
* [BUGFIX] Fixes an issue with events in checks.d where only events from the last instance would be sent.


# 3.2.1 / 2012-10-05
#### Details
https://github.com/DataDog/dd-agent/compare/3.2.0...3.2.1

#### Changes
* [BUGFIX] Fixes an issue with duplicate events being created in `checks.d` checks.


## 3.2.0 / 2012-10-05
#### Details
https://github.com/DataDog/dd-agent/compare/3.1.7...3.2.0

#### Changes
* [FEATURE] Add new AgentCheck interface for all future checks.
* [FEATURE] Split checks and configuration with `checks.d`/`conf.d`.


# 3.1.7 / 2012-09-28
#### Details
https://github.com/DataDog/dd-agent/compare/3.1.6...3.1.7

#### Changes
* [BUGFIX] Fixes the case where you have the `python-redis` module and the check will run with default host/port even if you don't have any redis configuration. Fixes case [#200](https://github.com/DataDog/dd-agent/issues/200).


# 3.1.6 / 2012-09-27
#### Details
https://github.com/DataDog/dd-agent/compare/3.1.5...3.1.6

#### Changes
* [BUGFIX] Fixes memcached integration bug running under Python 2.4 [#201](https://github.com/DataDog/dd-agent/issues/201)
* [BUGFIX] Removes token from the Cassandra Stats, because it is not always a number. Fixes case [#202](https://github.com/DataDog/dd-agent/issues/202)


# 3.1.5 / 2012-09-21
#### Details
https://github.com/DataDog/dd-agent/compare/3.1.4...3.1.5

#### Changes
* [BUGFIX] Fixes network traffic reporting bug introduced in 3.1.4. If you're running 3.1.4 we recommended that you upgrade.


# 3.1.4 / 2012-09-21
#### Details
https://github.com/DataDog/dd-agent/compare/3.1.3...3.1.4

#### Changes
* [FEATURE] memcached and nginx checks now support multiple instances per host.
* [FEATURE] Statsd: Added `sets` metric type. Read the [docs](http://docs.datadoghq.com/guides/metrics/#sets).
* [FEATURE] Statsd: Now supports multiple metrics per packet.
* [FEATURE] Some under the hood work to support more platforms.
* [FEATURE] Bug fixes
* [BUGFIX] Fixes invalid configuration parsing in the case of pure JVM metrics.


# 3.1.3
#### Details
https://github.com/DataDog/dd-agent/compare/3.1.2...3.1.3

#### Changes
* [BUGFIX] Fixes invalid configuration parsing in the case of pure JVM metrics.

# 3.1.2
#### Details
https://github.com/DataDog/dd-agent/compare/3.1.1...3.1.2

#### Changes
* [FEATURE] Dogstream (parsing logs with dd-agent) supports parsing classes in addition to parsing functions.

# 3.1.1
#### Details
https://github.com/DataDog/dd-agent/compare/3.1.0...3.1.1

#### Changes
* [FEATURE] Multi-instance JMX check
* [FEATURE] dogstatsd counters now send 0 for up to 10 minutes after the last increment(). They work with alerts.
* [BUGFIX] [part 1 of [#16][]5](https://github.com/DataDog/dd-agent/issues/165) dogstatsd's average is fixed
* [BUGFIX] HAProxy logging level was logging debug messages by default.

# 3.1.0
#### Details
https://github.com/DataDog/dd-agent/compare/3.0.5...3.1.0

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
#### Details
https://github.com/DataDog/dd-agent/compare/3.0.4...3.0.5

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
#### Details
https://github.com/DataDog/dd-agent/compare/3.0.3...3.0.4

#### Changes
* [FEATURE] [#112](https://github.com/DataDog/dd-agent/issues/112) Thanks to [@charles-dyfis-net](https://github.com/charles-dyfis-net), the agent supports extra `emitters`. An emitter is an output for events and metrics.
* [FEATURE] [#117](https://github.com/DataDog/dd-agent/issues/117) Thanks to [@rl-0x0](https://github.com/rl-0x0), the agent can now parse supervisord logs and turn them into events and metrics.
* [FEATURE] [#121](https://github.com/DataDog/dd-agent/issues/121) Thanks to [@charles-dyfis-net](https://github.com/charles-dyfis-net), the agent supports custom checks. Check out our README for more details.

# 3.0.3
#### Details
https://github.com/DataDog/dd-agent/compare/3.0.2...3.0.3

#### Changes
* [BUGFIX] [#82](https://github.com/DataDog/dd-agent/issues/82) Now proudly runs on Amazon Web Services Linux.
* [FEATURE] [#110](https://github.com/DataDog/dd-agent/issues/110) More ElasticSearch metrics

# 3.0.2
#### Details
https://github.com/DataDog/dd-agent/compare/3.0.1...3.0.2

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
#### Details
https://github.com/DataDog/dd-agent/compare/2.2.26...2.2.27

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
#### Details
https://github.com/DataDog/dd-agent/compare/2.2.22...2.2.24

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
#### Details
https://github.com/DataDog/dd-agent/compare/2.2.19...2.2.20

#### Changes
* [BUGFIX] fixes MongoDB support, broken in 2.2.19.

# 2.2.19
#### Details
https://github.com/DataDog/dd-agent/compare/2.2.18...2.2.19

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
#### Details
https://github.com/DataDog/dd-agent/compare/2.2.14...2.2.15

#### Changes
* [BUGFIX] Fixes MongoDB configuration parsing.

# 2.2.14
#### Details
https://github.com/DataDog/dd-agent/compare/2.2.12...2.2.14

#### Changes
* [BUGFIX] Used memory was not reported on 2.2.12 when running the agent on Debian Lenny.
* [BUGFIX] Cacti memory is reported in MB, not in bytes.

# 2.2.12
#### Details
https://github.com/DataDog/dd-agent/compare/2.2.11...2.2.12

#### Changes
* [BUGFIX] Cacti check should fail gracefully if it cannot find RRD files.

# 2.2.11
#### Details
https://github.com/DataDog/dd-agent/compare/2.2.10...2.2.11

#### Changes
* [BUGFIX] Prevent counters from wrapping ([#23](/DataDog/dd-agent/pull/30))
* [BUGFIX] Collect shared memory metric, accessible in Datadog via system.mem.shared.

# 2.2.10
#### Details
https://github.com/DataDog/dd-agent/compare/2.2.9...2.2.10

#### Changes
* [BUGFIX] On CentOS5, when both `datadog-agent` and `datadog-agent-base` are installed, `datadog-agent-base` runs with the stock 2.4 python, which allows python modules that support integrations (e.g. mysql) to be installed with yum.

# 2.2.9 (minor)
#### Details
  https://github.com/DataDog/dd-agent/issues?milestone=1&state=closed

#### Changes
* [FEATURE] Added support for [cacti](http://www.cacti.net)
* [FEATURE] Added support for new memory metrics: `system.mem.buffers`, `system.mem.cached`, `system.mem.buffers`, `system.mem.usable`, `system.mem.total`

<!--- The following link definition list is generated by PimpMyChangelog --->
[#2]: https://github.com/DataDog/dd-agent/issues/2
[#3]: https://github.com/DataDog/dd-agent/issues/3
[#7]: https://github.com/DataDog/dd-agent/issues/7
[#8]: https://github.com/DataDog/dd-agent/issues/8
[#9]: https://github.com/DataDog/dd-agent/issues/9
[#16]: https://github.com/DataDog/dd-agent/issues/16
[#21]: https://github.com/DataDog/dd-agent/issues/21
[#23]: https://github.com/DataDog/dd-agent/issues/23
[#24]: https://github.com/DataDog/dd-agent/issues/24
[#30]: https://github.com/DataDog/dd-agent/issues/30
[#42]: https://github.com/DataDog/dd-agent/issues/42
[#48]: https://github.com/DataDog/dd-agent/issues/48
[#49]: https://github.com/DataDog/dd-agent/issues/49
[#51]: https://github.com/DataDog/dd-agent/issues/51
[#55]: https://github.com/DataDog/dd-agent/issues/55
[#57]: https://github.com/DataDog/dd-agent/issues/57
[#62]: https://github.com/DataDog/dd-agent/issues/62
[#63]: https://github.com/DataDog/dd-agent/issues/63
[#65]: https://github.com/DataDog/dd-agent/issues/65
[#66]: https://github.com/DataDog/dd-agent/issues/66
[#68]: https://github.com/DataDog/dd-agent/issues/68
[#71]: https://github.com/DataDog/dd-agent/issues/71
[#72]: https://github.com/DataDog/dd-agent/issues/72
[#73]: https://github.com/DataDog/dd-agent/issues/73
[#76]: https://github.com/DataDog/dd-agent/issues/76
[#78]: https://github.com/DataDog/dd-agent/issues/78
[#79]: https://github.com/DataDog/dd-agent/issues/79
[#80]: https://github.com/DataDog/dd-agent/issues/80
[#81]: https://github.com/DataDog/dd-agent/issues/81
[#82]: https://github.com/DataDog/dd-agent/issues/82
[#83]: https://github.com/DataDog/dd-agent/issues/83
[#89]: https://github.com/DataDog/dd-agent/issues/89
[#90]: https://github.com/DataDog/dd-agent/issues/90
[#91]: https://github.com/DataDog/dd-agent/issues/91
[#92]: https://github.com/DataDog/dd-agent/issues/92
[#94]: https://github.com/DataDog/dd-agent/issues/94
[#95]: https://github.com/DataDog/dd-agent/issues/95
[#96]: https://github.com/DataDog/dd-agent/issues/96
[#97]: https://github.com/DataDog/dd-agent/issues/97
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
[#339]: https://github.com/DataDog/dd-agent/issues/339
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
[#1156]: https://github.com/DataDog/dd-agent/issues/1156
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
[#1348]: https://github.com/DataDog/dd-agent/issues/1348
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
[#1427]: https://github.com/DataDog/dd-agent/issues/1427
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
[#1482]: https://github.com/DataDog/dd-agent/issues/1482
[#1487]: https://github.com/DataDog/dd-agent/issues/1487
[#1490]: https://github.com/DataDog/dd-agent/issues/1490
[#1503]: https://github.com/DataDog/dd-agent/issues/1503
[#1507]: https://github.com/DataDog/dd-agent/issues/1507
[#1509]: https://github.com/DataDog/dd-agent/issues/1509
[#1511]: https://github.com/DataDog/dd-agent/issues/1511
[#1512]: https://github.com/DataDog/dd-agent/issues/1512
[#1518]: https://github.com/DataDog/dd-agent/issues/1518
[#1527]: https://github.com/DataDog/dd-agent/issues/1527
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
[#1620]: https://github.com/DataDog/dd-agent/issues/1620
[#1621]: https://github.com/DataDog/dd-agent/issues/1621
[#1623]: https://github.com/DataDog/dd-agent/issues/1623
[#1626]: https://github.com/DataDog/dd-agent/issues/1626
[#1628]: https://github.com/DataDog/dd-agent/issues/1628
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
[#1660]: https://github.com/DataDog/dd-agent/issues/1660
[#1664]: https://github.com/DataDog/dd-agent/issues/1664
[#1666]: https://github.com/DataDog/dd-agent/issues/1666
[#1679]: https://github.com/DataDog/dd-agent/issues/1679
[#1691]: https://github.com/DataDog/dd-agent/issues/1691
[#1696]: https://github.com/DataDog/dd-agent/issues/1696
[#1700]: https://github.com/DataDog/dd-agent/issues/1700
[#1701]: https://github.com/DataDog/dd-agent/issues/1701
[#1709]: https://github.com/DataDog/dd-agent/issues/1709
[#1710]: https://github.com/DataDog/dd-agent/issues/1710
[#1715]: https://github.com/DataDog/dd-agent/issues/1715
[#1717]: https://github.com/DataDog/dd-agent/issues/1717
[#1718]: https://github.com/DataDog/dd-agent/issues/1718
[#1720]: https://github.com/DataDog/dd-agent/issues/1720
[#1721]: https://github.com/DataDog/dd-agent/issues/1721
[#1722]: https://github.com/DataDog/dd-agent/issues/1722
[#1725]: https://github.com/DataDog/dd-agent/issues/1725
[#1726]: https://github.com/DataDog/dd-agent/issues/1726
[#1727]: https://github.com/DataDog/dd-agent/issues/1727
[#1734]: https://github.com/DataDog/dd-agent/issues/1734
[#1736]: https://github.com/DataDog/dd-agent/issues/1736
[#1737]: https://github.com/DataDog/dd-agent/issues/1737
[#1744]: https://github.com/DataDog/dd-agent/issues/1744
[#1745]: https://github.com/DataDog/dd-agent/issues/1745
[#1747]: https://github.com/DataDog/dd-agent/issues/1747
[#1750]: https://github.com/DataDog/dd-agent/issues/1750
[#1752]: https://github.com/DataDog/dd-agent/issues/1752
[#1755]: https://github.com/DataDog/dd-agent/issues/1755
[#1757]: https://github.com/DataDog/dd-agent/issues/1757
[#1758]: https://github.com/DataDog/dd-agent/issues/1758
[#1759]: https://github.com/DataDog/dd-agent/issues/1759
[#1760]: https://github.com/DataDog/dd-agent/issues/1760
[#1761]: https://github.com/DataDog/dd-agent/issues/1761
[#1767]: https://github.com/DataDog/dd-agent/issues/1767
[#1770]: https://github.com/DataDog/dd-agent/issues/1770
[#1771]: https://github.com/DataDog/dd-agent/issues/1771
[#1772]: https://github.com/DataDog/dd-agent/issues/1772
[#1773]: https://github.com/DataDog/dd-agent/issues/1773
[#1774]: https://github.com/DataDog/dd-agent/issues/1774
[#1776]: https://github.com/DataDog/dd-agent/issues/1776
[#1777]: https://github.com/DataDog/dd-agent/issues/1777
[#1782]: https://github.com/DataDog/dd-agent/issues/1782
[#1785]: https://github.com/DataDog/dd-agent/issues/1785
[#1786]: https://github.com/DataDog/dd-agent/issues/1786
[#1789]: https://github.com/DataDog/dd-agent/issues/1789
[#1792]: https://github.com/DataDog/dd-agent/issues/1792
[#1793]: https://github.com/DataDog/dd-agent/issues/1793
[#1798]: https://github.com/DataDog/dd-agent/issues/1798
[#1799]: https://github.com/DataDog/dd-agent/issues/1799
[#1800]: https://github.com/DataDog/dd-agent/issues/1800
[#1811]: https://github.com/DataDog/dd-agent/issues/1811
[#1813]: https://github.com/DataDog/dd-agent/issues/1813
[#1820]: https://github.com/DataDog/dd-agent/issues/1820
[#1822]: https://github.com/DataDog/dd-agent/issues/1822
[#1823]: https://github.com/DataDog/dd-agent/issues/1823
[#1824]: https://github.com/DataDog/dd-agent/issues/1824
[#1825]: https://github.com/DataDog/dd-agent/issues/1825
[#1826]: https://github.com/DataDog/dd-agent/issues/1826
[#1831]: https://github.com/DataDog/dd-agent/issues/1831
[#1839]: https://github.com/DataDog/dd-agent/issues/1839
[#1843]: https://github.com/DataDog/dd-agent/issues/1843
[#1844]: https://github.com/DataDog/dd-agent/issues/1844
[#1845]: https://github.com/DataDog/dd-agent/issues/1845
[#1846]: https://github.com/DataDog/dd-agent/issues/1846
[#1848]: https://github.com/DataDog/dd-agent/issues/1848
[#1852]: https://github.com/DataDog/dd-agent/issues/1852
[#1855]: https://github.com/DataDog/dd-agent/issues/1855
[#1856]: https://github.com/DataDog/dd-agent/issues/1856
[#1859]: https://github.com/DataDog/dd-agent/issues/1859
[#1860]: https://github.com/DataDog/dd-agent/issues/1860
[#1861]: https://github.com/DataDog/dd-agent/issues/1861
[#1864]: https://github.com/DataDog/dd-agent/issues/1864
[#1865]: https://github.com/DataDog/dd-agent/issues/1865
[#1875]: https://github.com/DataDog/dd-agent/issues/1875
[#1878]: https://github.com/DataDog/dd-agent/issues/1878
[#1880]: https://github.com/DataDog/dd-agent/issues/1880
[#1883]: https://github.com/DataDog/dd-agent/issues/1883
[#1885]: https://github.com/DataDog/dd-agent/issues/1885
[#1888]: https://github.com/DataDog/dd-agent/issues/1888
[#1889]: https://github.com/DataDog/dd-agent/issues/1889
[#1891]: https://github.com/DataDog/dd-agent/issues/1891
[#1892]: https://github.com/DataDog/dd-agent/issues/1892
[#1895]: https://github.com/DataDog/dd-agent/issues/1895
[#1900]: https://github.com/DataDog/dd-agent/issues/1900
[#1902]: https://github.com/DataDog/dd-agent/issues/1902
[#1907]: https://github.com/DataDog/dd-agent/issues/1907
[#1908]: https://github.com/DataDog/dd-agent/issues/1908
[#1910]: https://github.com/DataDog/dd-agent/issues/1910
[#1912]: https://github.com/DataDog/dd-agent/issues/1912
[#1914]: https://github.com/DataDog/dd-agent/issues/1914
[#1915]: https://github.com/DataDog/dd-agent/issues/1915
[#1919]: https://github.com/DataDog/dd-agent/issues/1919
[#1923]: https://github.com/DataDog/dd-agent/issues/1923
[#1924]: https://github.com/DataDog/dd-agent/issues/1924
[#1928]: https://github.com/DataDog/dd-agent/issues/1928
[#1932]: https://github.com/DataDog/dd-agent/issues/1932
[#1933]: https://github.com/DataDog/dd-agent/issues/1933
[#1936]: https://github.com/DataDog/dd-agent/issues/1936
[#1939]: https://github.com/DataDog/dd-agent/issues/1939
[#1940]: https://github.com/DataDog/dd-agent/issues/1940
[#1942]: https://github.com/DataDog/dd-agent/issues/1942
[#1943]: https://github.com/DataDog/dd-agent/issues/1943
[#1944]: https://github.com/DataDog/dd-agent/issues/1944
[#1948]: https://github.com/DataDog/dd-agent/issues/1948
[#1951]: https://github.com/DataDog/dd-agent/issues/1951
[#1952]: https://github.com/DataDog/dd-agent/issues/1952
[#1959]: https://github.com/DataDog/dd-agent/issues/1959
[#1961]: https://github.com/DataDog/dd-agent/issues/1961
[#1965]: https://github.com/DataDog/dd-agent/issues/1965
[#1974]: https://github.com/DataDog/dd-agent/issues/1974
[#1975]: https://github.com/DataDog/dd-agent/issues/1975
[#1976]: https://github.com/DataDog/dd-agent/issues/1976
[#1978]: https://github.com/DataDog/dd-agent/issues/1978
[#1979]: https://github.com/DataDog/dd-agent/issues/1979
[#1984]: https://github.com/DataDog/dd-agent/issues/1984
[#1985]: https://github.com/DataDog/dd-agent/issues/1985
[#1986]: https://github.com/DataDog/dd-agent/issues/1986
[#1987]: https://github.com/DataDog/dd-agent/issues/1987
[#1988]: https://github.com/DataDog/dd-agent/issues/1988
[#1990]: https://github.com/DataDog/dd-agent/issues/1990
[#1993]: https://github.com/DataDog/dd-agent/issues/1993
[#1995]: https://github.com/DataDog/dd-agent/issues/1995
[#1996]: https://github.com/DataDog/dd-agent/issues/1996
[#1997]: https://github.com/DataDog/dd-agent/issues/1997
[#2000]: https://github.com/DataDog/dd-agent/issues/2000
[#2005]: https://github.com/DataDog/dd-agent/issues/2005
[#2008]: https://github.com/DataDog/dd-agent/issues/2008
[#2009]: https://github.com/DataDog/dd-agent/issues/2009
[#2010]: https://github.com/DataDog/dd-agent/issues/2010
[#2011]: https://github.com/DataDog/dd-agent/issues/2011
[#2015]: https://github.com/DataDog/dd-agent/issues/2015
[#2022]: https://github.com/DataDog/dd-agent/issues/2022
[#2023]: https://github.com/DataDog/dd-agent/issues/2023
[#2026]: https://github.com/DataDog/dd-agent/issues/2026
[#2029]: https://github.com/DataDog/dd-agent/issues/2029
[#2031]: https://github.com/DataDog/dd-agent/issues/2031
[#2034]: https://github.com/DataDog/dd-agent/issues/2034
[#2035]: https://github.com/DataDog/dd-agent/issues/2035
[#2038]: https://github.com/DataDog/dd-agent/issues/2038
[#2039]: https://github.com/DataDog/dd-agent/issues/2039
[#2040]: https://github.com/DataDog/dd-agent/issues/2040
[#2048]: https://github.com/DataDog/dd-agent/issues/2048
[#2055]: https://github.com/DataDog/dd-agent/issues/2055
[#2056]: https://github.com/DataDog/dd-agent/issues/2056
[#2057]: https://github.com/DataDog/dd-agent/issues/2057
[#2061]: https://github.com/DataDog/dd-agent/issues/2061
[#2062]: https://github.com/DataDog/dd-agent/issues/2062
[#2063]: https://github.com/DataDog/dd-agent/issues/2063
[#2064]: https://github.com/DataDog/dd-agent/issues/2064
[#2065]: https://github.com/DataDog/dd-agent/issues/2065
[#2071]: https://github.com/DataDog/dd-agent/issues/2071
[#2072]: https://github.com/DataDog/dd-agent/issues/2072
[#2075]: https://github.com/DataDog/dd-agent/issues/2075
[#2079]: https://github.com/DataDog/dd-agent/issues/2079
[#2081]: https://github.com/DataDog/dd-agent/issues/2081
[#2082]: https://github.com/DataDog/dd-agent/issues/2082
[#2084]: https://github.com/DataDog/dd-agent/issues/2084
[#2086]: https://github.com/DataDog/dd-agent/issues/2086
[#2087]: https://github.com/DataDog/dd-agent/issues/2087
[#2088]: https://github.com/DataDog/dd-agent/issues/2088
[#2091]: https://github.com/DataDog/dd-agent/issues/2091
[#2092]: https://github.com/DataDog/dd-agent/issues/2092
[#2094]: https://github.com/DataDog/dd-agent/issues/2094
[#2097]: https://github.com/DataDog/dd-agent/issues/2097
[#2098]: https://github.com/DataDog/dd-agent/issues/2098
[#2100]: https://github.com/DataDog/dd-agent/issues/2100
[#2106]: https://github.com/DataDog/dd-agent/issues/2106
[#2108]: https://github.com/DataDog/dd-agent/issues/2108
[#2109]: https://github.com/DataDog/dd-agent/issues/2109
[#2111]: https://github.com/DataDog/dd-agent/issues/2111
[#2112]: https://github.com/DataDog/dd-agent/issues/2112
[#2114]: https://github.com/DataDog/dd-agent/issues/2114
[#2115]: https://github.com/DataDog/dd-agent/issues/2115
[#2116]: https://github.com/DataDog/dd-agent/issues/2116
[#2119]: https://github.com/DataDog/dd-agent/issues/2119
[#2120]: https://github.com/DataDog/dd-agent/issues/2120
[#2121]: https://github.com/DataDog/dd-agent/issues/2121
[#2126]: https://github.com/DataDog/dd-agent/issues/2126
[#2128]: https://github.com/DataDog/dd-agent/issues/2128
[#2130]: https://github.com/DataDog/dd-agent/issues/2130
[#2133]: https://github.com/DataDog/dd-agent/issues/2133
[#2134]: https://github.com/DataDog/dd-agent/issues/2134
[#2135]: https://github.com/DataDog/dd-agent/issues/2135
[#2136]: https://github.com/DataDog/dd-agent/issues/2136
[#2139]: https://github.com/DataDog/dd-agent/issues/2139
[#2140]: https://github.com/DataDog/dd-agent/issues/2140
[#2142]: https://github.com/DataDog/dd-agent/issues/2142
[#2143]: https://github.com/DataDog/dd-agent/issues/2143
[#2145]: https://github.com/DataDog/dd-agent/issues/2145
[#2146]: https://github.com/DataDog/dd-agent/issues/2146
[#2147]: https://github.com/DataDog/dd-agent/issues/2147
[#2148]: https://github.com/DataDog/dd-agent/issues/2148
[#2152]: https://github.com/DataDog/dd-agent/issues/2152
[#2153]: https://github.com/DataDog/dd-agent/issues/2153
[#2155]: https://github.com/DataDog/dd-agent/issues/2155
[#2156]: https://github.com/DataDog/dd-agent/issues/2156
[#2157]: https://github.com/DataDog/dd-agent/issues/2157
[#2160]: https://github.com/DataDog/dd-agent/issues/2160
[#2161]: https://github.com/DataDog/dd-agent/issues/2161
[#2162]: https://github.com/DataDog/dd-agent/issues/2162
[#2163]: https://github.com/DataDog/dd-agent/issues/2163
[#2164]: https://github.com/DataDog/dd-agent/issues/2164
[#2165]: https://github.com/DataDog/dd-agent/issues/2165
[#2166]: https://github.com/DataDog/dd-agent/issues/2166
[#2169]: https://github.com/DataDog/dd-agent/issues/2169
[#2171]: https://github.com/DataDog/dd-agent/issues/2171
[#2175]: https://github.com/DataDog/dd-agent/issues/2175
[#2176]: https://github.com/DataDog/dd-agent/issues/2176
[#2177]: https://github.com/DataDog/dd-agent/issues/2177
[#2179]: https://github.com/DataDog/dd-agent/issues/2179
[#2180]: https://github.com/DataDog/dd-agent/issues/2180
[#2181]: https://github.com/DataDog/dd-agent/issues/2181
[#2182]: https://github.com/DataDog/dd-agent/issues/2182
[#2183]: https://github.com/DataDog/dd-agent/issues/2183
[#2184]: https://github.com/DataDog/dd-agent/issues/2184
[#2185]: https://github.com/DataDog/dd-agent/issues/2185
[#2186]: https://github.com/DataDog/dd-agent/issues/2186
[#2189]: https://github.com/DataDog/dd-agent/issues/2189
[#2192]: https://github.com/DataDog/dd-agent/issues/2192
[#2193]: https://github.com/DataDog/dd-agent/issues/2193
[#2195]: https://github.com/DataDog/dd-agent/issues/2195
[#2198]: https://github.com/DataDog/dd-agent/issues/2198
[#2199]: https://github.com/DataDog/dd-agent/issues/2199
[#2200]: https://github.com/DataDog/dd-agent/issues/2200
[#2201]: https://github.com/DataDog/dd-agent/issues/2201
[#2202]: https://github.com/DataDog/dd-agent/issues/2202
[#2203]: https://github.com/DataDog/dd-agent/issues/2203
[#2205]: https://github.com/DataDog/dd-agent/issues/2205
[#2206]: https://github.com/DataDog/dd-agent/issues/2206
[#2207]: https://github.com/DataDog/dd-agent/issues/2207
[#2208]: https://github.com/DataDog/dd-agent/issues/2208
[#2210]: https://github.com/DataDog/dd-agent/issues/2210
[#2215]: https://github.com/DataDog/dd-agent/issues/2215
[#2216]: https://github.com/DataDog/dd-agent/issues/2216
[#2218]: https://github.com/DataDog/dd-agent/issues/2218
[#2220]: https://github.com/DataDog/dd-agent/issues/2220
[#2223]: https://github.com/DataDog/dd-agent/issues/2223
[#2225]: https://github.com/DataDog/dd-agent/issues/2225
[#2227]: https://github.com/DataDog/dd-agent/issues/2227
[#2228]: https://github.com/DataDog/dd-agent/issues/2228
[#2229]: https://github.com/DataDog/dd-agent/issues/2229
[#2232]: https://github.com/DataDog/dd-agent/issues/2232
[#2234]: https://github.com/DataDog/dd-agent/issues/2234
[#2235]: https://github.com/DataDog/dd-agent/issues/2235
[#2236]: https://github.com/DataDog/dd-agent/issues/2236
[#2237]: https://github.com/DataDog/dd-agent/issues/2237
[#2241]: https://github.com/DataDog/dd-agent/issues/2241
[#2242]: https://github.com/DataDog/dd-agent/issues/2242
[#2243]: https://github.com/DataDog/dd-agent/issues/2243
[#2244]: https://github.com/DataDog/dd-agent/issues/2244
[#2245]: https://github.com/DataDog/dd-agent/issues/2245
[#2246]: https://github.com/DataDog/dd-agent/issues/2246
[#2248]: https://github.com/DataDog/dd-agent/issues/2248
[#2249]: https://github.com/DataDog/dd-agent/issues/2249
[#2250]: https://github.com/DataDog/dd-agent/issues/2250
[#2259]: https://github.com/DataDog/dd-agent/issues/2259
[#2260]: https://github.com/DataDog/dd-agent/issues/2260
[#2263]: https://github.com/DataDog/dd-agent/issues/2263
[#2264]: https://github.com/DataDog/dd-agent/issues/2264
[#2266]: https://github.com/DataDog/dd-agent/issues/2266
[#2268]: https://github.com/DataDog/dd-agent/issues/2268
[#2271]: https://github.com/DataDog/dd-agent/issues/2271
[#2273]: https://github.com/DataDog/dd-agent/issues/2273
[#2274]: https://github.com/DataDog/dd-agent/issues/2274
[#2278]: https://github.com/DataDog/dd-agent/issues/2278
[#2280]: https://github.com/DataDog/dd-agent/issues/2280
[#2283]: https://github.com/DataDog/dd-agent/issues/2283
[#2285]: https://github.com/DataDog/dd-agent/issues/2285
[#2287]: https://github.com/DataDog/dd-agent/issues/2287
[#2288]: https://github.com/DataDog/dd-agent/issues/2288
[#2289]: https://github.com/DataDog/dd-agent/issues/2289
[#2291]: https://github.com/DataDog/dd-agent/issues/2291
[#2292]: https://github.com/DataDog/dd-agent/issues/2292
[#2296]: https://github.com/DataDog/dd-agent/issues/2296
[#2298]: https://github.com/DataDog/dd-agent/issues/2298
[#2299]: https://github.com/DataDog/dd-agent/issues/2299
[#2304]: https://github.com/DataDog/dd-agent/issues/2304
[#2308]: https://github.com/DataDog/dd-agent/issues/2308
[#2309]: https://github.com/DataDog/dd-agent/issues/2309
[#2311]: https://github.com/DataDog/dd-agent/issues/2311
[#2314]: https://github.com/DataDog/dd-agent/issues/2314
[#2320]: https://github.com/DataDog/dd-agent/issues/2320
[#2321]: https://github.com/DataDog/dd-agent/issues/2321
[#2322]: https://github.com/DataDog/dd-agent/issues/2322
[#2329]: https://github.com/DataDog/dd-agent/issues/2329
[#2339]: https://github.com/DataDog/dd-agent/issues/2339
[#2341]: https://github.com/DataDog/dd-agent/issues/2341
[#2345]: https://github.com/DataDog/dd-agent/issues/2345
[#2349]: https://github.com/DataDog/dd-agent/issues/2349
[#2351]: https://github.com/DataDog/dd-agent/issues/2351
[#2353]: https://github.com/DataDog/dd-agent/issues/2353
[#2357]: https://github.com/DataDog/dd-agent/issues/2357
[#2359]: https://github.com/DataDog/dd-agent/issues/2359
[#2363]: https://github.com/DataDog/dd-agent/issues/2363
[#2366]: https://github.com/DataDog/dd-agent/issues/2366
[#2368]: https://github.com/DataDog/dd-agent/issues/2368
[#2369]: https://github.com/DataDog/dd-agent/issues/2369
[#2371]: https://github.com/DataDog/dd-agent/issues/2371
[#2372]: https://github.com/DataDog/dd-agent/issues/2372
[#2373]: https://github.com/DataDog/dd-agent/issues/2373
[#2377]: https://github.com/DataDog/dd-agent/issues/2377
[#2378]: https://github.com/DataDog/dd-agent/issues/2378
[#2379]: https://github.com/DataDog/dd-agent/issues/2379
[#2381]: https://github.com/DataDog/dd-agent/issues/2381
[#2384]: https://github.com/DataDog/dd-agent/issues/2384
[#2385]: https://github.com/DataDog/dd-agent/issues/2385
[#2387]: https://github.com/DataDog/dd-agent/issues/2387
[#2388]: https://github.com/DataDog/dd-agent/issues/2388
[#2389]: https://github.com/DataDog/dd-agent/issues/2389
[#2390]: https://github.com/DataDog/dd-agent/issues/2390
[#2392]: https://github.com/DataDog/dd-agent/issues/2392
[#2393]: https://github.com/DataDog/dd-agent/issues/2393
[#2397]: https://github.com/DataDog/dd-agent/issues/2397
[#2400]: https://github.com/DataDog/dd-agent/issues/2400
[#2401]: https://github.com/DataDog/dd-agent/issues/2401
[#2402]: https://github.com/DataDog/dd-agent/issues/2402
[#2403]: https://github.com/DataDog/dd-agent/issues/2403
[#2405]: https://github.com/DataDog/dd-agent/issues/2405
[#2406]: https://github.com/DataDog/dd-agent/issues/2406
[#2407]: https://github.com/DataDog/dd-agent/issues/2407
[#2409]: https://github.com/DataDog/dd-agent/issues/2409
[#2410]: https://github.com/DataDog/dd-agent/issues/2410
[#2413]: https://github.com/DataDog/dd-agent/issues/2413
[#2414]: https://github.com/DataDog/dd-agent/issues/2414
[#2417]: https://github.com/DataDog/dd-agent/issues/2417
[#2418]: https://github.com/DataDog/dd-agent/issues/2418
[#2422]: https://github.com/DataDog/dd-agent/issues/2422
[#2423]: https://github.com/DataDog/dd-agent/issues/2423
[#2424]: https://github.com/DataDog/dd-agent/issues/2424
[#2425]: https://github.com/DataDog/dd-agent/issues/2425
[#2426]: https://github.com/DataDog/dd-agent/issues/2426
[#2427]: https://github.com/DataDog/dd-agent/issues/2427
[#2429]: https://github.com/DataDog/dd-agent/issues/2429
[#2430]: https://github.com/DataDog/dd-agent/issues/2430
[#2431]: https://github.com/DataDog/dd-agent/issues/2431
[#2432]: https://github.com/DataDog/dd-agent/issues/2432
[#2441]: https://github.com/DataDog/dd-agent/issues/2441
[#2443]: https://github.com/DataDog/dd-agent/issues/2443
[#2444]: https://github.com/DataDog/dd-agent/issues/2444
[#2446]: https://github.com/DataDog/dd-agent/issues/2446
[#2447]: https://github.com/DataDog/dd-agent/issues/2447
[#2448]: https://github.com/DataDog/dd-agent/issues/2448
[#2451]: https://github.com/DataDog/dd-agent/issues/2451
[#2454]: https://github.com/DataDog/dd-agent/issues/2454
[#2456]: https://github.com/DataDog/dd-agent/issues/2456
[#2457]: https://github.com/DataDog/dd-agent/issues/2457
[#2459]: https://github.com/DataDog/dd-agent/issues/2459
[#2463]: https://github.com/DataDog/dd-agent/issues/2463
[#2464]: https://github.com/DataDog/dd-agent/issues/2464
[#2466]: https://github.com/DataDog/dd-agent/issues/2466
[#2467]: https://github.com/DataDog/dd-agent/issues/2467
[#2468]: https://github.com/DataDog/dd-agent/issues/2468
[#2469]: https://github.com/DataDog/dd-agent/issues/2469
[#2472]: https://github.com/DataDog/dd-agent/issues/2472
[#2473]: https://github.com/DataDog/dd-agent/issues/2473
[#2474]: https://github.com/DataDog/dd-agent/issues/2474
[#2476]: https://github.com/DataDog/dd-agent/issues/2476
[#2477]: https://github.com/DataDog/dd-agent/issues/2477
[#2479]: https://github.com/DataDog/dd-agent/issues/2479
[#2482]: https://github.com/DataDog/dd-agent/issues/2482
[#2483]: https://github.com/DataDog/dd-agent/issues/2483
[#2486]: https://github.com/DataDog/dd-agent/issues/2486
[#2487]: https://github.com/DataDog/dd-agent/issues/2487
[#2490]: https://github.com/DataDog/dd-agent/issues/2490
[#2491]: https://github.com/DataDog/dd-agent/issues/2491
[#2492]: https://github.com/DataDog/dd-agent/issues/2492
[#2494]: https://github.com/DataDog/dd-agent/issues/2494
[#2499]: https://github.com/DataDog/dd-agent/issues/2499
[#2500]: https://github.com/DataDog/dd-agent/issues/2500
[#2502]: https://github.com/DataDog/dd-agent/issues/2502
[#2507]: https://github.com/DataDog/dd-agent/issues/2507
[#2508]: https://github.com/DataDog/dd-agent/issues/2508
[#2510]: https://github.com/DataDog/dd-agent/issues/2510
[#2512]: https://github.com/DataDog/dd-agent/issues/2512
[#2514]: https://github.com/DataDog/dd-agent/issues/2514
[#2515]: https://github.com/DataDog/dd-agent/issues/2515
[#2516]: https://github.com/DataDog/dd-agent/issues/2516
[#2521]: https://github.com/DataDog/dd-agent/issues/2521
[#2528]: https://github.com/DataDog/dd-agent/issues/2528
[#2531]: https://github.com/DataDog/dd-agent/issues/2531
[#2535]: https://github.com/DataDog/dd-agent/issues/2535
[#2537]: https://github.com/DataDog/dd-agent/issues/2537
[#2538]: https://github.com/DataDog/dd-agent/issues/2538
[#2541]: https://github.com/DataDog/dd-agent/issues/2541
[#2542]: https://github.com/DataDog/dd-agent/issues/2542
[#2543]: https://github.com/DataDog/dd-agent/issues/2543
[#2544]: https://github.com/DataDog/dd-agent/issues/2544
[#2548]: https://github.com/DataDog/dd-agent/issues/2548
[#2551]: https://github.com/DataDog/dd-agent/issues/2551
[#2553]: https://github.com/DataDog/dd-agent/issues/2553
[#2556]: https://github.com/DataDog/dd-agent/issues/2556
[#2557]: https://github.com/DataDog/dd-agent/issues/2557
[#2559]: https://github.com/DataDog/dd-agent/issues/2559
[#2560]: https://github.com/DataDog/dd-agent/issues/2560
[#2564]: https://github.com/DataDog/dd-agent/issues/2564
[#2565]: https://github.com/DataDog/dd-agent/issues/2565
[#2572]: https://github.com/DataDog/dd-agent/issues/2572
[#2573]: https://github.com/DataDog/dd-agent/issues/2573
[#2575]: https://github.com/DataDog/dd-agent/issues/2575
[#2580]: https://github.com/DataDog/dd-agent/issues/2580
[#2586]: https://github.com/DataDog/dd-agent/issues/2586
[#2588]: https://github.com/DataDog/dd-agent/issues/2588
[#2590]: https://github.com/DataDog/dd-agent/issues/2590
[#2591]: https://github.com/DataDog/dd-agent/issues/2591
[#2592]: https://github.com/DataDog/dd-agent/issues/2592
[#2593]: https://github.com/DataDog/dd-agent/issues/2593
[#2600]: https://github.com/DataDog/dd-agent/issues/2600
[#2603]: https://github.com/DataDog/dd-agent/issues/2603
[#2605]: https://github.com/DataDog/dd-agent/issues/2605
[#2607]: https://github.com/DataDog/dd-agent/issues/2607
[#2608]: https://github.com/DataDog/dd-agent/issues/2608
[#2609]: https://github.com/DataDog/dd-agent/issues/2609
[#2610]: https://github.com/DataDog/dd-agent/issues/2610
[#2619]: https://github.com/DataDog/dd-agent/issues/2619
[#2620]: https://github.com/DataDog/dd-agent/issues/2620
[#2621]: https://github.com/DataDog/dd-agent/issues/2621
[#2622]: https://github.com/DataDog/dd-agent/issues/2622
[#2625]: https://github.com/DataDog/dd-agent/issues/2625
[#2626]: https://github.com/DataDog/dd-agent/issues/2626
[#2627]: https://github.com/DataDog/dd-agent/issues/2627
[#2628]: https://github.com/DataDog/dd-agent/issues/2628
[#2631]: https://github.com/DataDog/dd-agent/issues/2631
[#2633]: https://github.com/DataDog/dd-agent/issues/2633
[#2639]: https://github.com/DataDog/dd-agent/issues/2639
[#2640]: https://github.com/DataDog/dd-agent/issues/2640
[#2646]: https://github.com/DataDog/dd-agent/issues/2646
[#2649]: https://github.com/DataDog/dd-agent/issues/2649
[#2651]: https://github.com/DataDog/dd-agent/issues/2651
[#2653]: https://github.com/DataDog/dd-agent/issues/2653
[#2658]: https://github.com/DataDog/dd-agent/issues/2658
[#2660]: https://github.com/DataDog/dd-agent/issues/2660
[#2661]: https://github.com/DataDog/dd-agent/issues/2661
[#2666]: https://github.com/DataDog/dd-agent/issues/2666
[#2667]: https://github.com/DataDog/dd-agent/issues/2667
[#2669]: https://github.com/DataDog/dd-agent/issues/2669
[#2670]: https://github.com/DataDog/dd-agent/issues/2670
[#2672]: https://github.com/DataDog/dd-agent/issues/2672
[#2673]: https://github.com/DataDog/dd-agent/issues/2673
[#2674]: https://github.com/DataDog/dd-agent/issues/2674
[#2677]: https://github.com/DataDog/dd-agent/issues/2677
[#2681]: https://github.com/DataDog/dd-agent/issues/2681
[#2684]: https://github.com/DataDog/dd-agent/issues/2684
[#2688]: https://github.com/DataDog/dd-agent/issues/2688
[#2691]: https://github.com/DataDog/dd-agent/issues/2691
[#2696]: https://github.com/DataDog/dd-agent/issues/2696
[#2702]: https://github.com/DataDog/dd-agent/issues/2702
[#2704]: https://github.com/DataDog/dd-agent/issues/2704
[#2708]: https://github.com/DataDog/dd-agent/issues/2708
[#2709]: https://github.com/DataDog/dd-agent/issues/2709
[#2711]: https://github.com/DataDog/dd-agent/issues/2711
[#2713]: https://github.com/DataDog/dd-agent/issues/2713
[#2714]: https://github.com/DataDog/dd-agent/issues/2714
[#2715]: https://github.com/DataDog/dd-agent/issues/2715
[#2724]: https://github.com/DataDog/dd-agent/issues/2724
[#2727]: https://github.com/DataDog/dd-agent/issues/2727
[#2729]: https://github.com/DataDog/dd-agent/issues/2729
[#2733]: https://github.com/DataDog/dd-agent/issues/2733
[#2734]: https://github.com/DataDog/dd-agent/issues/2734
[#2735]: https://github.com/DataDog/dd-agent/issues/2735
[#2736]: https://github.com/DataDog/dd-agent/issues/2736
[#2739]: https://github.com/DataDog/dd-agent/issues/2739
[#2740]: https://github.com/DataDog/dd-agent/issues/2740
[#2744]: https://github.com/DataDog/dd-agent/issues/2744
[#2745]: https://github.com/DataDog/dd-agent/issues/2745
[#2749]: https://github.com/DataDog/dd-agent/issues/2749
[#2752]: https://github.com/DataDog/dd-agent/issues/2752
[#2757]: https://github.com/DataDog/dd-agent/issues/2757
[#2758]: https://github.com/DataDog/dd-agent/issues/2758
[#2762]: https://github.com/DataDog/dd-agent/issues/2762
[#2772]: https://github.com/DataDog/dd-agent/issues/2772
[#2774]: https://github.com/DataDog/dd-agent/issues/2774
[#2779]: https://github.com/DataDog/dd-agent/issues/2779
[#2780]: https://github.com/DataDog/dd-agent/issues/2780
[#2782]: https://github.com/DataDog/dd-agent/issues/2782
[#2783]: https://github.com/DataDog/dd-agent/issues/2783
[#2784]: https://github.com/DataDog/dd-agent/issues/2784
[#2788]: https://github.com/DataDog/dd-agent/issues/2788
[#2796]: https://github.com/DataDog/dd-agent/issues/2796
[#2797]: https://github.com/DataDog/dd-agent/issues/2797
[#2798]: https://github.com/DataDog/dd-agent/issues/2798
[#2801]: https://github.com/DataDog/dd-agent/issues/2801
[#2803]: https://github.com/DataDog/dd-agent/issues/2803
[#2805]: https://github.com/DataDog/dd-agent/issues/2805
[#2809]: https://github.com/DataDog/dd-agent/issues/2809
[#2812]: https://github.com/DataDog/dd-agent/issues/2812
[#2813]: https://github.com/DataDog/dd-agent/issues/2813
[#2815]: https://github.com/DataDog/dd-agent/issues/2815
[#2820]: https://github.com/DataDog/dd-agent/issues/2820
[#2823]: https://github.com/DataDog/dd-agent/issues/2823
[#2825]: https://github.com/DataDog/dd-agent/issues/2825
[#2826]: https://github.com/DataDog/dd-agent/issues/2826
[#2829]: https://github.com/DataDog/dd-agent/issues/2829
[#2833]: https://github.com/DataDog/dd-agent/issues/2833
[#2836]: https://github.com/DataDog/dd-agent/issues/2836
[#2840]: https://github.com/DataDog/dd-agent/issues/2840
[#2843]: https://github.com/DataDog/dd-agent/issues/2843
[#2844]: https://github.com/DataDog/dd-agent/issues/2844
[#2846]: https://github.com/DataDog/dd-agent/issues/2846
[#2847]: https://github.com/DataDog/dd-agent/issues/2847
[#2848]: https://github.com/DataDog/dd-agent/issues/2848
[#2849]: https://github.com/DataDog/dd-agent/issues/2849
[#2852]: https://github.com/DataDog/dd-agent/issues/2852
[#2855]: https://github.com/DataDog/dd-agent/issues/2855
[#2856]: https://github.com/DataDog/dd-agent/issues/2856
[#2858]: https://github.com/DataDog/dd-agent/issues/2858
[#2859]: https://github.com/DataDog/dd-agent/issues/2859
[#2866]: https://github.com/DataDog/dd-agent/issues/2866
[#2873]: https://github.com/DataDog/dd-agent/issues/2873
[#2877]: https://github.com/DataDog/dd-agent/issues/2877
[#2879]: https://github.com/DataDog/dd-agent/issues/2879
[#2885]: https://github.com/DataDog/dd-agent/issues/2885
[#2887]: https://github.com/DataDog/dd-agent/issues/2887
[#2890]: https://github.com/DataDog/dd-agent/issues/2890
[#2894]: https://github.com/DataDog/dd-agent/issues/2894
[#2897]: https://github.com/DataDog/dd-agent/issues/2897
[#2898]: https://github.com/DataDog/dd-agent/issues/2898
[#2900]: https://github.com/DataDog/dd-agent/issues/2900
[#2901]: https://github.com/DataDog/dd-agent/issues/2901
[#2908]: https://github.com/DataDog/dd-agent/issues/2908
[#2910]: https://github.com/DataDog/dd-agent/issues/2910
[#2915]: https://github.com/DataDog/dd-agent/issues/2915
[#2920]: https://github.com/DataDog/dd-agent/issues/2920
[#2921]: https://github.com/DataDog/dd-agent/issues/2921
[#2924]: https://github.com/DataDog/dd-agent/issues/2924
[#2926]: https://github.com/DataDog/dd-agent/issues/2926
[#2928]: https://github.com/DataDog/dd-agent/issues/2928
[#2929]: https://github.com/DataDog/dd-agent/issues/2929
[#2931]: https://github.com/DataDog/dd-agent/issues/2931
[#2934]: https://github.com/DataDog/dd-agent/issues/2934
[#2935]: https://github.com/DataDog/dd-agent/issues/2935
[#2937]: https://github.com/DataDog/dd-agent/issues/2937
[#2938]: https://github.com/DataDog/dd-agent/issues/2938
[#2940]: https://github.com/DataDog/dd-agent/issues/2940
[#2941]: https://github.com/DataDog/dd-agent/issues/2941
[#2942]: https://github.com/DataDog/dd-agent/issues/2942
[#2947]: https://github.com/DataDog/dd-agent/issues/2947
[#2948]: https://github.com/DataDog/dd-agent/issues/2948
[#2950]: https://github.com/DataDog/dd-agent/issues/2950
[#2951]: https://github.com/DataDog/dd-agent/issues/2951
[#2955]: https://github.com/DataDog/dd-agent/issues/2955
[#2956]: https://github.com/DataDog/dd-agent/issues/2956
[#2957]: https://github.com/DataDog/dd-agent/issues/2957
[#2960]: https://github.com/DataDog/dd-agent/issues/2960
[#2962]: https://github.com/DataDog/dd-agent/issues/2962
[#2964]: https://github.com/DataDog/dd-agent/issues/2964
[#2965]: https://github.com/DataDog/dd-agent/issues/2965
[#2967]: https://github.com/DataDog/dd-agent/issues/2967
[#2968]: https://github.com/DataDog/dd-agent/issues/2968
[#2970]: https://github.com/DataDog/dd-agent/issues/2970
[#2971]: https://github.com/DataDog/dd-agent/issues/2971
[#2972]: https://github.com/DataDog/dd-agent/issues/2972
[#2973]: https://github.com/DataDog/dd-agent/issues/2973
[#2975]: https://github.com/DataDog/dd-agent/issues/2975
[#2976]: https://github.com/DataDog/dd-agent/issues/2976
[#2978]: https://github.com/DataDog/dd-agent/issues/2978
[#2982]: https://github.com/DataDog/dd-agent/issues/2982
[#2983]: https://github.com/DataDog/dd-agent/issues/2983
[#2984]: https://github.com/DataDog/dd-agent/issues/2984
[#2989]: https://github.com/DataDog/dd-agent/issues/2989
[#2990]: https://github.com/DataDog/dd-agent/issues/2990
[#2991]: https://github.com/DataDog/dd-agent/issues/2991
[#3002]: https://github.com/DataDog/dd-agent/issues/3002
[#3004]: https://github.com/DataDog/dd-agent/issues/3004
[#3005]: https://github.com/DataDog/dd-agent/issues/3005
[#3006]: https://github.com/DataDog/dd-agent/issues/3006
[#3007]: https://github.com/DataDog/dd-agent/issues/3007
[#3010]: https://github.com/DataDog/dd-agent/issues/3010
[#3011]: https://github.com/DataDog/dd-agent/issues/3011
[#3012]: https://github.com/DataDog/dd-agent/issues/3012
[#3013]: https://github.com/DataDog/dd-agent/issues/3013
[#3015]: https://github.com/DataDog/dd-agent/issues/3015
[#3016]: https://github.com/DataDog/dd-agent/issues/3016
[#3018]: https://github.com/DataDog/dd-agent/issues/3018
[#3023]: https://github.com/DataDog/dd-agent/issues/3023
[#3024]: https://github.com/DataDog/dd-agent/issues/3024
[#3028]: https://github.com/DataDog/dd-agent/issues/3028
[#3035]: https://github.com/DataDog/dd-agent/issues/3035
[#3037]: https://github.com/DataDog/dd-agent/issues/3037
[#3038]: https://github.com/DataDog/dd-agent/issues/3038
[#3039]: https://github.com/DataDog/dd-agent/issues/3039
[#3040]: https://github.com/DataDog/dd-agent/issues/3040
[#3041]: https://github.com/DataDog/dd-agent/issues/3041
[#3043]: https://github.com/DataDog/dd-agent/issues/3043
[#3044]: https://github.com/DataDog/dd-agent/issues/3044
[#3048]: https://github.com/DataDog/dd-agent/issues/3048
[#3049]: https://github.com/DataDog/dd-agent/issues/3049
[#3051]: https://github.com/DataDog/dd-agent/issues/3051
[#3052]: https://github.com/DataDog/dd-agent/issues/3052
[#3053]: https://github.com/DataDog/dd-agent/issues/3053
[#3055]: https://github.com/DataDog/dd-agent/issues/3055
[#3059]: https://github.com/DataDog/dd-agent/issues/3059
[#3060]: https://github.com/DataDog/dd-agent/issues/3060
[#3066]: https://github.com/DataDog/dd-agent/issues/3066
[#3067]: https://github.com/DataDog/dd-agent/issues/3067
[#3069]: https://github.com/DataDog/dd-agent/issues/3069
[#3070]: https://github.com/DataDog/dd-agent/issues/3070
[#3072]: https://github.com/DataDog/dd-agent/issues/3072
[#3073]: https://github.com/DataDog/dd-agent/issues/3073
[#3074]: https://github.com/DataDog/dd-agent/issues/3074
[#3076]: https://github.com/DataDog/dd-agent/issues/3076
[#3077]: https://github.com/DataDog/dd-agent/issues/3077
[#3078]: https://github.com/DataDog/dd-agent/issues/3078
[#3079]: https://github.com/DataDog/dd-agent/issues/3079
[#3080]: https://github.com/DataDog/dd-agent/issues/3080
[#3093]: https://github.com/DataDog/dd-agent/issues/3093
[#3095]: https://github.com/DataDog/dd-agent/issues/3095
[#3096]: https://github.com/DataDog/dd-agent/issues/3096
[#3100]: https://github.com/DataDog/dd-agent/issues/3100
[#3109]: https://github.com/DataDog/dd-agent/issues/3109
[#3111]: https://github.com/DataDog/dd-agent/issues/3111
[#3116]: https://github.com/DataDog/dd-agent/issues/3116
[#3117]: https://github.com/DataDog/dd-agent/issues/3117
[#3118]: https://github.com/DataDog/dd-agent/issues/3118
[#3124]: https://github.com/DataDog/dd-agent/issues/3124
[#3125]: https://github.com/DataDog/dd-agent/issues/3125
[#3127]: https://github.com/DataDog/dd-agent/issues/3127
[#3129]: https://github.com/DataDog/dd-agent/issues/3129
[#3134]: https://github.com/DataDog/dd-agent/issues/3134
[#3140]: https://github.com/DataDog/dd-agent/issues/3140
[#3141]: https://github.com/DataDog/dd-agent/issues/3141
[#3142]: https://github.com/DataDog/dd-agent/issues/3142
[#3145]: https://github.com/DataDog/dd-agent/issues/3145
[#3148]: https://github.com/DataDog/dd-agent/issues/3148
[#3150]: https://github.com/DataDog/dd-agent/issues/3150
[#3154]: https://github.com/DataDog/dd-agent/issues/3154
[#3158]: https://github.com/DataDog/dd-agent/issues/3158
[#3160]: https://github.com/DataDog/dd-agent/issues/3160
[#3165]: https://github.com/DataDog/dd-agent/issues/3165
[#3166]: https://github.com/DataDog/dd-agent/issues/3166
[#3168]: https://github.com/DataDog/dd-agent/issues/3168
[#3169]: https://github.com/DataDog/dd-agent/issues/3169
[#3172]: https://github.com/DataDog/dd-agent/issues/3172
[#3174]: https://github.com/DataDog/dd-agent/issues/3174
[#3176]: https://github.com/DataDog/dd-agent/issues/3176
[#3180]: https://github.com/DataDog/dd-agent/issues/3180
[#3182]: https://github.com/DataDog/dd-agent/issues/3182
[#3183]: https://github.com/DataDog/dd-agent/issues/3183
[#3189]: https://github.com/DataDog/dd-agent/issues/3189
[#3193]: https://github.com/DataDog/dd-agent/issues/3193
[#3194]: https://github.com/DataDog/dd-agent/issues/3194
[#3196]: https://github.com/DataDog/dd-agent/issues/3196
[#3197]: https://github.com/DataDog/dd-agent/issues/3197
[#3206]: https://github.com/DataDog/dd-agent/issues/3206
[#3208]: https://github.com/DataDog/dd-agent/issues/3208
[#3210]: https://github.com/DataDog/dd-agent/issues/3210
[#3218]: https://github.com/DataDog/dd-agent/issues/3218
[#3220]: https://github.com/DataDog/dd-agent/issues/3220
[#3224]: https://github.com/DataDog/dd-agent/issues/3224
[#3240]: https://github.com/DataDog/dd-agent/issues/3240
[#3243]: https://github.com/DataDog/dd-agent/issues/3243
[#3244]: https://github.com/DataDog/dd-agent/issues/3244
[#3252]: https://github.com/DataDog/dd-agent/issues/3252
[#3256]: https://github.com/DataDog/dd-agent/issues/3256
[#3265]: https://github.com/DataDog/dd-agent/issues/3265
[#3272]: https://github.com/DataDog/dd-agent/issues/3272
[#3274]: https://github.com/DataDog/dd-agent/issues/3274
[#3280]: https://github.com/DataDog/dd-agent/issues/3280
[#3281]: https://github.com/DataDog/dd-agent/issues/3281
[#3287]: https://github.com/DataDog/dd-agent/issues/3287
[#3288]: https://github.com/DataDog/dd-agent/issues/3288
[#3289]: https://github.com/DataDog/dd-agent/issues/3289
[#3291]: https://github.com/DataDog/dd-agent/issues/3291
[#3293]: https://github.com/DataDog/dd-agent/issues/3293
[#3294]: https://github.com/DataDog/dd-agent/issues/3294
[#3297]: https://github.com/DataDog/dd-agent/issues/3297
[#3298]: https://github.com/DataDog/dd-agent/issues/3298
[#3300]: https://github.com/DataDog/dd-agent/issues/3300
[#3301]: https://github.com/DataDog/dd-agent/issues/3301
[#3304]: https://github.com/DataDog/dd-agent/issues/3304
[#3307]: https://github.com/DataDog/dd-agent/issues/3307
[#3310]: https://github.com/DataDog/dd-agent/issues/3310
[#3311]: https://github.com/DataDog/dd-agent/issues/3311
[#3313]: https://github.com/DataDog/dd-agent/issues/3313
[#3314]: https://github.com/DataDog/dd-agent/issues/3314
[#3315]: https://github.com/DataDog/dd-agent/issues/3315
[#3317]: https://github.com/DataDog/dd-agent/issues/3317
[#3318]: https://github.com/DataDog/dd-agent/issues/3318
[#3320]: https://github.com/DataDog/dd-agent/issues/3320
[#3326]: https://github.com/DataDog/dd-agent/issues/3326
[#3328]: https://github.com/DataDog/dd-agent/issues/3328
[#3329]: https://github.com/DataDog/dd-agent/issues/3329
[#3330]: https://github.com/DataDog/dd-agent/issues/3330
[#3331]: https://github.com/DataDog/dd-agent/issues/3331
[#3332]: https://github.com/DataDog/dd-agent/issues/3332
[#3334]: https://github.com/DataDog/dd-agent/issues/3334
[#3335]: https://github.com/DataDog/dd-agent/issues/3335
[#3339]: https://github.com/DataDog/dd-agent/issues/3339
[#3341]: https://github.com/DataDog/dd-agent/issues/3341
[#3344]: https://github.com/DataDog/dd-agent/issues/3344
[#3346]: https://github.com/DataDog/dd-agent/issues/3346
[#3348]: https://github.com/DataDog/dd-agent/issues/3348
[#3349]: https://github.com/DataDog/dd-agent/issues/3349
[#3350]: https://github.com/DataDog/dd-agent/issues/3350
[#3351]: https://github.com/DataDog/dd-agent/issues/3351
[#3356]: https://github.com/DataDog/dd-agent/issues/3356
[#3357]: https://github.com/DataDog/dd-agent/issues/3357
[#3358]: https://github.com/DataDog/dd-agent/issues/3358
[#3359]: https://github.com/DataDog/dd-agent/issues/3359
[#3364]: https://github.com/DataDog/dd-agent/issues/3364
[#3368]: https://github.com/DataDog/dd-agent/issues/3368
[#3373]: https://github.com/DataDog/dd-agent/issues/3373
[#3374]: https://github.com/DataDog/dd-agent/issues/3374
[#3375]: https://github.com/DataDog/dd-agent/issues/3375
[#3376]: https://github.com/DataDog/dd-agent/issues/3376
[#3377]: https://github.com/DataDog/dd-agent/issues/3377
[#3378]: https://github.com/DataDog/dd-agent/issues/3378
[#3383]: https://github.com/DataDog/dd-agent/issues/3383
[#3385]: https://github.com/DataDog/dd-agent/issues/3385
[#3386]: https://github.com/DataDog/dd-agent/issues/3386
[#3387]: https://github.com/DataDog/dd-agent/issues/3387
[#3390]: https://github.com/DataDog/dd-agent/issues/3390
[#3391]: https://github.com/DataDog/dd-agent/issues/3391
[#3394]: https://github.com/DataDog/dd-agent/issues/3394
[#3395]: https://github.com/DataDog/dd-agent/issues/3395
[#3399]: https://github.com/DataDog/dd-agent/issues/3399
[#3401]: https://github.com/DataDog/dd-agent/issues/3401
[#3402]: https://github.com/DataDog/dd-agent/issues/3402
[#3403]: https://github.com/DataDog/dd-agent/issues/3403
[#3404]: https://github.com/DataDog/dd-agent/issues/3404
[#3405]: https://github.com/DataDog/dd-agent/issues/3405
[#3406]: https://github.com/DataDog/dd-agent/issues/3406
[#3408]: https://github.com/DataDog/dd-agent/issues/3408
[#3409]: https://github.com/DataDog/dd-agent/issues/3409
[#3411]: https://github.com/DataDog/dd-agent/issues/3411
[#3413]: https://github.com/DataDog/dd-agent/issues/3413
[#3414]: https://github.com/DataDog/dd-agent/issues/3414
[#3415]: https://github.com/DataDog/dd-agent/issues/3415
[#3417]: https://github.com/DataDog/dd-agent/issues/3417
[#3421]: https://github.com/DataDog/dd-agent/issues/3421
[#3429]: https://github.com/DataDog/dd-agent/issues/3429
[#3443]: https://github.com/DataDog/dd-agent/issues/3443
[#3445]: https://github.com/DataDog/dd-agent/issues/3445
[#3446]: https://github.com/DataDog/dd-agent/issues/3446
[#3448]: https://github.com/DataDog/dd-agent/issues/3448
[#3449]: https://github.com/DataDog/dd-agent/issues/3449
[#3451]: https://github.com/DataDog/dd-agent/issues/3451
[#3454]: https://github.com/DataDog/dd-agent/issues/3454
[#3458]: https://github.com/DataDog/dd-agent/issues/3458
[#3460]: https://github.com/DataDog/dd-agent/issues/3460
[#3461]: https://github.com/DataDog/dd-agent/issues/3461
[#3463]: https://github.com/DataDog/dd-agent/issues/3463
[#3466]: https://github.com/DataDog/dd-agent/issues/3466
[#3467]: https://github.com/DataDog/dd-agent/issues/3467
[#3468]: https://github.com/DataDog/dd-agent/issues/3468
[#3470]: https://github.com/DataDog/dd-agent/issues/3470
[#3476]: https://github.com/DataDog/dd-agent/issues/3476
[#3477]: https://github.com/DataDog/dd-agent/issues/3477
[#3478]: https://github.com/DataDog/dd-agent/issues/3478
[#3479]: https://github.com/DataDog/dd-agent/issues/3479
[#3481]: https://github.com/DataDog/dd-agent/issues/3481
[#3483]: https://github.com/DataDog/dd-agent/issues/3483
[#3485]: https://github.com/DataDog/dd-agent/issues/3485
[#3486]: https://github.com/DataDog/dd-agent/issues/3486
[#3487]: https://github.com/DataDog/dd-agent/issues/3487
[#3488]: https://github.com/DataDog/dd-agent/issues/3488
[#3489]: https://github.com/DataDog/dd-agent/issues/3489
[#3492]: https://github.com/DataDog/dd-agent/issues/3492
[#3494]: https://github.com/DataDog/dd-agent/issues/3494
[#3497]: https://github.com/DataDog/dd-agent/issues/3497
[#3505]: https://github.com/DataDog/dd-agent/issues/3505
[#3506]: https://github.com/DataDog/dd-agent/issues/3506
[#3507]: https://github.com/DataDog/dd-agent/issues/3507
[#3508]: https://github.com/DataDog/dd-agent/issues/3508
[#3509]: https://github.com/DataDog/dd-agent/issues/3509
[#3511]: https://github.com/DataDog/dd-agent/issues/3511
[#3521]: https://github.com/DataDog/dd-agent/issues/3521
[#3523]: https://github.com/DataDog/dd-agent/issues/3523
[#3527]: https://github.com/DataDog/dd-agent/issues/3527
[#3528]: https://github.com/DataDog/dd-agent/issues/3528
[#3529]: https://github.com/DataDog/dd-agent/issues/3529
[#3532]: https://github.com/DataDog/dd-agent/issues/3532
[#3534]: https://github.com/DataDog/dd-agent/issues/3534
[#3536]: https://github.com/DataDog/dd-agent/issues/3536
[#3537]: https://github.com/DataDog/dd-agent/issues/3537
[#3538]: https://github.com/DataDog/dd-agent/issues/3538
[#3539]: https://github.com/DataDog/dd-agent/issues/3539
[#3543]: https://github.com/DataDog/dd-agent/issues/3543
[#3546]: https://github.com/DataDog/dd-agent/issues/3546
[#3547]: https://github.com/DataDog/dd-agent/issues/3547
[#3548]: https://github.com/DataDog/dd-agent/issues/3548
[#3549]: https://github.com/DataDog/dd-agent/issues/3549
[#3551]: https://github.com/DataDog/dd-agent/issues/3551
[#3553]: https://github.com/DataDog/dd-agent/issues/3553
[#3554]: https://github.com/DataDog/dd-agent/issues/3554
[#3555]: https://github.com/DataDog/dd-agent/issues/3555
[#3557]: https://github.com/DataDog/dd-agent/issues/3557
[#3563]: https://github.com/DataDog/dd-agent/issues/3563
[#3564]: https://github.com/DataDog/dd-agent/issues/3564
[#3565]: https://github.com/DataDog/dd-agent/issues/3565
[#3571]: https://github.com/DataDog/dd-agent/issues/3571
[#3574]: https://github.com/DataDog/dd-agent/issues/3574
[#3581]: https://github.com/DataDog/dd-agent/issues/3581
[#3586]: https://github.com/DataDog/dd-agent/issues/3586
[#3589]: https://github.com/DataDog/dd-agent/issues/3589
[#3596]: https://github.com/DataDog/dd-agent/issues/3596
[#3599]: https://github.com/DataDog/dd-agent/issues/3599
[#3603]: https://github.com/DataDog/dd-agent/issues/3603
[#3607]: https://github.com/DataDog/dd-agent/issues/3607
[#3608]: https://github.com/DataDog/dd-agent/issues/3608
[#3609]: https://github.com/DataDog/dd-agent/issues/3609
[#3611]: https://github.com/DataDog/dd-agent/issues/3611
[#3612]: https://github.com/DataDog/dd-agent/issues/3612
[#3614]: https://github.com/DataDog/dd-agent/issues/3614
[#3617]: https://github.com/DataDog/dd-agent/issues/3617
[#3618]: https://github.com/DataDog/dd-agent/issues/3618
[#3619]: https://github.com/DataDog/dd-agent/issues/3619
[#3620]: https://github.com/DataDog/dd-agent/issues/3620
[#3622]: https://github.com/DataDog/dd-agent/issues/3622
[#3623]: https://github.com/DataDog/dd-agent/issues/3623
[#3625]: https://github.com/DataDog/dd-agent/issues/3625
[#3629]: https://github.com/DataDog/dd-agent/issues/3629
[#3630]: https://github.com/DataDog/dd-agent/issues/3630
[#3635]: https://github.com/DataDog/dd-agent/issues/3635
[#3640]: https://github.com/DataDog/dd-agent/issues/3640
[#3641]: https://github.com/DataDog/dd-agent/issues/3641
[#3643]: https://github.com/DataDog/dd-agent/issues/3643
[#3644]: https://github.com/DataDog/dd-agent/issues/3644
[#3645]: https://github.com/DataDog/dd-agent/issues/3645
[#3648]: https://github.com/DataDog/dd-agent/issues/3648
[#3655]: https://github.com/DataDog/dd-agent/issues/3655
[#3657]: https://github.com/DataDog/dd-agent/issues/3657
[#3661]: https://github.com/DataDog/dd-agent/issues/3661
[#3663]: https://github.com/DataDog/dd-agent/issues/3663
[#3667]: https://github.com/DataDog/dd-agent/issues/3667
[#3669]: https://github.com/DataDog/dd-agent/issues/3669
[#3670]: https://github.com/DataDog/dd-agent/issues/3670
[#3674]: https://github.com/DataDog/dd-agent/issues/3674
[#3691]: https://github.com/DataDog/dd-agent/issues/3691
[#3703]: https://github.com/DataDog/dd-agent/issues/3703
[#3704]: https://github.com/DataDog/dd-agent/issues/3704
[#3711]: https://github.com/DataDog/dd-agent/issues/3711
[#3712]: https://github.com/DataDog/dd-agent/issues/3712
[#3713]: https://github.com/DataDog/dd-agent/issues/3713
[#3719]: https://github.com/DataDog/dd-agent/issues/3719
[#3723]: https://github.com/DataDog/dd-agent/issues/3723
[#3726]: https://github.com/DataDog/dd-agent/issues/3726
[@2rs2ts]: https://github.com/2rs2ts
[@AirbornePorcine]: https://github.com/AirbornePorcine
[@AntoCard]: https://github.com/AntoCard
[@CaptTofu]: https://github.com/CaptTofu
[@Carles-Figuerola]: https://github.com/Carles-Figuerola
[@DylanFrese]: https://github.com/DylanFrese
[@EdRow]: https://github.com/EdRow
[@GregBowyer]: https://github.com/GregBowyer
[@KnownSubset]: https://github.com/KnownSubset
[@MiguelMoll]: https://github.com/MiguelMoll
[@Osterjour]: https://github.com/Osterjour
[@ParthKolekar]: https://github.com/ParthKolekar
[@PedroMiguelFigueiredo]: https://github.com/PedroMiguelFigueiredo
[@Radstake]: https://github.com/Radstake
[@TheCloudlessSky]: https://github.com/TheCloudlessSky
[@Zarkantho]: https://github.com/Zarkantho
[@Zenexer]: https://github.com/Zenexer
[@a20012251]: https://github.com/a20012251
[@adriandoolittle]: https://github.com/adriandoolittle
[@aerostitch]: https://github.com/aerostitch
[@ahamilton55]: https://github.com/ahamilton55
[@alaz]: https://github.com/alaz
[@alexef]: https://github.com/alexef
[@allixsenos]: https://github.com/allixsenos
[@alz]: https://github.com/alz
[@antifuchs]: https://github.com/antifuchs
[@aoking]: https://github.com/aoking
[@arohner]: https://github.com/arohner
[@arosenhagen]: https://github.com/arosenhagen
[@arrawatia]: https://github.com/arrawatia
[@arthurnn]: https://github.com/arthurnn
[@arzarif]: https://github.com/arzarif
[@asiebert]: https://github.com/asiebert
[@avaughan89]: https://github.com/avaughan89
[@bakins]: https://github.com/bakins
[@bdharrington7]: https://github.com/bdharrington7
[@bdotdub]: https://github.com/bdotdub
[@benmccann]: https://github.com/benmccann
[@bluestix]: https://github.com/bluestix
[@bpuzon]: https://github.com/bpuzon
[@bradhe]: https://github.com/bradhe
[@brettlangdon]: https://github.com/brettlangdon
[@brianwolfe]: https://github.com/brianwolfe
[@brothhaar]: https://github.com/brothhaar
[@c960657]: https://github.com/c960657
[@cberry777]: https://github.com/cberry777
[@ccocsas]: https://github.com/ccocsas
[@charles-dyfis-net]: https://github.com/charles-dyfis-net
[@chrissnel]: https://github.com/chrissnel
[@chrissnell]: https://github.com/chrissnell
[@ckrough]: https://github.com/ckrough
[@clly]: https://github.com/clly
[@clokep]: https://github.com/clokep
[@cryptspirit]: https://github.com/cryptspirit
[@cslee00]: https://github.com/cslee00
[@darnaut]: https://github.com/darnaut
[@datadoghq]: https://github.com/datadoghq
[@dblackdblack]: https://github.com/dblackdblack
[@dcrosta]: https://github.com/dcrosta
[@diogokiss]: https://github.com/diogokiss
[@diver-in-sky]: https://github.com/diver-in-sky
[@djensen47]: https://github.com/djensen47
[@dmulter]: https://github.com/dmulter
[@donalguy]: https://github.com/donalguy
[@dougbarth]: https://github.com/dougbarth
[@dspangen]: https://github.com/dspangen
[@dturn]: https://github.com/dturn
[@ebroder]: https://github.com/ebroder
[@echohead]: https://github.com/echohead
[@ejholmes]: https://github.com/ejholmes
[@ensonik]: https://github.com/ensonik
[@eredjar]: https://github.com/eredjar
[@erkolson]: https://github.com/erkolson
[@etrepum]: https://github.com/etrepum
[@garnermccloud]: https://github.com/garnermccloud
[@generica]: https://github.com/generica
[@ghTravis]: https://github.com/ghTravis
[@glickbot]: https://github.com/glickbot
[@gphat]: https://github.com/gphat
[@graemej]: https://github.com/graemej
[@gtaylor]: https://github.com/gtaylor
[@gzysk8]: https://github.com/gzysk8
[@hamano]: https://github.com/hamano
[@handigarde]: https://github.com/handigarde
[@hjkatz]: https://github.com/hjkatz
[@host]: https://github.com/host
[@iancward]: https://github.com/iancward
[@ibwhite]: https://github.com/ibwhite
[@igor47]: https://github.com/igor47
[@igroenewold]: https://github.com/igroenewold
[@imlucas]: https://github.com/imlucas
[@ipolishchuk]: https://github.com/ipolishchuk
[@ive]: https://github.com/ive
[@jalaziz]: https://github.com/jalaziz
[@jamesandariese]: https://github.com/jamesandariese
[@jamescrowley]: https://github.com/jamescrowley
[@janeczku]: https://github.com/janeczku
[@jcapricebasho]: https://github.com/jcapricebasho
[@jcejohnson]: https://github.com/jcejohnson
[@jdavisp3]: https://github.com/jdavisp3
[@jeffwidman]: https://github.com/jeffwidman
[@jgmchan]: https://github.com/jgmchan
[@jimmystewpot]: https://github.com/jimmystewpot
[@jkoppe]: https://github.com/jkoppe
[@jkorzekwa-atlassian]: https://github.com/jkorzekwa-atlassian
[@jnewland]: https://github.com/jnewland
[@joelvanvelden]: https://github.com/joelvanvelden
[@joewilliams]: https://github.com/joewilliams
[@jonaf]: https://github.com/jonaf
[@jonchiu]: https://github.com/jonchiu
[@joningle]: https://github.com/joningle
[@joshk0]: https://github.com/joshk0
[@jpittis]: https://github.com/jpittis
[@jraede]: https://github.com/jraede
[@jslatts]: https://github.com/jslatts
[@jstotzs]: https://github.com/jstotzs
[@jzoldak]: https://github.com/jzoldak
[@kennydo]: https://github.com/kennydo
[@kzw]: https://github.com/kzw
[@lattwood]: https://github.com/lattwood
[@leifwalsh]: https://github.com/leifwalsh
[@leucos]: https://github.com/leucos
[@loris]: https://github.com/loris
[@lowl4tency]: https://github.com/lowl4tency
[@markine]: https://github.com/markine
[@mastrolinux]: https://github.com/mastrolinux
[@matlockx]: https://github.com/matlockx
[@mattrobenolt]: https://github.com/mattrobenolt
[@mausch]: https://github.com/mausch
[@mberner-ch]: https://github.com/mberner-ch
[@mcclurmc]: https://github.com/mcclurmc
[@mdelaney]: https://github.com/mdelaney
[@mderomph-coolblue]: https://github.com/mderomph-coolblue
[@michalyao]: https://github.com/michalyao
[@micktwomey]: https://github.com/micktwomey
[@mike-lerch]: https://github.com/mike-lerch
[@mikekap]: https://github.com/mikekap
[@millerdev]: https://github.com/millerdev
[@mms-gianni]: https://github.com/mms-gianni
[@mooney6023]: https://github.com/mooney6023
[@morskoyzmey]: https://github.com/morskoyzmey
[@mpidlisnyi]: https://github.com/mpidlisnyi
[@mtougeron]: https://github.com/mtougeron
[@mutemule]: https://github.com/mutemule
[@n0ts]: https://github.com/n0ts
[@nambrosch]: https://github.com/nambrosch
[@nfo]: https://github.com/nfo
[@nwillems]: https://github.com/nwillems
[@nyanshak]: https://github.com/nyanshak
[@obi11235]: https://github.com/obi11235
[@oeuftete]: https://github.com/oeuftete
[@ojongerius]: https://github.com/ojongerius
[@ordenull]: https://github.com/ordenull
[@oremj]: https://github.com/oremj
[@orenmazor]: https://github.com/orenmazor
[@ovaistariq]: https://github.com/ovaistariq
[@ovesh]: https://github.com/ovesh
[@pabrahamsson]: https://github.com/pabrahamsson
[@parkr]: https://github.com/parkr
[@patrickbcullen]: https://github.com/patrickbcullen
[@patricknelson]: https://github.com/patricknelson
[@pbitty]: https://github.com/pbitty
[@pbrisbin]: https://github.com/pbrisbin
[@pfmooney]: https://github.com/pfmooney
[@pidah]: https://github.com/pidah
[@polynomial]: https://github.com/polynomial
[@ptinsley]: https://github.com/ptinsley
[@rdxiang]: https://github.com/rdxiang
[@rhwlo]: https://github.com/rhwlo
[@ricky26]: https://github.com/ricky26
[@rl-0x0]: https://github.com/rl-0x0
[@ronaldbradford]: https://github.com/ronaldbradford
[@ross]: https://github.com/ross
[@scottbessler]: https://github.com/scottbessler
[@scottgeary]: https://github.com/scottgeary
[@sethp-jive]: https://github.com/sethp-jive
[@sha1sum]: https://github.com/sha1sum
[@shamada-kuuluu]: https://github.com/shamada-kuuluu
[@shashiranjan84]: https://github.com/shashiranjan84
[@sirlantis]: https://github.com/sirlantis
[@sj26]: https://github.com/sj26
[@skingry]: https://github.com/skingry
[@slushpupie]: https://github.com/slushpupie
[@sophaskins]: https://github.com/sophaskins
[@squaresurf]: https://github.com/squaresurf
[@ssbarnea]: https://github.com/ssbarnea
[@steeve]: https://github.com/steeve
[@stefan-mees]: https://github.com/stefan-mees
[@stonith]: https://github.com/stonith
[@subuk]: https://github.com/subuk
[@takus]: https://github.com/takus
[@tarvip]: https://github.com/tarvip
[@tebriel]: https://github.com/tebriel
[@theckman]: https://github.com/theckman
[@theojulienne]: https://github.com/theojulienne
[@therc]: https://github.com/therc
[@tliakos]: https://github.com/tliakos
[@toksvaeth]: https://github.com/toksvaeth
[@tomduckering]: https://github.com/tomduckering
[@tschellhorn]: https://github.com/tschellhorn
[@ulich]: https://github.com/ulich
[@urosgruber]: https://github.com/urosgruber
[@walkeran]: https://github.com/walkeran
[@warnerpr-cyan]: https://github.com/warnerpr-cyan
[@wyaeld]: https://github.com/wyaeld
[@xkrt]: https://github.com/xkrt
[@yannrouillard]: https://github.com/yannrouillard
[@yenif]: https://github.com/yenif
[@yyamano]: https://github.com/yyamano
[@zachradtka]: https://github.com/zachradtka
[@zdannar]: https://github.com/zdannar
