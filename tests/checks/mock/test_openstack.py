from unittest import TestCase
from tests.checks.common import AgentCheckTest, load_check, load_check_local_dep
from mock import MagicMock, patch


OS_CHECK_NAME = 'openstack'

OpenStackProjectScope = load_check_local_dep(OS_CHECK_NAME, "OpenStackProjectScope")
KeystoneCatalog = load_check_local_dep(OS_CHECK_NAME, "KeystoneCatalog")
IncompleteConfig = load_check_local_dep(OS_CHECK_NAME, "IncompleteConfig")
IncompleteAuthScope = load_check_local_dep(OS_CHECK_NAME, "IncompleteAuthScope")
IncompleteIdentity = load_check_local_dep(OS_CHECK_NAME, "IncompleteIdentity")

MOCK_EXCLUDE_CONFIG = {
    'init_config': {
        "exclude_servers" : ["server_1"],
        "exclude_physical_hosts": ["host_1"],
        # "exclude_hypervisors" :?
        "exclude_aggregates": ["aggregate_1"],

        "check_all_servers": True
    },
    'instances': [{}]
}

class OSProjectScopeTest(TestCase):
    BAD_AUTH_SCOPES = [
        { "auth_scope": {} },
        { "auth_scope": {"project": {}} },
        { "auth_scope": {"project": {"id": ""}} },
        { "auth_scope": {"project": {"name": "test"}} },
        { "auth_scope": {"project": {"name": "test", "domain": {}}} },
        { "auth_scope": {"project": {"name": "test", "domain": {"id": ""}}} },
    ]

    GOOD_AUTH_SCOPES = [
        { "auth_scope": {"project": {"id": "test_project_id"}} },
        { "auth_scope": {"project": {"name": "test", "domain": {"id": "test_id"}}} },
    ]

    BAD_USERS = [
        {"user": {}},
        {"user": {"name": ""}},
        {"user": {"name": "test_name", "password": ""}},
        {"user": {"name": "test_name", "password": "test_pass", "domain": {}}},
        {"user": {"name": "test_name", "password": "test_pass", "domain": {"id": ""}}},
    ]

    GOOD_USERS = [
        {"user": {"name": "test_name", "password": "test_pass", "domain": {"id": "test_id"}}},
    ]

    def _test_bad_auth_scope(self, scope):
        with self.assertRaises(IncompleteAuthScope):
            OpenStackProjectScope.get_auth_scope(scope)

    def test_get_auth_scope(self):
        for scope in self.BAD_AUTH_SCOPES:
            self._test_bad_auth_scope(scope)

        for scope in self.GOOD_AUTH_SCOPES:
            auth_scope = OpenStackProjectScope.get_auth_scope(scope)

            # Should pass through unchanged
            self.assertEqual(auth_scope, scope.get("auth_scope"))

    def _test_bad_user(self, user):
        with self.assertRaises(IncompleteIdentity):
            OpenStackProjectScope.get_user_identity(user)


    def test_get_user_identity(self):
        for user in self.BAD_USERS:
            self._test_bad_user(user)

        for user in self.GOOD_USERS:
            parsed_user = OpenStackProjectScope.get_user_identity(user)
            self.assertEqual(parsed_user, {"methods": ["password"], "password": user})

    def test_from_config(self):
        init_config = {"keystone_server_url": ""}
        instance_config = {}
        with self.assertRaises(IncompleteConfig):
            OpenStackProjectScope.from_config(init_config, instance_config)


