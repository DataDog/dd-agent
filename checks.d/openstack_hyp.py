
# stdlib
import os
from datetime import datetime, timedelta
from urlparse import urljoin

# project
from checks import AgentCheck
from util import get_hostname

# 3p
import requests
import simplejson as json

SOURCE_TYPE = 'openstack'

DEFAULT_KEYSTONE_API_VERSION = 'v3'
DEFAULT_NOVA_API_VERSION = 'v2.1'
DEFAULT_NEUTRON_API_VERSION = 'v2.0'

DEFAULT_API_REQUEST_TIMEOUT = 5 # seconds

NOVA_HYPERVISOR_METRICS = [
    'current_workload',
    'disk_available_least',
    'free_disk_gb',
    'free_ram_mb',
    'local_gb',
    'local_gb_used',
    'memory_mb',
    'memory_mb_used',
    'running_vms',
    'vcpus',
    'vcpus_used',
]

NOVA_SERVER_METRICS = [
    "hdd_errors",
    "hdd_read",
    "hdd_read_req",
    "hdd_write",
    "hdd_write_req",
    "memory",
    "memory-actual",
    "memory-rss",
    "cpu0_time",

    "vda_errors",
    "vda_read",
    "vda_read_req",
    "vda_write",
    "vda_write_req"
]

NOVA_SERVER_INTERFACE_SEGMENTS = ['_rx', '_tx']

PROJECT_METRICS = dict([
    ("maxImageMeta", "max_image_meta"),
    ("maxPersonality", "max_personality"),
    ("maxPersonalitySize", "max_personality_size"),
    ("maxSecurityGroupRules", "max_security_group_rules"),
    ("maxSecurityGroups", "max_security_groups"),
    ("maxServerMeta", "max_server_meta"),
    ("maxTotalCores", "max_total_cores"),
    ("maxTotalFloatingIps", "max_total_floating_ips"),
    ("maxTotalInstances", "max_total_instances"),
    ("maxTotalKeypairs", "max_total_keypairs"),
    ("maxTotalRAMSize", "max_total_ram_size"),

    ("totalImageMetaUsed", "total_image_meta_used"),
    ("totalPersonalityUsed", "total_personality_used"),
    ("totalPersonalitySizeUsed", "total_personality_size_used"),
    ("totalSecurityGroupRulesUsed", "total_security_group_rules_used"),
    ("totalSecurityGroupsUsed", "total_security_groups_used"),
    ("totalServerMetaUsed", "total_server_meta_used"),
    ("totalCoresUsed", "total_cores_used"),
    ("totalFloatingIpsUsed", "total_floating_ips_used"),
    ("totalInstancesUsed", "total_instances_used"),
    ("totalKeypairsUsed", "total_keypairs_used"),
    ("totalRAMUsed", "total_ram_used"),
])

class OpenStackAuthFailure(Exception):
    pass

class InstancePowerOffFailure(Exception):
    pass

class IncompleteConfig(Exception):
    pass

class IncompleteAuthScope(IncompleteConfig):
    pass

class IncompleteIdentity(IncompleteConfig):
    pass

class BadCredentials(Exception):
    pass

class MissingEndpoint(Exception):
    pass

class MissingNovaEndpoint(MissingEndpoint):
    pass

class MissingNeutronEndpoint(MissingEndpoint):
    pass

class KeystoneUnreachable(Exception):
    pass


