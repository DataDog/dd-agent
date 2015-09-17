import json
import requests

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

class IncompleteConfig(Exception):
    pass

class OpenstackCheck(AgentCheck):

    HYPERVISOR_STATE_UP = 'up'
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

    def _make_request_with_auth_fallback(self, url, headers=None):
        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            if resp.status_code == 401:
                self.log.info('Need to reauthenticate before next check')
                raise OpenstackAuthFailure
            else:
                raise

        return resp

    ### Check config accessors
    def _get_auth_scope(self):
        auth_scope = self.init_config.get('auth_scope')
        if not auth_scope or not auth_scope.get('project') or not auth_scope.get('project').get('name'):
            self.warning("Please specify the auth scope via the `auth_scope` variable in your init_config.\n" +
                         "The auth_scope should look like: {'project': {'name': 'my_project'}}")
            raise IncompleteConfig

        if not auth_scope['project'].get('domain', {}).get('id'):
            auth_scope['project']['domain'] = {'id': 'default'}
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

        resp = requests.post(auth_url, headers=headers, data=json.dumps(payload))
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

        for entry in catalog:
            if entry['name'] == match:
                for ep in entry['endpoints']:
                    if ep.get('interface', '') == 'public':
                        url = ep.get('url', None)
                        if url is not None:
                            return url
                # Fall back to the 1st one
                return entry['endpoints'][0].get('url', '')
        else:
            return None

    def get_network_stats(self):
        if self.init_config.get('check_all_networks', False):
            network_ids = self.get_all_network_ids()
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
            resp = self._make_request_with_auth_fallback(url, headers)
            net_details = resp.json()
            for network in net_details['networks']:
                network_ids.append(network['id'])
        except:
            self.warning('Unable to get the list of all network ids.')

        return network_ids

    def get_stats_for_single_network(self, network_id):
        url = '{0}/{1}/networks/{2}'.format(self._neutron_url, self.DEFAULT_NEUTRON_API_VERSION, network_id)
        headers = {'X-Auth-Token': self._auth_token}
        resp = self._make_request_with_auth_fallback(url, headers)

        net_details = resp.json()
        service_check_tags = ['network:{0}'.format(network_id)]

        if net_details.get('admin_state_up'):
            self.service_check(self.NETWORK_SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags)
        else:
            self.service_check(self.NETWORK_SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)
    ###

    def _parse_uptime_string(self, uptime):
        """ Parse u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n' """
        uptime = uptime.strip()
        load_averages = uptime[uptime.find('load average:'):].split(':')[1].split(',')
        uptime_sec = uptime.split(',')[0]

        return {
            'loads': map(float, load_averages),
            'uptime_sec': uptime_sec
        }

    ### Compute
    def get_nova_url_from_auth_response(self, json_resp, nova_version=None):
        nova_version = nova_version or self.DEFAULT_NOVA_API_VERSION
        catalog = json_resp.get('token', {}).get('catalog', [])
        nova_match = 'novav21' if nova_version == 'v2.1' else 'nova'
        for entry in catalog:
            if entry['name'] == nova_match:
                for ep in entry['endpoints']:
                    if ep.get('interface', '') == 'public':
                        url = ep.get('url', None)
                        if url is not None:
                            return url
                # Fall back to the 1st one
                return entry['endpoints'][0].get('url', '')
        else:
            return None

    def get_hypervisor_stats(self):
        hypervisors = self.init_config.get('hypervisor_ids', [])

        if not hypervisors:
            self.warning("Your check is not configured to monitor any hypervisors.\n" +
                         "Please list `hypervisor_ids` under your init_config")

        stats = {}
        for hyp in hypervisors:
            stats[hyp] = {
                'payload': self.get_stats_for_single_hypervisor(hyp),
                'uptime': self.get_uptime_for_single_hypervisor(hyp)
            }
        return stats

    def get_uptime_for_single_hypervisor(self, hyp_id):
        url = '{0}/os-hypervisors/{1}/uptime'.format(self._nova_url, hyp_id)
        headers = {'X-Auth-Token': self._auth_token}

        resp = self._make_request_with_auth_fallback(url, headers)
        uptime = resp.json()['hypervisor']['uptime']
        return self._parse_uptime_string(uptime)

    def get_stats_for_single_hypervisor(self, hyp_id):
        url = '{0}/os-hypervisors/{1}'.format(self._nova_url, hyp_id)
        headers = {'X-Auth-Token': self._auth_token}
        resp = self._make_request_with_auth_fallback(url, headers)
        hyp = resp.json()['hypervisor']
        service_check_tags = ['hypervisor:{0}'.format(hyp['hypervisor_hostname'])]

        if hyp['state'] != self.HYPERVISOR_STATE_UP:
            self.service_check(self.HYPERVISOR_SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags)
        else:
            self.service_check(self.HYPERVISOR_SERVICE_CHECK_NAME, AgentCheck.OK,
                               tags=service_check_tags)

        return hyp

    def get_server_stats(self):
        server_ids = self.init_config.get('server_ids', [])
        if not server_ids:
            self.warning("Your check is not configured to monitor any servers.\n" +
                         "Please list `server_ids` under your init_config in openstack.yaml")

        for sid in server_ids:
            self.get_stats_for_single_server(sid)

    def get_stats_for_single_server(self, server_id):
        def _is_valid_metric(label):
            return label in NOVA_SERVER_METRICS or any(seg in label for seg in NOVA_SERVER_INTERFACE_SEGMENTS)

        url = '{0}/servers/{1}/diagnostics'.format(self._nova_url, server_id)
        headers = {'X-Auth-Token': self._auth_token}
        resp = self._make_request_with_auth_fallback(url, headers)

        server_stats = resp.json()
        tags = ['server:{0}'.format(server_id)]

        for st in server_stats:
            if _is_valid_metric(st):
                self.gauge("openstack.nova.server.{0}".format(st), server_stats[st], tags=tags)

    ###

    def nova_stats_to_metrics(self, stats):
        for _, v in stats.iteritems():
            payload = v['payload']

            tags = ['hypervisor:{0}'.format(payload['hypervisor_hostname']),'virt_type:{0}'.format(payload['hypervisor_type'])]

            for label, val in payload.iteritems():
                if label in NOVA_HYPERVISOR_METRICS:
                    metric_label = "openstack.nova.{0}".format(label)
                    self.gauge(metric_label, val, tags=tags)

            uptime = v['uptime']
            load_averages = uptime['loads']

            assert len(load_averages) == 3
            for i, avg in enumerate([1, 5, 15]):
                self.gauge('openstack.nova.hypervisor_load.{0}'.format(avg), load_averages[i], tags=tags)


    def check(self, instance):

        try:
            if self._auth_required:
                self.authenticate()

            self.log.debug("Running check with creds: \n")
            self.log.debug("Nova Url: %s", self._nova_url)
            self.log.debug("Neutron Url: %s", self._neutron_url)
            self.log.debug("Auth Token: %s", self._auth_token)

            try:
                hyp_stats = self.get_hypervisor_stats()
                self.nova_stats_to_metrics(hyp_stats)

                self.get_server_stats()
                self.get_network_stats()
            except OpenstackAuthFailure:
                self._auth_required = True

        except IncompleteConfig:
            self.warning("Configuration Incomplete! Check your openstack.yaml file")
            return
