from nose.plugins.attrib import attr

from tests.checks.common import AgentCheckTest


@attr(requires='fluentd')
class TestFluentd(AgentCheckTest):
    CHECK_NAME = 'fluentd'
    CHECK_GAUGES = ['retry_count', 'buffer_total_queued_size', 'buffer_queue_length']

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.config = {
            "instances": [
                {
                    "monitor_agent_url": "http://localhost:24220/api/plugins.json",
                    "plugin_ids": ["plg1"],
                }
            ]
        }

    def test_fluentd(self):
        self.run_check(self.config)
        self.assertServiceCheckOK(self.check.SERVICE_CHECK_NAME,
                                  tags=['fluentd_host:localhost', 'fluentd_port:24220'])
        for m in self.CHECK_GAUGES:
            self.assertMetric('{0}.{1}'.format(self.CHECK_NAME, m), tags=['plugin_id:plg1'])

        self.assertServiceCheckOK(
            self.check.SERVICE_CHECK_NAME, tags=['fluentd_host:localhost', 'fluentd_port:24220'])

        self.coverage_report()

    def test_fluentd_exception(self):
        self.assertRaises(Exception, lambda: self.run_check({"instances": [{
            "monitor_agent_url": "http://localhost:24222/api/plugins.json",
            "plugin_ids": ["plg2"]}]}))

        self.assertServiceCheckCritical(self.check.SERVICE_CHECK_NAME,
                                        tags=['fluentd_host:localhost', 'fluentd_port:24222'])
        self.coverage_report()

    def test_fluentd_with_tag_by_type(self):
        config = {
            "init_config": {
            },
            "instances": [
                {
                    "monitor_agent_url": "http://localhost:24220/api/plugins.json",
                    "tag_by": "type",
                }
            ]
        }
        self.run_check(config)
        for m in self.CHECK_GAUGES:
            self.assertMetric('{0}.{1}'.format(self.CHECK_NAME, m))
            self.assertMetricTagPrefix('{0}.{1}'.format(self.CHECK_NAME, m), 'type')

        self.assertServiceCheckOK(
            self.check.SERVICE_CHECK_NAME, tags=['fluentd_host:localhost', 'fluentd_port:24220'])

        self.coverage_report()

    def test_fluentd_with_tag_by_plugin_id(self):
        config = {
            "init_config": {
            },
            "instances": [
                {
                    "monitor_agent_url": "http://localhost:24220/api/plugins.json",
                    "tag_by": "plugin_id",
                }
            ]
        }
        self.run_check(config)
        for m in self.CHECK_GAUGES:
            self.assertMetric('{0}.{1}'.format(self.CHECK_NAME, m), tags=['plugin_id:plg1'])
            self.assertMetric('{0}.{1}'.format(self.CHECK_NAME, m), tags=['plugin_id:plg2'])
        self.assertServiceCheckOK(
            self.check.SERVICE_CHECK_NAME, tags=['fluentd_host:localhost', 'fluentd_port:24220'])
        self.coverage_report()
