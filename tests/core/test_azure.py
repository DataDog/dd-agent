# stdlib
import unittest
import os
import json

# 3rd party
import mock

# project
from utils.cloud_metadata import Azure


class TestAzure(unittest.TestCase):
    @mock.patch('requests.get')
    def test_host_aliases(self, mock_get):
        resp = mock.Mock()
        with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'azure', 'metadata_instance.json')) as f:
                data = json.load(f)
                resp.json = lambda: data

        mock_get.return_value = resp

        vm_id = Azure.get_host_aliases({})
        self.assertEqual(vm_id, ["5d33a910-a7a0-4443-9f01-6a807801b29b"])

    @mock.patch('requests.get')
    def test_host_aliases_exception(self, mock_get):
        def raise_error():
            raise Exception("test error")
        resp = mock.Mock()
        resp.raise_for_status = raise_error
        mock_get.return_value = resp

        vm_id = Azure.get_host_aliases({})
        self.assertEqual(vm_id, [])

    @mock.patch('requests.get')
    def test_hostname_bad_format(self, mock_get):
        resp = mock.Mock()
        resp.json = lambda: "{}"
        mock_get.return_value = resp

        vm_id = Azure.get_host_aliases({})
        self.assertEqual(vm_id, [])
