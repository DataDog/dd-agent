# stdlib
import unittest

# 3rd party
import mock
import requests  # noqa: F401

# project
from utils.orchestrator import BaseUtil
from utils.dockerutil import DockerUtil

CO_ID = 1234


class MockResponse:
    """
    Helper class to mock a json response from requests
    """
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


class TestBaseUtil(unittest.TestCase):
    class DummyUtil(BaseUtil):
        def _get_cacheable_tags(self, cid, co=None):
            return ["test:tag"]

    class NeedLabelsUtil(BaseUtil):
        def __init__(self):
            BaseUtil.__init__(self)
            self.needs_inspect_labels = True

        def _get_cacheable_tags(self, cid, co=None):
            return ["test:tag"]

    class NeedEnvUtil(BaseUtil):
        def __init__(self):
            BaseUtil.__init__(self)
            self.needs_inspect_config = True

        def _get_cacheable_tags(self, cid, co=None):
            return ["test:tag"]

    @mock.patch('docker.Client.__init__')
    def test_extract_tags(self, mock_init):
        mock_init.return_value = None
        dummy = self.DummyUtil()
        dummy.reset_cache()

        self.assertEqual(["test:tag"], dummy.get_container_tags(cid=CO_ID))

    @mock.patch('docker.Client.__init__')
    def test_cache_invalidation_event(self, mock_init):
        mock_init.return_value = None
        dummy = self.DummyUtil()
        dummy.reset_cache()

        dummy.get_container_tags(cid=CO_ID)
        self.assertTrue(CO_ID in dummy._container_tags_cache)

        EVENT = {'status': 'die', 'id': CO_ID}
        dummy.invalidate_cache([EVENT])
        self.assertFalse(CO_ID in dummy._container_tags_cache)

    @mock.patch('docker.Client.__init__')
    def test_reset_cache(self, mock_init):
        mock_init.return_value = None
        dummy = self.DummyUtil()
        dummy.reset_cache()

        dummy.get_container_tags(cid=CO_ID)
        self.assertTrue(CO_ID in dummy._container_tags_cache)

        dummy.reset_cache()
        self.assertFalse(CO_ID in dummy._container_tags_cache)

    def test_auto_inspect(self):
        du = DockerUtil()
        du._client = mock.MagicMock()
        mock_inspect = mock.MagicMock(name='inspect_container', return_value = {'RepoTags': ["redis:3.2"], 'RepoDigests': []})
        du._client.inspect_container = mock_inspect

        dummy = self.NeedLabelsUtil()
        dummy.reset_cache()

        dummy.get_container_tags(cid=CO_ID)
        mock_inspect.assert_called_once()

    def test_no_inspect_if_cached(self):
        du = DockerUtil()
        du._client = mock.MagicMock()
        mock_inspect = mock.MagicMock(name='inspect_container', return_value = {'RepoTags': ["redis:3.2"], 'RepoDigests': []})
        du._client.inspect_container = mock_inspect

        dummy = self.NeedLabelsUtil()
        dummy.reset_cache()

        dummy.get_container_tags(cid=CO_ID)
        mock_inspect.assert_called_once()

        dummy.get_container_tags(cid=CO_ID)
        mock_inspect.assert_called_once()

    @mock.patch('docker.Client.inspect_container')
    @mock.patch('docker.Client.__init__')
    def test_no_useless_inspect(self, mock_init, mock_inspect):
        mock_init.return_value = None

        dummy = self.NeedLabelsUtil()
        dummy.reset_cache()
        co = {'Id': CO_ID, 'Created': 1, 'Labels': {}}

        dummy.get_container_tags(co=co)
        mock_inspect.assert_not_called()

        dummy.get_container_tags(co=co)
        mock_inspect.assert_not_called()

    def test_auto_env_inspect(self):
        du = DockerUtil()
        du._client = mock.MagicMock()
        mock_inspect = mock.MagicMock(name='inspect_container', return_value = {'RepoTags': ["redis:3.2"], 'RepoDigests': []})
        du._client.inspect_container = mock_inspect

        dummy = self.NeedEnvUtil()
        dummy.reset_cache()

        dummy.get_container_tags(co={'Id': CO_ID})
        mock_inspect.assert_called_once()

    @mock.patch('docker.Client.inspect_container')
    @mock.patch('docker.Client.__init__')
    def test_no_useless_env_inspect(self, mock_init, mock_inspect):
        mock_init.return_value = None

        dummy = self.NeedEnvUtil()
        dummy.reset_cache()

        dummy.get_container_tags(co={'Id': CO_ID, 'Config': {'Env': {1: 1}}})
        mock_inspect.assert_not_called()
