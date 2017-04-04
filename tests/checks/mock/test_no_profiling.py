import mock

from tests.checks.common import AgentCheckTest, load_check

class TestNoProfiling(AgentCheckTest):

    CHECK_NAME = 'redisdb'

    def test_no_profiling(self):
        agentConfig = {
            'api_key': 'XXXtest_apikey',
            'developer_mode': True,
            'allow_profiling': False
        }
        # this must be SystemExit, because otherwise the Exception is eaten
        mocks = {
            '_set_internal_profiling_stats': mock.MagicMock(side_effect=SystemExit),
        }
        disk_config = {
            "init_config": {},
            "instances": [{}]
        }
        check = load_check('disk', disk_config, agentConfig)

        self.assertFalse(check.allow_profiling)
        self.assertTrue(check.in_developer_mode)

        for func_name, mock1 in mocks.iteritems():
            if not hasattr(check, func_name):
                continue
            else:
                setattr(check, func_name, mock1)

        check.run()
        # If we get here, no Exception was thrown
