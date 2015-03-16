import unittest
from tests.common import load_check, read_data_from_file, AgentCheckTest
from mock import Mock
from socket import error
from checks import AgentCheck

class RiakCSTest(AgentCheckTest):

        CHECK_NAME = "riakcs"
        def __init__(self, *args, **kwargs):
            unittest.TestCase.__init__(self, *args, **kwargs)
            self.config = {"instances": [{
                "access_id":"foo",
                "access_secret": "bar"}]}
            self.check = load_check(self.CHECK_NAME, self.config, {})
            self.check._connect = Mock(return_value=(None, None, ["aggregation_key:localhost:8080"]))
            self.check._get_stats = Mock(return_value=self.check.load_json(read_data_from_file("riakcs_in.json")))

        def test_parser(self):
            input_json = read_data_from_file("riakcs_in.json")
            output_python = read_data_from_file("riakcs_out.python")
            self.assertEquals(self.check.load_json(input_json), eval(output_python))

        def test_metrics(self):
            self.run_check(self.config)
            expected = eval(read_data_from_file("riakcs_metrics.python"))
            for m in expected:
                self.assertMetric(m[0], m[2], m[3].get('tags', []))


        def test_service_checks(self):
            self.check = load_check(self.CHECK_NAME, self.config, {})
            self.assertRaises(error, lambda: self.run_check(self.config))

            self.assertEqual(len(self.service_checks), 1, self.service_checks)
            self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                    status=AgentCheck.CRITICAL,
                                    tags=['aggregation_key:localhost:8080'])
