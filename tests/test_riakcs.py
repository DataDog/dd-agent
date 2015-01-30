import unittest
from tests.common import load_check, read_data_from_file


def _get_stats(self, s3, aggregation_key):
    return self.load_json(read_data_from_file("riakcs_in.json"))

def _connect(self, instance):
    return None, None, ["aggregation_key:localhost:8080"]

class RiakCSTest(unittest.TestCase):

        def test_parser(self):
            c = load_check('riakcs', {}, {})
            input_json = read_data_from_file("riakcs_in.json")
            output_python = read_data_from_file("riakcs_out.python")
            self.assertEquals(c.load_json(input_json), eval(output_python))

        def test_metrics(self):
            c = load_check('riakcs', {}, {})
            
            c._connect = lambda x: _connect(c, x)
            c._get_stats = lambda x,y: _get_stats(c, x, y)
            c.check({})
            sorted_metrics = sorted(c.get_metrics())
            sorted_expected = sorted(eval(read_data_from_file("riakcs_metrics.python")))
            self.assertEquals(len(sorted_metrics), len(sorted_expected))
            for i in range(len(sorted_metrics)):
                m_name = sorted_metrics[i][0]
                m_value = sorted_metrics[i][2]
                m_tags = sorted(sorted_metrics[i][3].get('tags', []))
                expected_m_name = sorted_expected[i][0]
                expected_m_value = sorted_expected[i][2]
                expected_m_tags = sorted(sorted_expected[i][3].get('tags', []))
                self.assertEquals((m_name, m_value, m_tags), (expected_m_name, expected_m_value, expected_m_tags))
            