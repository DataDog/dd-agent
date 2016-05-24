# project
from tests.checks.common import AgentCheckTest

class TestCheckShell(AgentCheckTest):
    CHECK_NAME = "shell"

    CONFIG = {
        "instances": [{
            "command": "uptime | awk '{print $4}'",
            "metric_name": "current.users",
            "metric_type": "gauge",
            "tags": ["directory:foo"]
        }],
        "metric_name": "shell.current.users",
        "metric_type": "gauge",
        "tags":["directory:foo"]
    }

    def test_check(self):
        config = self.CONFIG
        metric_name = config.get("metric_name")
        tags = config.get("tags")

        self.run_check(config)

        self.assertMetric(metric_name, count=1, tags=tags)

        self.coverage_report()
