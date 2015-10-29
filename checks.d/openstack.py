# stdlib
from datetime import datetime, timedelta
import json
import socket

# project
from checks import AgentCheck

# 3p
import requests

SOURCE_TYPE = 'openstack'

DEFAULT_KEYSTONE_API_VERSION = 'v3'
DEFAULT_NOVA_API_VERSION = 'v2.1'
DEFAULT_NEUTRON_API_VERSION = 'v2.0'


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

PROJECT_METRICS = [
    "maxImageMeta",
    "maxPersonality",
    "maxPersonalitySize",
    "maxSecurityGroupRules",
    "maxSecurityGroups",
    "maxServerMeta",
    "maxTotalCores",
    "maxTotalFloatingIps",
    "maxTotalInstances",
    "maxTotalKeypairs",
    "maxTotalRAMSize",

    "totalImageMetaUsed",
    "totalPersonalityUsed",
    "totalPersonalitySizeUsed",
    "totalSecurityGroupRulesUsed",
    "totalSecurityGroupsUsed",
    "totalServerMetaUsed",
    "totalCoresUsed",
    "totalFloatingIpsUsed",
    "totalInstancesUsed",
    "totalKeypairsUsed",
    "totalRAMUsed"
]

class OpenstackAuthFailure(Exception):
    pass

class InstancePowerOffFailure(Exception):
    pass

class IncompleteConfig(Exception): pass
class IncompleteAuthScope(IncompleteConfig): pass
class IncompleteIdentity(IncompleteConfig): pass


class OpenStackProjectScope(object):
    """
    Container class for a single project's authorization scope
    Embeds the auth token to be included with API requests, and refreshes
    the token on expiry (TODO)
    """
    def __init__(self, auth_token, auth_scope, service_catalog):
        self.auth_token = auth_token

        # Store some identifiers for this project
        self.project_name = auth_scope["project"].get("name")
        self.domain_id = auth_scope["project"].get("domain", {}).get("id")
        self.tenant_id = auth_scope["project"].get("id")
        self.service_catalog = service_catalog

    @classmethod
    def from_config(cls, init_config, instance_config):
        keystone_server_url = init_config.get("keystone_server_url")
        ssl_verify = init_config.get("ssl_verify", False)
        nova_api_version = init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)

        auth_scope = cls.get_auth_scope(instance_config)
        identity = cls.get_user_identity(instance_config)

        auth_resp = cls.request_auth_token(auth_scope, identity, keystone_server_url, ssl_verify)
        auth_token = auth_resp.headers.get('X-Subject-Token')

        service_catalog = KeystoneCatalog.from_auth_response(
            auth_resp.json(), nova_api_version
        )

        # (NOTE): aaditya
        # In some cases, the nova url is returned without the tenant id suffixed
        # e.g. http://172.0.0.1:8774 rather than http://172.0.0.1:8774/<tenant_id>
        # It is still unclear when this happens, but for now the user can configure
        # `append_tenant_id` to manually add this suffix for downstream requests
        if instance_config.get("append_tenant_id", False):
            t_id = auth_scope["project"].get("id")

            assert t_id and t_id not in service_catalog.nova_endpoint,\
                """Incorrect use of append_tenant_id, please inspect the service catalog response of your Identity server.
                   You may need to disable this flag if your Nova service url contains the tenant_id already"""

            service_catalog.nova_endpoint += "/{0}".format(t_id)

        return cls(auth_token, auth_scope, service_catalog)

    @classmethod
    def get_auth_scope(cls, instance_config):
        """
        Parse authorization scope out of init_config

        To guarantee a uniquely identifiable scope, expects either:
        {'project': {'name': 'my_project', 'domain': {'id': 'my_domain_id'}}}
        OR
        {'project': {'id': 'my_project_id'}}
        """
        auth_scope = instance_config.get('auth_scope')
        if not auth_scope or not auth_scope.get('project'):
            raise IncompleteAuthScope

            # TODO : move warnings to outer scope
            # self.warning("""Please specify the auth scope via the `auth_scope` variable in your init_config.\n
            #              The auth_scope should look like: \n
            #             {'project': {'name': 'my_project', 'domain': {'id': 'my_domain_id'}}}\n
            #             OR\n
            #             {'project': {'id': 'my_project_id'}}
            #              """)
            # raise IncompleteConfig

        if auth_scope['project'].get('name'):
            # We need to add a domain scope to avoid name clashes. Search for one. If not raise IncompleteConfig
            if not auth_scope['project'].get('domain', {}).get('id'):
                raise IncompleteAuthScope
        else:
            # Assume a unique project id has been given
            if not auth_scope['project'].get('id'):
                raise IncompleteAuthScope

        # TODO: Move debug log to outer scope
        # self.log.debug("Parsed authorization scope: %s", auth_scope)
        return auth_scope

    @classmethod
    def get_user_identity(cls, instance_config):
        """
        Parse user identity out of init_config

        To guarantee a uniquely identifiable user, expects
        {"user": {"name": "my_username", "password": "my_password",
                  "domain": {"id": "my_domain_id"}
                  }
        }
        """
        user = instance_config.get('user')
        if not user\
                or not user.get('name')\
                or not user.get('password')\
                or not user.get("domain")\
                or not user.get("domain").get("id"):

            raise IncompleteIdentity
            # TODO : move warnings to outer scope
            # self.warning("Please specify the user via the `user` variable in your init_config.\n" +
            #              "This is the user you would use to authenticate with Keystone v3 via password auth.\n" +
            #              "The user should look like: {'password': 'my_password', 'name': 'my_name', 'domain': {'id': 'my_domain_id'}}")
            # raise IncompleteConfig

        identity = {
            "methods": ['password'],
            "password": {"user": user}
        }
        # TODO: Move debug log to outer scope
        # self.log.debug("Identity: %s", identity)
        return identity

    @classmethod
    def request_auth_token(cls, auth_scope, identity, keystone_server_url, ssl_verify):
        payload = {"auth": {"scope": auth_scope, "identity": identity}}
        auth_url = "{0}/{1}/auth/tokens".format(keystone_server_url, DEFAULT_KEYSTONE_API_VERSION)
        headers = {'Content-Type': 'application/json'}

        resp = requests.post(auth_url, headers=headers, data=json.dumps(payload), verify=ssl_verify)
        resp.raise_for_status()

        return resp.headers.get('X-Subject-Token')


