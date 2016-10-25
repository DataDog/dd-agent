# project
from tests.checks.common import AgentCheckTest
from tests.checks.common import Fixtures

DEPLOYMENT_METRICS_CONFIG = {
    'init_config': {
        'default_timeout': 5
    },
    'instances': [
        {
            'url': 'http://localhost:8080',
            'enable_deployment_metrics': True
        }
    ]
}

DEFAULT_CONFIG = {
    'init_config': {
        'default_timeout': 5
    },
    'instances': [
        {
            'url': 'http://localhost:8080'
        }
    ]
}

def getMetricNames(metrics):
    return [metric[0] for metric in metrics]

class MarathonCheckTest(AgentCheckTest):
    CHECK_NAME = 'marathon'

    def test_default_configuration(self):
        def side_effect(url, timeout, auth):
            if "v2/apps" in url:
                return Fixtures.read_json_file("apps.json")
            else:
                raise Exception("unknown url:" + url)

        self.run_check(DEFAULT_CONFIG, mocks={"get_json": side_effect})
        self.assertMetric('marathon.apps', value=1)

        # deployment-related metrics aren't included by default.
        self.assertTrue('marathon.deployments' not in getMetricNames(self.metrics))

    def test_empty_responses(self):
        def side_effect(url, timeout, auth):
            if "v2/apps" in url:
                return {"apps": []}
            else:
                raise Exception("unknown url:" + url)

        self.run_check(DEFAULT_CONFIG, mocks={"get_json": side_effect})
        self.assertMetric('marathon.apps', value=0)

    def test_enabled_deployment_metrics(self):
        def side_effect(url, timeout, auth):
            if "v2/apps" in url:
                return Fixtures.read_json_file("apps.json")
            elif "v2/deployments" in url:
                return Fixtures.read_json_file("deployments.json")
            else:
                raise Exception("unknown url:" + url)

        self.run_check(DEPLOYMENT_METRICS_CONFIG, mocks={"get_json": side_effect})
        self.assertMetric('marathon.apps', value=1)
        self.assertMetric('marathon.deployments', value=1)