class KeyStoneCatalogTest(TestCase):
    EXAMPLE_AUTH_RESPONSE =  {
        u'token': {
            u'methods': [
                u'password'
            ],
            u'roles': [
                {
                    u'id': u'f20c215f5a4d47b7a6e510bc65485ced',
                    u'name': u'datadog_monitoring'
                },
                {
                    u'id': u'9fe2ff9ee4384b1894a90878d3e92bab',
                    u'name': u'_member_'
                }
            ],
            u'expires_at': u'2015-11-02T15: 57: 43.911674Z',
            u'project': {
                u'domain': {
                    u'id': u'default',
                    u'name': u'Default'
                },
                u'id': u'0850707581fe4d738221a72db0182876',
                u'name': u'admin'
            },
            u'catalog': [
                {
                    u'endpoints': [
                        {
                            u'url': u'http://10.0.2.15:8773/',
                            u'interface': u'public',
                            u'region': u'RegionOne',
                            u'region_id': u'RegionOne',
                            u'id': u'541baeb9ab7542609d7ae307a7a9d5f0'
                        },
                        {
                            u'url': u'http: //10.0.2.15:8773/',
                            u'interface': u'admin',
                            u'region': u'RegionOne',
                            u'region_id': u'RegionOne',
                            u'id': u'5c648acaea9941659a5dc04fb3b18e49'
                        },
                        {
                            u'url': u'http: //10.0.2.15: 8773/',
                            u'interface': u'internal',
                            u'region': u'RegionOne',
                            u'region_id': u'RegionOne',
                            u'id': u'cb70e610620542a1804522d365226981'
                        }
                    ],
                    u'type': u'ec2',
                    u'id': u'1398dc02f9b7474eb165106485033b48',
                    u'name': u'nova'
                },
                {
                    u'endpoints': [
                        {
                            u'url': u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876',
                            u'interface': u'internal',
                            u'region': u'RegionOne',
                            u'region_id': u'RegionOne',
                            u'id': u'354e35ed19774e398f80dc2a90d07f4b'
                        },
                        {
                            u'url': u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876',
                            u'interface': u'public',
                            u'region': u'RegionOne',
                            u'region_id': u'RegionOne',
                            u'id': u'36e8e2bf24384105b9d56a65b0900172'
                        },
                        {
                            u'url': u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876',
                            u'interface': u'admin',
                            u'region': u'RegionOne',
                            u'region_id': u'RegionOne',
                            u'id': u'de93edcbf7f9446286687ec68423c36f'
                        }
                    ],
                    u'type': u'computev21',
                    u'id': u'2023bd4f451849ba8abeaaf283cdde4f',
                    u'name': u'novav21'
                },
                {
                    u'endpoints': [
                        {
                            u'url': u'http://10.0.2.15:9292',
                            u'interface': u'internal',
                            u'region': u'RegionOne',
                            u'region_id': u'RegionOne',
                            u'id': u'7c1e318d8f7f42029fcb591598df2ef5'
                        },
                        {
                            u'url': u'http://10.0.2.15:9292',
                            u'interface': u'public',
                            u'region': u'RegionOne',
                            u'region_id': u'RegionOne',
                            u'id': u'afcc88b1572f48a38bb393305dc2b584'
                        },
                        {
                            u'url': u'http://10.0.2.15:9292',
                            u'interface': u'admin',
                            u'region': u'RegionOne',
                            u'region_id': u'RegionOne',
                            u'id': u'd9730dbdc07844d785913219da64a197'
                        }
                    ],
                    u'type': u'network',
                    u'id': u'21ad241f26194bccb7d2e49ee033d5a2',
                    u'name': u'neutron'
                },

            ],
            u'extras': {

            },
            u'user': {
                u'domain': {
                    u'id': u'default',
                    u'name': u'Default'
                },
                u'id': u'5f10e63fbd6b411186e561dc62a9a675',
                u'name': u'datadog'
            },
            u'audit_ids': [
                u'OMQQg9g3QmmxRHwKrfWxyQ'
            ],
            u'issued_at': u'2015-11-02T14: 57: 43.911697Z'
        }
    }

    def test_get_nova_endpoint(self):
        self.assertEqual(KeystoneCatalog.get_nova_endpoint(self.EXAMPLE_AUTH_RESPONSE), u"http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876")
        self.assertEqual(KeystoneCatalog.get_nova_endpoint(self.EXAMPLE_AUTH_RESPONSE, nova_api_version="v2"), u"http://10.0.2.15:8773/")

    def test_get_neutron_endpoint(self):
        self.assertEqual(KeystoneCatalog.get_neutron_endpoint(self.EXAMPLE_AUTH_RESPONSE), u"http://10.0.2.15:9292")

    def test_from_auth_response(self):
        catalog = KeystoneCatalog.from_auth_response(self.EXAMPLE_AUTH_RESPONSE, "v2.1")
        self.assertIsInstance(catalog, KeystoneCatalog)
        self.assertEqual(catalog.neutron_endpoint, u"http://10.0.2.15:9292")
        self.assertEqual(catalog.nova_endpoint, u"http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876")


### INCOMPLETE


# class TestCheckOpenStack(AgentCheckTest):
#     CHECK_NAME = OS_CHECK_NAME
#
#     MOCK_CONFIG = {
#         "keystone_server_url": "",
#         "ssl_verify": False,
#
#         "instances": [
#             {"name" : "test_name"}
#         ]
#     }
#
#     def test_get_scope_for_instance(self):
#         pass
#         # #check = load_check(self.CHECK_NAME, self.MOCK_CONFIG, self.DEFAULT_AGENT_CONFIG)
#         # instance = self.MOCK_CONFIG["instance"][0]
#         #
#         # with self.assertRaises(KeyError):
#         #     check.get_scope_for_instance(instance)
#
#
#         # with patch("OpenStackProjectScope.from_config",
#         #         sassertEqual(self.instance_map["test_name"]
#
#
#     def mock_get_all_servers_by_host(self):
#
#         return {
#             "server_1": {
#                 "aggregate": "aggregate_2"
#             },
#             "server_2": {
#                 "aggregate": "aggregate_1"
#             },
#             "server_3": {
#                 "aggregate": "aggregate_2"
#             }
#         }
