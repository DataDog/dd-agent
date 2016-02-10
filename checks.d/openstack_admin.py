# stdlib
import os
from urlparse import urljoin

# project
from checks import AgentCheck

# 3p
import requests
import simplejson as json

SOURCE_TYPE = 'openstack'

DEFAULT_KEYSTONE_API_VERSION = 'v3'
DEFAULT_NOVA_API_VERSION = 'v2.1'
DEFAULT_NEUTRON_API_VERSION = 'v2.0'

DEFAULT_API_REQUEST_TIMEOUT = 5 # seconds

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

class BadCredentials(IncompleteConfig):
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
    IDENTITY_API_SC = 'openstack.keystone.api.up'

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
        resp = requests.get(url, headers=headers, verify=verify, params=params, timeout=DEFAULT_API_REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

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
        nova_endpoint = self.get_nova_endpoint(auth_resp.json(), self.init_config.get("nova_api_version"))

        if self.init_config.get("append_tenant_id"):
            nova_endpoint = urljoin(os.path.join(nova_endpoint, ''), project_id)
        return auth_token, nova_endpoint


    def get_nova_endpoint(self, json_resp, nova_api_version=None):
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
                    nova_endpoint = valid_endpoints.get("public", valid_endpoints.get("internal"))
                    return nova_endpoint
        else:
            raise MissingNovaEndpoint()

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
        return auth_token, user_id

    def get_stats_for_single_project(self, project, token, nova_endpoint):
        def _is_valid_metric(label):
            return label in PROJECT_METRICS

        project_id = project['id']
        url = '{0}/limits'.format(nova_endpoint)
        headers = {'X-Auth-Token': token}

        self.log.debug("Requesting project stats from url %s", url)
        server_stats = self._make_request_with_auth_fallback(url, headers, params={"tenant_id": project['id']})
        if not server_stats:
            return

        tags = ['tenant_id:{0}'.format(project['id'])]
        if 'name' in project:
            tags.append('project_name:{0}'.format(project['name']))

        for st in server_stats['limits']['absolute']:
            if _is_valid_metric(st):
                metric_key = PROJECT_METRICS[st]
                self.gauge("openstack.nova.limits.{0}".format(metric_key), server_stats['limits']['absolute'][st], tags=tags)
    ###

    def check(self, instance):
        domain_id = instance.get("admin_domain_id")
        auth = instance.get("auth")

        admin_token, admin_user_id = self.get_domain_scoped_token(auth["user"], auth["password"], domain_id)
        if not admin_token:
            raise BadCredentials
        if not domain_id:
            self.warning("Please specify a domain id under instances.")
            raise IncompleteConfig

        try:
            # Monitor all projects and hypervisors and servers

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

                try:
                    project_token, nova_endpoint = self.get_project_scoped_token(
                        project['id'], domain_id, auth["user"], auth["password"]
                    )
                    self.log.debug("Project auth token for project %s is %s", project['id'], project_token)
                    self.log.debug("Nova endpoint for project %s is %s", project['id'], nova_endpoint)
                    self.get_stats_for_single_project(project, project_token, nova_endpoint)
                except Exception as e:
                    self.warning("Couldn't get stats for project %s : %s" % (project['id'], e))

        except BadCredentials:
            self.warning("Please check your admin domain and auth credentials")
        except IncompleteConfig:
            self.warning("Configuration Incomplete! Check your openstack.yaml file")

    ### Cloud Admin Mode
    def get_all_projects(self, auth_token):
        keystone_server_url = self.keystone_server_url
        url = "{0}/{1}/{2}".format(keystone_server_url, DEFAULT_KEYSTONE_API_VERSION, "projects")
        headers = {'X-Auth-Token': auth_token}

        projects = []
        try:
            projects = self._make_request_with_auth_fallback(url, headers)
        except Exception as e:
            self.warning('Unable to get the list of all project ids: {0}'.format(str(e)))

        return projects["projects"]

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