class KeystoneCatalog(object):
    """
    A registry of services, scoped to the project, returned by the identity server
    Contains parsers for retrieving service endpoints from the server auth response
    """
    def __init__(self, nova_endpoint, neutron_endpoint):
        self.nova_endpoint = nova_endpoint
        self.neutron_endpoint = neutron_endpoint

    @classmethod
    def from_auth_response(cls, json_response, nova_api_version):
        return cls(
            nova_endpoint=cls.get_nova_endpoint(json_response, nova_api_version),
            neutron_endpoint=cls.get_neutron_endpoint(json_response)
        )

        pass

    @classmethod
    def get_neutron_endpoint(cls, json_resp):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching the Neutron service
        Sends a CRITICAL service check when none are found registered in the Catalog
        """
        catalog = json_resp.get('token', {}).get('catalog', [])
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
                    # (FIXME) Fall back to the 1st available one
                    # FIXME: move warning to outer scope
                    # self.warning("Neutron endpoint on public interface not found. Defaulting to {0}".format(
                    #     entry['endpoints'][0].get('url', '')
                    # ))
                    neutron_endpoint = entry['endpoints'][0].get('url', '')
                    break
        else:
            # FIXME: move warning and service check to outer scope
            # self.warning("Neutron service %s cannot be found in your service catalog", match)
            # self.service_check("openstack.neutron.api", AgentCheck.CRITICAL)
            pass

        return neutron_endpoint

    @classmethod
    def get_nova_endpoint(cls, json_resp, nova_api_version=None):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching the Nova service with the requested version
        Sends a CRITICAL service check when no viable candidates are found in the Catalog
        """
        nova_version = nova_api_version or DEFAULT_NOVA_API_VERSION
        catalog = json_resp.get('token', {}).get('catalog', [])

        # TODO: Get rid of this debug or find a way to store it properly
        # self.log.debug("Keystone Service Catalog: %s", catalog)

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
                    # (FIXME) Fall back to the 1st available one
                    # This is quite arbitrary and is not guaranteed to work
                    # FIXME: propagate warning to outer scope
                    # self.warning("Nova endpoint on public interface not found. Defaulting to {0}".format(
                    #     entry['endpoints'][0].get('url', '')
                    # ))
                    return entry['endpoints'][0].get('url', '')
        else:
            # FIXME: propagate warning to outer scope
            # self.warning("Nova service %s cannot be found in your service catalog", nova_match)
            return None


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

    HYPERVISOR_SERVICE_CHECK_NAME = 'openstack.nova.hypervisor.up'
    NETWORK_SERVICE_CHECK_NAME = 'openstack.neutron.network.up'

    HYPERVISOR_CACHE_EXPIRY = 120 # seconds

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Make sure auth happens at initialization
        self._auth_required = True

        self._ssl_verify = init_config.get("ssl_verify", True)
        self.keystone_server_url = init_config.get("keystone_server_url")
        if not self.keystone_server_url:
            raise IncompleteConfig

        ### Cache some things between runs for values that change rarely
        self._aggregate_list = None

        self._local_only = init_config.get("local_only", True)

        # Mapping of Nova-managed servers to tags
        self.external_host_tags = {}

    def _make_request_with_auth_fallback(self, url, headers=None, verify=True, params=None):
        """
        Generic request handler for OpenStack API requests
        Raises specialized Exceptions for commonly encountered error codes
        """
        try:
            resp = requests.get(url, headers=headers, verify=verify, params=params)
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            if resp.status_code == 401:
                self.log.info('Need to reauthenticate before next check')
                raise OpenstackAuthFailure
            elif resp.status_code == 409:
                # TODO: What are the other cases where this will happen
                raise InstancePowerOffFailure
            else:
                raise

        return resp

    def get_auth_token(self, instance):
        return self.instance_to_scope(instance).auth_token

    ### Network
    def get_neutron_endpoint(self, instance):
        return self.instance_to_scope(instance).service_catalog.neutron_endpoint

    def get_network_stats(self, instance):
        """
        Collect stats for all reachable networks
        """

        # FIXME: (aaditya) Check all networks defaults to true until we can reliably assign agents to networks to monitor
        if self.init_config.get('check_all_networks', True):
            network_ids = list(set(self.get_all_network_ids(instance)) - set(self.init_config.get('exclude_network_ids', [])))
        else:
            network_ids = self.init_config.get('network_ids', [])

        if not network_ids:
            self.warning("Your check is not configured to monitor any networks.\n" +
                         "Please list `network_ids` under your init_config")

        for nid in network_ids:
            self.get_stats_for_single_network(instance, nid)

    def get_all_network_ids(self, instance):
        url = '{0}/{1}/networks'.format(self.get_neutron_endpoint(instance), DEFAULT_NEUTRON_API_VERSION)
        headers = {'X-Auth-Token': self.get_auth_token(instance)}

        network_ids = []
        try:
            resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
            net_details = resp.json()
            for network in net_details['networks']:
                network_ids.append(network['id'])
        except Exception as e:
            self.warning('Unable to get the list of all network ids: {0}'.format(str(e)))

        return network_ids

    def get_stats_for_single_network(self, instance, network_id):
        url = '{0}/{1}/networks/{2}'.format(self.get_neutron_endpoint(instance), DEFAULT_NEUTRON_API_VERSION, network_id)
        headers = {'X-Auth-Token': self.get_auth_token(instance)}
        resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)

        net_details = resp.json()
        service_check_tags = ['network:{0}'.format(network_id)]

        network_name = net_details.get('network', {}).get('name')
        if network_name is not None:
            service_check_tags.append('network_name:{0}'.format(network_name))

        tenant_id = net_details.get('network', {}).get('tenant_id')
        if tenant_id is not None:
            service_check_tags.append('tenant_id:{0}'.format(tenant_id))

        if net_details.get('admin_state_up'):
            self.service_check(self.NETWORK_SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)
        else:
            self.service_check(self.NETWORK_SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags)
    ###

    ### Compute
    def get_nova_endpoint(self, instance):
        return self.instance_to_scope(instance).service_catalog.nova_endpoint

    def _parse_uptime_string(self, uptime):
        """ Parse u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n' """
        uptime = uptime.strip()
        load_averages = uptime[uptime.find('load average:'):].split(':')[1].split(',')
        uptime_sec = uptime.split(',')[0]

        return {
            'loads': map(float, load_averages),
            'uptime_sec': uptime_sec
        }

    def get_hypervisor_stats(self):
        if self.init_config.get('check_all_hypervisors', False):
            hypervisors = list(set(self.get_all_hypervisor_ids()) - set(self.init_config.get('excluded_hypervisor_ids', [])))
        else:
            hypervisors = self.init_config.get('hypervisor_ids', [])

        if not hypervisors:
            self.warning("Your check is not configured to monitor any hypervisors.\n" +
                         "Please list `hypervisor_ids` under your init_config")

        # Populate aggregates, if we haven't done so yet
        self._get_and_set_aggregate_list()
        stats = {}
        for hyp in hypervisors:
            try:
                self.get_stats_for_single_hypervisor(hyp)
            except Exception as e:
                self.warning('Unable to get stats for hypervisor {0}: {1}'.format(hyp, str(e)))

    def get_all_hypervisor_ids(self, filter_by_host=None):
        nova_version = self.init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)
        if nova_version == "v2.1":
            url = '{0}/os-hypervisors'.format(self._nova_url)
            headers = {'X-Auth-Token': self.get_auth_token(instance)}

            hypervisor_ids = []
            try:
                resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
                hv_list = resp.json()
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
                self.warning("Nova API v2 requires admin privileges to index hypervisors. " +\
                             "Please specify the hypervisor you wish to monitor under the `hypervisor_ids` section")
                return []
            return self.init_config.get("hypervisor_ids")

    def get_all_aggregate_hypervisors(self):
        url = '{0}/os-aggregates'.format(self._nova_url)
        headers = {'X-Auth-Token': self.get_auth_token(instance)}

        hypervisor_aggregate_map = {}
        try:
            resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
            aggregate_list = resp.json()
            for v in aggregate_list['aggregates']:
                for host in v['hosts']:
                    hypervisor_aggregate_map[host] = {
                        'aggregate': v['name'],
                        'availability_zone': v['availability_zone']
                    }

        except Exception as e:
            self.warning('Unable to get the list of aggregates: {0}'.format(str(e)))

        return hypervisor_aggregate_map

    def get_uptime_for_single_hypervisor(self, hyp_id):
        url = '{0}/os-hypervisors/{1}/uptime'.format(self._nova_url, hyp_id)
        headers = {'X-Auth-Token': self.get_auth_token(instance)}

        resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
        uptime = resp.json()['hypervisor']['uptime']
        return self._parse_uptime_string(uptime)

    def get_stats_for_single_hypervisor(self, hyp_id, host_tags=None):
        url = '{0}/os-hypervisors/{1}'.format(self._nova_url, hyp_id)
        headers = {'X-Auth-Token': self.get_auth_token(instance)}
        resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
        hyp = resp.json()['hypervisor']
        host_tags = host_tags or []
        tags = [
            'hypervisor:{0}'.format(hyp['hypervisor_hostname']),
            'hypervisor_id:{0}'.format(hyp['id']),
            'virt_type:{0}'.format(hyp['hypervisor_type'])
        ]
        tags.extend(host_tags)

        try:
            uptime = self.get_uptime_for_single_hypervisor(hyp['id'])
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
            except:
                # This creates the AgentCheck.UNKNOWN state
                pass

        if hyp_state is None:
            self.service_check(self.HYPERVISOR_SERVICE_CHECK_NAME, AgentCheck.UNKNOWN,
                               tags=tags)
        elif hyp_state != self.HYPERVISOR_STATE_UP:
            self.service_check(self.HYPERVISOR_SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=tags)
        else:
            self.service_check(self.HYPERVISOR_SERVICE_CHECK_NAME, AgentCheck.OK,
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

    def get_server_stats(self):
        if self.init_config.get('check_all_servers', False):
            server_ids = list(set(self.get_all_server_ids()) - set(self.init_config.get('excluded_server_ids', [])))
        else:
            server_ids = self.init_config.get('server_ids', [])

        if not server_ids:
            self.warning("Your check is not configured to monitor any servers.\n" +
                         "Please list `server_ids` under your init_config in openstack.yaml")

        host_tags = self._get_tags_for_host()
        for sid in server_ids:
            server_tags = host_tags + ["host:%s" % sid]
            self.get_stats_for_single_server(sid, tags=server_tags)

    def get_all_server_ids(self, filter_by_host=None):
        query_params = {}
        if filter_by_host:
            query_params["host"] = filter_by_host

        url = '{0}/servers'.format(self._nova_url)
        headers = {'X-Auth-Token': self.get_auth_token(instance)}

        server_ids = []
        try:
            resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify, params=query_params)

            server_ids = [s['id'] for s in resp.json()['servers']]
        except Exception as e:
            self.warning('Unable to get the list of all servers: {0}'.format(str(e)))

        return server_ids

    def get_stats_for_single_server(self, server_id, tags=None):
        def _is_valid_metric(label):
            return label in NOVA_SERVER_METRICS or any(seg in label for seg in NOVA_SERVER_INTERFACE_SEGMENTS)

        url = '{0}/servers/{1}/diagnostics'.format(self._nova_url, server_id)
        headers = {'X-Auth-Token': self.get_auth_token(instance)}
        server_stats = {}

        try:
            resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
            server_stats = resp.json()
        except InstancePowerOffFailure:
            self.warning("Server %s is powered off and cannot be monitored" % server_id)
            # TODO: Maybe send an event/service check here?
        except Exception as e:
            self.warning("Unknown error when monitoring %s : %s" % (server_id, e))

        if server_stats:
            tags = tags or []
            for st in server_stats:
                if _is_valid_metric(st):
                    self.gauge("openstack.nova.server.{0}".format(st), server_stats[st], tags=tags)

    def get_project_stats(self):
        if self.init_config.get('check_all_projects', False):
            projects = self.get_all_projects()
        else:
            projects = []
            for project_id in self.init_config.get('project_ids', []):
                # Make the format of the data match the results from get_all_projects()
                projects.append({'id': project_id})

        if not projects:
            self.warning("Your check is not configured to monitor any Projects.\n" +
                         "Please list `project_ids` under your init_config")

        for project in projects:
            try:
                self.get_stats_for_single_project(project)
            except Exception as e:
                self.warning('Unable to get stats for Project {0}: {1}'.format(project['id'], str(e)))

    def get_all_projects(self):
        keystone_api_version = self.init_config.get('keystone_api_version', DEFAULT_KEYSTONE_API_VERSION)
        endpoint_name = 'tenants' if keystone_api_version == 'v2.0' else 'projects'
        url = "{0}/{1}/{2}".format(self.keystone_server_url, keystone_api_version, endpoint_name)
        headers = {'X-Auth-Token': self.get_auth_token(instance)}

        projects = []
        try:
            resp = self._make_request_with_auth_fallback(url, headers)
            project_details = resp.json()
            for project in project_details[endpoint_name]:
                projects.append(project)
        except Exception as e:
            self.warning('Unable to get the list of all project ids: {0}'.format(str(e)))

        return projects

    def get_stats_for_single_project(self, project):
        def _is_valid_metric(label):
            return label in PROJECT_METRICS

        url = '{0}/limits'.format(self._nova_url)
        headers = {'X-Auth-Token': self.get_auth_token(instance)}
        resp = self._make_request_with_auth_fallback(url, headers, params={"tenant_id": project['id']})

        server_stats = resp.json()
        tags = ['tenant_id:{0}'.format(project['id'])]
        if 'name' in project:
            tags.append('project_name:{0}'.format(project['name']))

        for st in server_stats['limits']['absolute']:
            if _is_valid_metric(st):
                self.gauge("openstack.nova.limits.{0}".format(st), server_stats['limits']['absolute'][st], tags=tags)

    ###

    ### Cache util
    def _is_expired(self, entry):
        assert entry in ["aggregates", "physical_hosts", "hypervisors"]
        ttl = self.CACHE_TTL.get(entry)
        last_fetch_time = getattr(self, self.FETCH_TIME_ACCESSORS.get(entry))
        return datetime.now() - last_fetch_time > timedelta(seconds=ttl)

    def _get_and_set_aggregate_list(self):
        if not self._aggregate_list or self._is_expired("aggregates"):
            self._aggregate_list = self.get_all_aggregate_hypervisors()
            self._last_aggregate_fetch_time = datetime.now()

        return self._aggregate_list
    ###

    def check(self, instance):

        try:
            # FIXME: must authenticate on a per-instance basis
            if self._auth_required:
                self.authenticate()

            self.log.debug("Running check with creds: \n")
            self.log.debug("Nova Url: %s", self._nova_url)
            self.log.debug("Neutron Url: %s", self.get_neutron_endpoint(instance))
            self.log.debug("Auth Token: %s", self.get_auth_token(instance))

            try:
                # The new default: restrict monitoring to this (host, hypervisor, project)
                # and it's guest servers

                hyp = self.get_local_hypervisor()
                project = self.get_scoped_project()

                # Restrict monitoring to hyp and non-excluded servers, don't do anything else
                excluded_server_ids = self.init_config.get("exclude_server_ids", [])
                servers = list(
                    set(self.get_servers_managed_by_hypervisor()) - set(excluded_server_ids)
                )
                host_tags = self._get_tags_for_host()

                for sid in servers:
                    server_tags = ['server:%s' % sid, "nova_managed_server"]
                    self.external_host_tags[sid] = host_tags
                    self.get_stats_for_single_server(sid, tags=server_tags)

                if hyp:
                    self.get_stats_for_single_hypervisor(hyp, host_tags=host_tags)

                if project:
                    self.get_stats_for_single_project(project)

                # For now, monitor all networks
                self.get_network_stats()
            except OpenstackAuthFailure:
                self._auth_required = True

        except IncompleteConfig:
            self.warning("Configuration Incomplete! Check your openstack.yaml file")
            return


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
        else:
            return None

    def get_scoped_project(self, instance):
        """
        Returns the project that this instance of the check is scoped to
        """
        project_auth_scope = self.instance_to_scope(instance)
        if project_auth_scope.tenant_id:
            return {"id": project_auth_scope.tenant_id}

        filter_params = {
            "name": project_auth_scope.project_name,
            "domain_id": project_auth_scope.domain_id
        }

        url = "{0}/{1}/{2}".format(self.keystone_server_url, DEFAULT_KEYSTONE_API_VERSION, "projects")
        headers = {'X-Auth-Token': self.get_auth_token(instance)}

        projects = []
        try:
            resp = self._make_request_with_auth_fallback(url, headers, params=filter_params)
            project_details = resp.json()
            assert len(project_details["projects"]) == 1, "Non-unique project credentials"
            return project_details["projects"][0]
        except Exception as e:
            self.warning('Unable to get the list of all project ids: {0}'.format(str(e)))

        return None

    def get_my_hostname(self):
        return socket.gethostname()

    def get_servers_managed_by_hypervisor(self):
        return self.get_all_server_ids(filter_by_host=self.get_my_hostname())

    def _get_tags_for_host(self):
        hostname = self.get_my_hostname()

        tags = []
        if hostname in self._get_and_set_aggregate_list():
            tags.append('aggregate:{0}'.format(self._aggregate_list[hostname]['aggregate']))
            # Need to check if there is a value for availability_zone because it is possible to have an aggregate without an AZ
            if self._aggregate_list[hostname]['availability_zone']:
                tags.append('availability_zone:{0}'.format(self._aggregate_list[hostname]['availability_zone']))
        else:
            self.log.info('Unable to find hostname {0} in aggregate list. Assuming this host is unaggregated'.format(hostname))

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
