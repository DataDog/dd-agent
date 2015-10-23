from datetime import datetime, timedelta
import json
import requests
import socket

from checks import AgentCheck

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


class OpenstackAuthFailure(Exception):
    pass

class InstancePowerOffFailure(Exception):
    pass

class IncompleteConfig(Exception):
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

    DEFAULT_KEYSTONE_API_VERSION = 'v3'
    DEFAULT_NOVA_API_VERSION = 'v2.1'
    DEFAULT_NEUTRON_API_VERSION = 'v2.0'

    HYPERVISOR_SERVICE_CHECK_NAME = 'openstack.nova.hypervisor.up'
    NETWORK_SERVICE_CHECK_NAME = 'openstack.neutron.network.up'

    HYPERVISOR_CACHE_EXPIRY = 120 # seconds

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Make sure auth happens at initialization
        self._auth_required = True

        self._auth_token = None
        self._nova_url = None
        self._neutron_url = None

        self._ssl_verify = init_config.get("ssl_verify", True)

        self._tenant_id = None
        self._append_tenant_id = init_config.get("append_tenant_id", False)

        ### Cache some stuff between runs for values that change rarely
        self._aggregate_list = None
        self._physical_host_list = None
        self._hypervisor_list = None
        ###

        self._check_v2 = init_config.get("check_v2", True)

    def _make_request_with_auth_fallback(self, url, headers=None, verify=True):
        self.log.debug("SSL Certificate Verification set to %s", verify)
        try:
            resp = requests.get(url, headers=headers, verify=verify)
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

    ### Check config accessors
    def _get_auth_scope(self):
        """
        Expects
        {'project': {'name': 'my_project', 'domain': 'my_domain} or {'project': {'id': 'my_project_id'}}
        """

        auth_scope = self.init_config.get('auth_scope')
        if not auth_scope or not auth_scope.get('project'):
            self.warning("Please specify the auth scope via the `auth_scope` variable in your init_config.\n" +
                         "The auth_scope should look like: {'project': {'name': 'my_project'}} or {'project': {'id': 'project_uuid'}")
            raise IncompleteConfig

        if auth_scope['project'].get('name'):
            # We need to add a domain scope to avoid name, clashes. Search for one. If not raise IncompleteConfig
            if not auth_scope['project'].get('domain', {}).get('id'):
                raise IncompleteConfig
        else:
            if not auth_scope['project'].get('id'):
                raise IncompleteConfig
            self._tenant_id = auth_scope['project']['id']

        self.log.debug("Auth Scope: %s", auth_scope)
        return auth_scope

    def _get_identity_by_method(self):
        user = self.init_config.get('user')
        if not user or not user.get('name') or not user.get('password'):
            self.warning("Please specify the user via the `user` variable in your init_config.\n" +
                         "This is the user you would use to authenticate with Keystone v3 via password auth.\n" +
                         "The user should look like: {'password': 'my_password', 'name': 'my_name'}")
            raise IncompleteConfig

        if not user.get('domain', {}).get('id'):
            user['domain'] = {'id': 'default'}

        identity = {
            "methods": ['password'],
            "password": {"user": user}
        }
        self.log.debug("Identity: %s", identity)
        return identity

    def _get_keystone_server_url(self):
        return self.init_config.get('keystone_server_url')
    ###

    ### Auth
    def get_auth_token_from_auth_response(self, resp):
        return resp.headers.get('X-Subject-Token')

    def authenticate(self):
        keystone_api_version = self.init_config.get('keystone_api_version', self.DEFAULT_KEYSTONE_API_VERSION)

        auth_scope = self._get_auth_scope()

        identity = self._get_identity_by_method()
        keystone_server_url = self._get_keystone_server_url()

        payload = {"auth": {"scope": auth_scope, "identity": identity}}
        auth_url = "{0}/{1}/auth/tokens".format(keystone_server_url, self.DEFAULT_KEYSTONE_API_VERSION)
        headers = {'Content-Type': 'application/json'}

        self.log.debug("SSL Certificate Verification set to %s", self._ssl_verify)
        resp = requests.post(auth_url, headers=headers, data=json.dumps(payload), verify=self._ssl_verify)
        resp.raise_for_status()

        self._nova_url = self.get_nova_url_from_auth_response(resp.json(),
                                                              nova_version=self.init_config.get('nova_api_version'))

        self._neutron_url = self.get_neutron_url_from_auth_response(resp.json())
        self._auth_token = self.get_auth_token_from_auth_response(resp)
    ###

    ### Network
    def get_neutron_url_from_auth_response(self, json_resp):
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
                    self.warning("Neutron endpoint on public interface not found. Defaulting to {0}".format(
                        entry['endpoints'][0].get('url', '')
                    ))
                    neutron_endpoint = entry['endpoints'][0].get('url', '')
                    break
        else:
            self.warning("Nova service %s cannot be found in your service catalog", match)

        return neutron_endpoint

    def get_network_stats(self):
        if self.init_config.get('check_all_networks', False):
            network_ids = list(set(self.get_all_network_ids()) - set(self.init_config.get('excluded_network_ids', [])))
        else:
            network_ids = self.init_config.get('network_ids', [])

        if not network_ids:
            self.warning("Your check is not configured to monitor any networks.\n" +
                         "Please list `network_ids` under your init_config")

        for nid in network_ids:
            self.get_stats_for_single_network(nid)

    def get_all_network_ids(self):
        url = '{0}/{1}/networks'.format(self._neutron_url, self.DEFAULT_NEUTRON_API_VERSION)
        headers = {'X-Auth-Token': self._auth_token}

        network_ids = []
        try:
            resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
            net_details = resp.json()
            for network in net_details['networks']:
                network_ids.append(network['id'])
        except Exception as e:
            self.warning('Unable to get the list of all network ids: {0}'.format(str(e)))

        return network_ids

    def get_stats_for_single_network(self, network_id):
        url = '{0}/{1}/networks/{2}'.format(self._neutron_url, self.DEFAULT_NEUTRON_API_VERSION, network_id)
        headers = {'X-Auth-Token': self._auth_token}
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
    def _parse_uptime_string(self, uptime):
        """ Parse u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n' """
        uptime = uptime.strip()
        load_averages = uptime[uptime.find('load average:'):].split(':')[1].split(',')
        uptime_sec = uptime.split(',')[0]

        return {
            'loads': map(float, load_averages),
            'uptime_sec': uptime_sec
        }

    def get_nova_url_from_auth_response(self, json_resp, nova_version=None):
        nova_version = nova_version or self.DEFAULT_NOVA_API_VERSION
        catalog = json_resp.get('token', {}).get('catalog', [])
        self.log.debug("Keystone Service Catalog: %s", catalog)
        nova_match = 'novav21' if nova_version == 'v2.1' else 'nova'

        nova_endpoint = None

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
                    break
                else:
                    # (FIXME) Fall back to the 1st available one
                    self.warning("Nova endpoint on public interface not found. Defaulting to {0}".format(
                        entry['endpoints'][0].get('url', '')
                    ))
                    nova_endpoint = entry['endpoints'][0].get('url', '')
                    break
        else:
            self.warning("Nova service %s cannot be found in your service catalog", nova_match)
            return None


        # (FIXME): aaditya
        # In some cases, the nova url is returned without the tenant id suffixed
        # e.g. http://172.0.0.1:8774 rather than http://172.0.0.1:8774/<tenant_id>
        # It is still unclear when this happens, but for now the user can configure
        # `append_tenant_id` to manually add this suffix for downstream requests
        if self._append_tenant_id:
            assert self._tenant_id and self._tenant_id not in nova_endpoint,\
                """Incorrect use of _append_tenant_id, please inspect service catalog response.
                   You may need to disable this flag if you're Nova service url contains the tenant_id already"""

            return "{0}/{1}".format(nova_endpoint, self._tenant_id)
        else:
            return nova_endpoint

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
        url = '{0}/os-hypervisors'.format(self._nova_url)
        headers = {'X-Auth-Token': self._auth_token}

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

    def get_all_aggregate_hypervisors(self):
        url = '{0}/os-aggregates'.format(self._nova_url)
        headers = {'X-Auth-Token': self._auth_token}

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
        headers = {'X-Auth-Token': self._auth_token}

        resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
        uptime = resp.json()['hypervisor']['uptime']
        return self._parse_uptime_string(uptime)

    def get_stats_for_single_hypervisor(self, hyp_id, host_tags=None):
        url = '{0}/os-hypervisors/{1}'.format(self._nova_url, hyp_id)
        headers = {'X-Auth-Token': self._auth_token}
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

        for sid in server_ids:
            self.get_stats_for_single_server(sid)

    def get_all_server_ids(self, filter_by_host=None):
        url = '{0}/servers{1}'.format(self._nova_url, "?host=%s" % filter_by_host if filter_by_host else '')
        headers = {'X-Auth-Token': self._auth_token}

        server_ids = []
        try:
            resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)

            server_ids = [s['id'] for s in resp.json()['servers']]
        except Exception as e:
            self.warning('Unable to get the list of all servers: {0}'.format(str(e)))

        return server_ids

    def get_stats_for_single_server(self, server_id, tags=None):
        def _is_valid_metric(label):
            return label in NOVA_SERVER_METRICS or any(seg in label for seg in NOVA_SERVER_INTERFACE_SEGMENTS)

        url = '{0}/servers/{1}/diagnostics'.format(self._nova_url, server_id)
        headers = {'X-Auth-Token': self._auth_token}
        server_stats = {}

        try:
            resp = self._make_request_with_auth_fallback(url, headers, verify=self._ssl_verify)
            server_stats = resp.json()
        except InstancePowerOffFailure:
            self.warning("Server %s is powered off and cannot be monitored" % server_id)
            # TODO: Maybe send an event/service check here?

        if server_stats:
            tags = tags or []
            for st in server_stats:
                if _is_valid_metric(st):
                    self.gauge("openstack.nova.server.{0}".format(st), server_stats[st], tags=tags)

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
            if self._auth_required:
                self.authenticate()

            self.log.debug("Running check with creds: \n")
            self.log.debug("Nova Url: %s", self._nova_url)
            self.log.debug("Neutron Url: %s", self._neutron_url)
            self.log.debug("Auth Token: %s", self._auth_token)

            try:
                if self._check_v2:
                    hyp = self.get_local_hypervisor()
                    aggregate = self.get_aggregates_for_local_host()

                    # Restrict monitoring to hyp and servers, don't do anything else
                    servers = self.get_servers_managed_by_hypervisor()
                    host_tags = self._get_tags_for_host()

                    for sid in servers:
                        server_tags = host_tags + ['host:%s' % sid]
                        self.get_stats_for_single_server(sid, tags=server_tags)

                    hyp_stats = {}
                    self.get_stats_for_single_hypervisor(hyp, host_tags=host_tags)
                else:
                    self.get_hypervisor_stats()
                    self.get_server_stats()

                # What about networks? monitor all
                self.get_network_stats()
            except OpenstackAuthFailure:
                self._auth_required = True

        except IncompleteConfig:
            self.warning("Configuration Incomplete! Check your openstack.yaml file")
            return


    #### Local Info accessors
    def get_local_hypervisor(self):
        # Look up hypervisors available filtered by my hostname
        host = self.get_my_hostname()
        hyp = self.get_all_hypervisor_ids(filter_by_host=host)
        return hyp[0]

    def get_my_hostname(self):
        return socket.gethostname()

    def get_aggregates_for_local_host(self):
        aggregate_list = self._get_and_set_aggregate_list()
        return aggregate_list[self.get_my_hostname()]

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

        return tags
    ####
