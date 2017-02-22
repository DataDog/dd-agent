import mock

from tests.checks.common import AgentCheckTest, load_check, copy_checks, remove_checks

class TestNoProfiling(AgentCheckTest):

    CHECK_NAME = 'redisdb'

    def setUp(self):
        copy_checks()

    def tearDown(self):
        remove_checks()

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
        redis_config = {
            "init_config": {},
            "instances": [{"host": "localhost", "port": 6379}]
        }
        check = load_check('redisdb', redis_config, agentConfig)

        self.assertFalse(check.allow_profiling)
        self.assertTrue(check.in_developer_mode)

        for func_name, mock1 in mocks.iteritems():
            if not hasattr(check, func_name):
                continue
            else:
                setattr(check, func_name, mock1)

        check.run()
        # If we get here, no Exception was thrown