class OpenStackCheck(AgentCheck):
    CACHE_TTL = {
        "aggregates": 300, # seconds
        "physical_hosts": 300,
        "hypervisors": 300
    }

    FETCH_TIME_ACCESSORS = {
        "aggregates": "_last_aggregate_fetch_time",
        "physical_hosts": "_last_host_fetch_time",
        "hypervisors": "_last_hypervisor_fetch_time"

    }

    HYPERVISOR_STATE_UP = 'up'
    HYPERVISOR_STATE_DOWN = 'down'
    NETWORK_STATE_UP = 'UP'

    NETWORK_API_SC = 'openstack.neutron.api.up'
    COMPUTE_API_SC = 'openstack.nova.api.up'
    IDENTITY_API_SC = 'openstack.keystone.api.up'

    # Service checks for individual hypervisors and networks
    HYPERVISOR_SC = 'openstack.nova.hypervisor.up'
    NETWORK_SC = 'openstack.neutron.network.up'


    HYPERVISOR_CACHE_EXPIRY = 120 # seconds

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        self._ssl_verify = init_config.get("ssl_verify", True)
        self.keystone_server_url = init_config.get("keystone_server_url")
        if not self.keystone_server_url:
            raise IncompleteConfig()

        ### Cache some things between runs for values that change rarely
        self._aggregate_list = None

        # Mapping of check instances to associated OpenStack project scopes
        self.instance_map = {}

        # Mapping of Nova-managed servers to tags
        self.external_host_tags = {}

    def _make_request_with_auth_fallback(self, url, headers=None, verify=True, params=None):
        """
        Generic request handler for OpenStack API requests
        Raises specialized Exceptions for commonly encountered error codes
        """
        try:
            resp = requests.get(url, headers=headers, verify=verify, params=params, timeout=DEFAULT_API_REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            if resp.status_code == 401:
                self.log.info('Need to reauthenticate before next check')

                # Delete the scope, we'll populate a new one on the next run for this instance
                self.delete_current_scope()
            elif resp.status_code == 409:
                raise InstancePowerOffFailure()
            else:
                raise

        return resp.json()

    ### Network
    def get_neutron_endpoint_from_catalog(self, catalog):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching the Neutron service
        Sends a CRITICAL service check when none are found registered in the Catalog
        """
        match = 'neutron'

        neutron_endpoint = None
        for entry in catalog:
            if entry['name'] == match:
                valid_endpoints = {}
                for ep in entry['endpoints']:
                    interface = ep.get('interface','')
                    if interface in ['public', 'internal']:
                        valid_endpoints[interface] = ep['url']

                if valid_endpoints:
                    # Favor public endpoints over internal
                    neutron_endpoint = valid_endpoints.get("public",
                                        valid_endpoints.get("internal"))
                    break
        else:
            raise MissingNeutronEndpoint()

        return neutron_endpoint


    def get_network_stats(self, neutron_endpoint, domain_token):
        """
        Collect stats for all reachable networks
        """

        # FIXME: (aaditya) Check all networks defaults to true until we can reliably assign agents to networks to monitor
        if self.init_config.get('check_all_networks', True):
            network_ids = list(set(self.get_all_network_ids(neutron_endpoint, domain_token)) - set(self.init_config.get('exclude_network_ids', [])))
        else:
            network_ids = self.init_config.get('network_ids', [])

        if not network_ids:
            self.warning("Your check is not configured to monitor any networks.\n" +
                         "Please list `network_ids` under your init_config")

        for nid in network_ids:
            self.get_stats_for_single_network(nid, neutron_endpoint, domain_token)

    def get_all_network_ids(self, neutron_endpoint, domain_token):
        url = '{0}/{1}/networks'.format(neutron_endpoint, DEFAULT_NEUTRON_API_VERSION)
        headers = {'X-Auth-Token': domain_token}

        network_ids = []
        try:
            net_details = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
            for network in net_details['networks']:
                network_ids.append(network['id'])
        except Exception as e:
            self.warning('Unable to get the list of all network ids: {0}'.format(str(e)))
        return network_ids

    def get_stats_for_single_network(self, network_id, neutron_endpoint, domain_token):
        url = '{0}/{1}/networks/{2}'.format(neutron_endpoint, DEFAULT_NEUTRON_API_VERSION, network_id)
        headers = {'X-Auth-Token': domain_token}
        net_details = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)

        service_check_tags = ['network:{0}'.format(network_id)]

        network_name = net_details.get('network', {}).get('name')
        if network_name is not None:
            service_check_tags.append('network_name:{0}'.format(network_name))

        tenant_id = net_details.get('network', {}).get('tenant_id')
        if tenant_id is not None:
            service_check_tags.append('tenant_id:{0}'.format(tenant_id))

        if net_details.get('network', {}).get('admin_state_up'):
            self.service_check(self.NETWORK_SC, AgentCheck.OK, tags=service_check_tags)
        else:
            self.service_check(self.NETWORK_SC, AgentCheck.CRITICAL, tags=service_check_tags)
    ###

    ### Compute

    def get_nova_endpoint_v2(self, json_resp, nova_api_version=None):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching the Nova service with the requested version
        Sends a CRITICAL service check when no viable candidates are found in the Catalog
        """
        nova_version = nova_api_version or DEFAULT_NOVA_API_VERSION
        catalog = json_resp.get('token', {}).get('catalog', [])

        nova_match = 'novav21' if nova_version == 'v2.1' else 'nova'

        for entry in catalog:
            if entry['name'] == nova_match:
                # Collect any endpoints on the public or internal interface
                valid_endpoints = {}
                for ep in entry['endpoints']:
                    interface = ep.get('interface','')
                    if interface in ['public', 'internal']:
                        valid_endpoints[interface] = ep['url']

                if valid_endpoints:
                    # Favor public endpoints over internal
                    nova_endpoint = valid_endpoints.get("public",
                                        valid_endpoints.get("internal"))

                    return nova_endpoint
        else:
            raise MissingNovaEndpoint()

    def _parse_uptime_string(self, uptime):
        """ Parse u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n' """
        uptime = uptime.strip()
        load_averages = uptime[uptime.find('load average:'):].split(':')[1].split(',')
        uptime_sec = uptime.split(',')[0]

        return {
            'loads': map(float, load_averages),
            'uptime_sec': uptime_sec
        }


    def get_all_hypervisor_ids_v2(self, project_token, nova_endpoint, filter_by_host=None):
        headers = {'X-Auth-Token': project_token}
        url = '{0}/os-hypervisors'.format(nova_endpoint)
        hypervisor_ids = []
        try:
            self.log.debug("Requesting hypervisor ids from %s", url)
            hv_list = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
            self.log.debug("Obtained hypervisor list %s", hv_list)
            for hv in hv_list['hypervisors']:
                if filter_by_host and hv['hypervisor_hostname'] == filter_by_host:
                    # Assume one-one relationship between hypervisor and host, return the 1st found
                    return [hv['id']]

                hypervisor_ids.append(hv['id'])
        except Exception as e:
            self.warning('Unable to get the list of all hypervisors: {0}'.format(str(e)))

        return hypervisor_ids


    def get_all_hypervisor_ids(self, filter_by_host=None):
        nova_version = self.init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)
        if nova_version == "v2.1":
            url = '{0}/os-hypervisors'.format(self.get_nova_endpoint())
            headers = {'X-Auth-Token': self.get_auth_token()}

            hypervisor_ids = []
            try:
                hv_list = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
                for hv in hv_list['hypervisors']:
                    if filter_by_host and hv['hypervisor_hostname'] == filter_by_host:
                        # Assume one-one relationship between hypervisor and host, return the 1st found
                        return [hv['id']]

                    hypervisor_ids.append(hv['id'])
            except Exception as e:
                self.warning('Unable to get the list of all hypervisors: {0}'.format(str(e)))

            return hypervisor_ids
        else:
            if not self.init_config.get("hypervisor_ids"):
                self.warning("Nova API v2 requires admin privileges to index hypervisors. " +
                             "Please specify the hypervisor you wish to monitor under the `hypervisor_ids` section")
                return []
            return self.init_config.get("hypervisor_ids")

    def get_all_aggregate_hypervisors(self, project_token, nova_endpoint):
        url = '{0}/os-aggregates'.format(nova_endpoint)
        headers = {'X-Auth-Token': project_token}

        hypervisor_aggregate_map = {}
        try:
            aggregate_list = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
            for v in aggregate_list['aggregates']:
                for host in v['hosts']:
                    hypervisor_aggregate_map[host] = {
                        'aggregate': v['name'],
                        'availability_zone': v['availability_zone']
                    }

        except Exception as e:
            self.warning('Unable to get the list of aggregates: {0}'.format(str(e)))

        return hypervisor_aggregate_map

    def get_uptime_for_single_hypervisor(self, hyp_id, project_token, nova_endpoint):
        url = '{0}/os-hypervisors/{1}/uptime'.format(nova_endpoint, hyp_id)
        headers = {'X-Auth-Token': project_token}

        resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
        uptime = resp['hypervisor']['uptime']
        return self._parse_uptime_string(uptime)

    def get_stats_for_single_hypervisor(self, hyp_id, project_token, nova_endpoint, host_tags=None):
        url = '{0}/os-hypervisors/{1}'.format(nova_endpoint, hyp_id)
        headers = {'X-Auth-Token': project_token}
        resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
        hyp = resp['hypervisor']
        host_tags = host_tags or []
        tags = [
            'hypervisor:{0}'.format(hyp['hypervisor_hostname']),
            'hypervisor_id:{0}'.format(hyp['id']),
            'virt_type:{0}'.format(hyp['hypervisor_type'])
        ]
        tags.extend(host_tags)

        try:
            uptime = self.get_uptime_for_single_hypervisor(hyp['id'], project_token, nova_endpoint)
        except Exception as e:
            self.warning('Unable to get uptime for hypervisor {0}: {1}'.format(hyp['id'], str(e)))
            uptime = {}

        hyp_state = hyp.get('state', None)
        if hyp_state is None:
            try:
                # Fall back for pre Nova v2.1 to the uptime response
                if uptime.get('uptime_sec', 0) > 0:
                    hyp_state = self.HYPERVISOR_STATE_UP
                else:
                    hyp_state = self.HYPERVISOR_STATE_DOWN
            except Exception:
                # This creates the AgentCheck.UNKNOWN state
                pass

        if hyp_state is None:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.UNKNOWN,
                               tags=tags)
        elif hyp_state != self.HYPERVISOR_STATE_UP:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.CRITICAL,
                               tags=tags)
        else:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.OK,
                               tags=tags)

        for label, val in hyp.iteritems():
            if label in NOVA_HYPERVISOR_METRICS:
                metric_label = "openstack.nova.{0}".format(label)
                self.gauge(metric_label, val, tags=tags)

        load_averages = uptime.get("loads")
        if load_averages is not None:
            assert len(load_averages) == 3
            for i, avg in enumerate([1, 5, 15]):
                self.gauge('openstack.nova.hypervisor_load.{0}'.format(avg), load_averages[i], tags=tags)

    def get_all_server_ids(self, project_token, nova_endpoint, filter_by_host=None):
        query_params = {}
        if filter_by_host:
            query_params["host"] = filter_by_host

        url = '{0}/servers'.format(nova_endpoint)
        headers = {'X-Auth-Token': project_token}

        server_ids = []
        try:
            self.log.debug("Requesting servers from url %s", url)
            resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify, params=query_params)

            server_ids = [s['id'] for s in resp['servers']]
        except Exception as e:
            self.warning('Unable to get the list of all servers: {0}'.format(str(e)))

        return server_ids

    def get_stats_for_single_server(self, server_id, project_token, nova_endpoint, tags=None):
        def _is_valid_metric(label):
            return label in NOVA_SERVER_METRICS or any(seg in label for seg in NOVA_SERVER_INTERFACE_SEGMENTS)

        url = '{0}/servers/{1}/diagnostics'.format(nova_endpoint, server_id)
        headers = {'X-Auth-Token': project_token}
        server_stats = {}

        try:
            server_stats = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
        except InstancePowerOffFailure:
            self.warning("Server %s is powered off and cannot be monitored" % server_id)
        except Exception as e:
            self.warning("Unknown error when monitoring %s : %s" % (server_id, e))

        if server_stats:
            tags = tags or []
            for st in server_stats:
                if _is_valid_metric(st):
                    self.gauge("openstack.nova.server.{0}".format(st.replace("-", "_")), server_stats[st], tags=tags, hostname=server_id)

    ###

    ### Cache util
    def _is_expired(self, entry):
        assert entry in ["aggregates", "physical_hosts", "hypervisors"]
        ttl = self.CACHE_TTL.get(entry)
        last_fetch_time = getattr(self, self.FETCH_TIME_ACCESSORS.get(entry))
        return datetime.now() - last_fetch_time > timedelta(seconds=ttl)

    def _get_and_set_aggregate_list(self, project_token, nova_endpoint):
        if not self._aggregate_list or self._is_expired("aggregates"):
            self._aggregate_list = self.get_all_aggregate_hypervisors(project_token, nova_endpoint)
            self._last_aggregate_fetch_time = datetime.now()

        return self._aggregate_list
    ###

    def _send_api_service_checks(self, instance_scope):
        # Nova
        headers = {"X-Auth-Token": instance_scope.auth_token}

        try:
            requests.get(instance_scope.service_catalog.nova_endpoint, headers=headers, verify=self._ssl_verify, timeout=DEFAULT_API_REQUEST_TIMEOUT)
            self.service_check(self.COMPUTE_API_SC, AgentCheck.OK, tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")])
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self.service_check(self.COMPUTE_API_SC, AgentCheck.CRITICAL, tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")])

        # Neutron
        try:
            requests.get(instance_scope.service_catalog.neutron_endpoint, headers=headers, verify=self._ssl_verify, timeout=DEFAULT_API_REQUEST_TIMEOUT)
            self.service_check(self.NETWORK_API_SC, AgentCheck.OK, tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")])
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self.service_check(self.NETWORK_API_SC, AgentCheck.CRITICAL, tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")])

    def get_project_scoped_token(self, project_id, domain_id, user, password):
        identity = {
            "methods": ["password"],
            "password": {
                "user": {"name": user, "password": password, "domain": {"id": domain_id}}
            }
        }
        payload = {"auth": {"scope": {"project": {"id": project_id}}, "identity": identity}}
        auth_url = urljoin(
            self.keystone_server_url,
            "{0}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION)
        )
        headers = {'Content-Type': 'application/json'}

        auth_resp = requests.post(
            auth_url,
            headers=headers,
            data=json.dumps(payload), verify=self._ssl_verify, timeout=DEFAULT_API_REQUEST_TIMEOUT
        )

        auth_resp.raise_for_status()
        auth_token = auth_resp.headers.get('X-Subject-Token')
        nova_endpoint = self.get_nova_endpoint_v2(auth_resp.json(), self.init_config.get("nova_api_version"))
        if self.init_config.get("append_tenant_id"):
            nova_endpoint = urljoin(
                os.path.join(nova_endpoint, ''),
                project_id
            )
        return auth_token, nova_endpoint

    def get_domain_scoped_token(self, user, password, domain_id):

        identity = {
            "methods": ["password"],
            "password": {
                "user": {"name": user, "password": password, "domain": {"id": domain_id}}
            }
        }
        payload = {"auth": {"scope": {"domain": {"id": domain_id}}, "identity": identity}}
        auth_url = urljoin(
            self.keystone_server_url,
            "{0}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION)
        )
        headers = {'Content-Type': 'application/json'}

        auth_resp = requests.post(auth_url, headers=headers, data=json.dumps(payload), verify=self._ssl_verify, timeout=DEFAULT_API_REQUEST_TIMEOUT)
        auth_resp.raise_for_status()

        auth_token = auth_resp.headers.get('X-Subject-Token')
        user_id = auth_resp.json()['token']['user']['id']
        neutron_endpoint = self.get_neutron_endpoint_from_catalog(auth_resp.json()["token"]["catalog"])

        return auth_token, user_id, neutron_endpoint

    def get_projects_for_user(self, auth_token, user_id):
        keystone_server_url = self.keystone_server_url
        url = "{0}/{1}/users/{2}/projects".format(
            keystone_server_url, DEFAULT_KEYSTONE_API_VERSION, user_id,
        )
        headers = {'X-Auth-Token': auth_token}

        projects = []
        try:
            projects = self._make_request_with_auth_fallback(url, headers)
        except Exception as e:
            self.warning('Unable to get the list of all project ids: {0}'.format(str(e)))

        return projects["projects"]

    def check(self, instance):
        domain_id = instance.get("admin_domain_id")
        auth = instance.get("auth")

        admin_token, admin_user_id, neutron_endpoint = self.get_domain_scoped_token(auth["user"], auth["password"], domain_id)
        if not admin_token:
            raise BadCredentials
        if not domain_id:
            self.log("Please specify a domain id under instances.")
            raise IncompleteConfig

        try:
            # Only monitor projects that we are users of
            projects = self.get_projects_for_user(admin_token, admin_user_id)
            for project in projects:
                if project["domain_id"] != domain_id:
                    # Assume we don't have permissions for this project and skip it
                    self.log.debug("Skipping project %s because it's outside our domain", project['id'])
                    continue

                if not project["enabled"]:
                    self.log.debug("Skipping project %s because it's not enabled", project['id'])
                    continue

                project_token, nova_endpoint = self.get_project_scoped_token(
                    project['id'], domain_id, auth["user"], auth["password"]
                )
                self.log.debug("Project auth token for project %s is %s", project['id'], project_token)
                self.log.debug("Nova endpoint for project %s is %s", project['id'], nova_endpoint)
                hyp = self.get_local_hypervisor_v2(project_token, nova_endpoint)
                host_tags = self._get_tags_for_host(project_token, nova_endpoint)

                if hyp:
                    self.get_stats_for_single_hypervisor(hyp, project_token, nova_endpoint, host_tags=host_tags)
                else:
                    self.warning("Couldn't get hypervisor to monitor for host: %s" % self.get_my_hostname())

                # Restrict monitoring to non-excluded servers
                excluded_server_ids = self.init_config.get("exclude_server_ids", [])
                servers = self.get_servers_managed_by_hypervisor(project_token, nova_endpoint)
                servers = list(set(servers) - set(excluded_server_ids))

                for sid in servers:
                    server_tags = ["tenant_id:%s" % project['id'], "hypervisor_host:%s" % self.get_my_hostname()]
                    self.external_host_tags[sid] = host_tags + server_tags
                    self.get_stats_for_single_server(sid, project_token, nova_endpoint, tags=server_tags)

                self.external_host_tags[self.get_my_hostname()] = host_tags

            # For now, monitor all networks
            self.get_network_stats(neutron_endpoint, admin_token)

        except IncompleteConfig as e:
            if isinstance(e, IncompleteAuthScope):
                self.warning("""Please specify the auth scope via the `auth_scope` variable in your init_config.\n
                             The auth_scope should look like: \n
                            {'project': {'name': 'my_project', 'domain': {'id': 'my_domain_id'}}}\n
                            OR\n
                            {'project': {'id': 'my_project_id'}}
                             """)
            elif isinstance(e, IncompleteIdentity):
                self.warning("Please specify the user via the `user` variable in your init_config.\n" +
                             "This is the user you would use to authenticate with Keystone v3 via password auth.\n" +
                             "The user should look like: {'password': 'my_password', 'name': 'my_name', 'domain': {'id': 'my_domain_id'}}")
            else:
                self.warning("Configuration Incomplete! Check your openstack.yaml file")


    #### Local Info accessors
    def get_local_hypervisor(self):
        """
        Returns the hypervisor running on this host, and assumes a 1-1 between host and hypervisor
        """
        # Look up hypervisors available filtered by my hostname
        host = self.get_my_hostname()
        hyp = self.get_all_hypervisor_ids(filter_by_host=host)
        if hyp:
            return hyp[0]

    def get_local_hypervisor_v2(self, project_token, nova_endpoint):
        """
        Returns the hypervisor running on this host, and assumes a 1-1 between host and hypervisor
        """
        # Look up hypervisors available filtered by my hostname
        host = self.get_my_hostname()
        hyp = self.get_all_hypervisor_ids_v2(project_token, nova_endpoint, filter_by_host=host)
        if hyp:
            return hyp[0]

    def get_my_hostname(self):
        """
        Returns a best guess for the hostname registered with OpenStack for this host
        """
        return self.init_config.get("os_host") or get_hostname(self.agentConfig)

    def get_servers_managed_by_hypervisor(self, project_token, nova_endpoint):
        return self.get_all_server_ids(project_token, nova_endpoint, filter_by_host=self.get_my_hostname())

    def _get_tags_for_host(self, project_token, nova_endpoint):
        hostname = self.get_my_hostname()

        tags = []
        if hostname in self._get_and_set_aggregate_list(project_token, nova_endpoint):
            tags.append('aggregate:{0}'.format(self._aggregate_list[hostname]['aggregate']))
            # Need to check if there is a value for availability_zone because it is possible to have an aggregate without an AZ
            if self._aggregate_list[hostname]['availability_zone']:
                tags.append('availability_zone:{0}'.format(self._aggregate_list[hostname]['availability_zone']))
        else:
            self.log.info('Unable to find hostname %s in aggregate list. Assuming this host is unaggregated', hostname)

        return tags

    ### For attaching tags to hosts that are not the host running the agent

    def get_external_host_tags(self):
        """ Returns a list of tags for every guest server that is detected by the OpenStack
        integration.
        List of pairs (hostname, list_of_tags)
        """
        self.log.info("Collecting external_host_tags now")
        external_host_tags = []
        for k,v in self.external_host_tags.iteritems():
            external_host_tags.append((k, {SOURCE_TYPE: v}))

        self.log.debug("Sending external_host_tags: %s", external_host_tags)
        return external_host_tags
