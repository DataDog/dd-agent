# stdlib
import unittest
from types import ListType

# 3p
from mock import patch, MagicMock

# project
from tests.checks.common import load_check, AgentCheckTest
from tests.checks.common import Fixtures

CONFIG = {
    'init_config': {
			'default_timeout': 5
		},
    'instances': [
        {
						'url': 'http://localhost:8080'
        }
    ]
}

class MarathonCheckTest(AgentCheckTest):
	CHECK_NAME = 'marathon'

	def test_empty_responses(self):
		def side_effect(url, timeout, auth):
			m = MagicMock()

			if "v2/apps" in url:
				return {"apps": []}
			elif "v2/deployments" in url:
				return []
			else:
				raise Exception("unknown url:" + url)

		self.run_check(CONFIG, mocks={"get_json": side_effect})
		self.assertMetric('marathon.apps', value=0)
		self.assertMetric('marathon.deployments', value=0)

	def test_has_apps(self):
		def side_effect(url, timeout, auth):
			m = MagicMock()

			if "v2/apps" in url:
				return Fixtures.read_json_file("apps.json")
			elif "v2/deployments" in url:
				return []
			else:
				raise Exception("unknown url:" + url)

		self.run_check(CONFIG, mocks={"get_json": side_effect})
		self.assertMetric('marathon.apps', value=1)
		self.assertMetric('marathon.deployments', value=0)

	def test_has_deployments(self):
		def side_effect(url, timeout, auth):
			m = MagicMock()

			if "v2/apps" in url:
				return Fixtures.read_json_file("apps.json")
			elif "v2/deployments" in url:
				return Fixtures.read_json_file("deployments.json")
			else:
				raise Exception("unknown url:" + url)

		self.run_check(CONFIG, mocks={"get_json": side_effect})
		self.assertMetric('marathon.apps', value=1)
		self.assertMetric('marathon.deployments', value=1)
