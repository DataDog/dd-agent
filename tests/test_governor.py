import copy
import unittest
from functools import partial
from mock import patch

from utils.governor import (
    CheckGovernor,
    ExpiringSelection,
    Governor,
    Limiter,
    LimiterParser,
    LimiterConfigError)
from aggregator import MetricsAggregator


class HybridGovernor(Governor):
    """
    HybridGovernor for tests purpose
    """
    def __init__(self):
        super(HybridGovernor, self).__init__()
        self._limiters = copy.deepcopy(self._CHECK_LIMITERS + self._AGENT_LIMITERS)


class MockMetricAggregator(MetricsAggregator):
    """a MockClass for tests"""
    def __init__(self):
        self.governor = CheckGovernor()
        super(MockMetricAggregator, self).__init__("", governor=self.governor)

    def get_governor(self):
        return self.governor

    def submit_metric(self, name, value=42, mtype='g', tags=None, hostname=None,
                      device_name=None, timestamp=None, sample_rate=1):
        return True


class MockLimiter(Limiter):
    """
    MockLimiter
    """
    _ATOMS = frozenset(['key1', 'key2', 'key3', 'key4', 'key5'])


class GovernorTestCase(unittest.TestCase):
    LIMIT_METRIC_NB = {
        'limiters': [{
            'scope': 'check',
            'selection': 'name',
            'limit': 1
        }]
    }

    NO_LIMIT = {}

    METRIC_PAYLOAD = [
        ('metric_name1', 123456, 42, {"tags": ["tag1", "tag2"]}),
        ('metric_name2', 123456, 42, {"tags": ["tag1", "tag2"]}),
        ('metric_name1', 123456, 42, {"tags": ["tag3"]}),
    ]

    def setUp(self):
        # Simplify `Governor.init` function for tests
        Governor.init = partial(Governor.init, agent_config={}, hostname="my_hostname")

    ##########
    # Common #
    ##########

    def test_empty_conf(self):
        """
        Always accept when no rule is specified
        """
        Governor.init(self.NO_LIMIT)

        m1 = MockMetricAggregator()

        for x in xrange(1, 100):
            self.assertTrue(m1.submit_metric(name='my_metric'))

    def test_name_args(self):
        """
        Properly name arguments
        """
        def myfunction(self, arg1, arg2, arg3):
            pass
        m_governor = CheckGovernor()
        m_governor.set(myfunction)

        # Synchronous
        self.assertTrue(
            m_governor._name_args([1, 2, 3], {}) == {'arg1': 1, 'arg2': 2, 'arg3': 3})
        self.assertTrue(
            m_governor._name_args([1], {'arg2': 2, 'arg3': 3}) == {'arg1': 1, 'arg2': 2, 'arg3': 3})

        # Asynchronous
        self.assertTrue(
            m_governor._name_args(
                [1, 2, 3], {}, asynchronous=True) == {'name': 1, 'timestamp': 2, 'value': 3})
        self.assertTrue(
            m_governor._name_args(
                [1],
                {'arg2': 2, 'arg3': 3}, asynchronous=True) == {'name': 1, 'arg2': 2, 'arg3': 3})

    def test_flush(self):
        """
        Getting governor status should flush limiters when explicitely asked
        """
        Governor.init(self.LIMIT_METRIC_NB)
        Governor._CONTEXTS_TTL = 0  # Reset active contexts at each governor iteration

        aggr = MockMetricAggregator()
        governor = aggr.get_governor()

        self.assertTrue(aggr.submit_metric('my_metric'))
        self.assertFalse(aggr.submit_metric('another_metric'))    # Blocked !

        # Get governor status
        statuses = governor.get_status(flush=True)

        self.assertTrue(len(statuses) == 1)
        mstatus = statuses[0]
        self.assertTrue(mstatus['trace']['overflow_metrics'] == 1)
        self.assertTrue(mstatus['trace']['max_selection_cardinal'] == 1)

        # Get it again
        statuses = governor.get_status()

        self.assertTrue(len(statuses) == 1)
        mstatus = statuses[0]
        self.assertTrue(mstatus['trace']['overflow_metrics'] == 0)
        self.assertTrue(mstatus['trace']['max_selection_cardinal'] == 0)

    ########################################
    # Governor for `asynchronous` analysis #
    ########################################

    @patch('utils.governor.Governor._report_to_datadog')
    def test_process(self, mock_post_warning):
        """
        Hitting the governor limit should trigger a post warning
        """
        Governor.init(self.LIMIT_METRIC_NB)
        governor = HybridGovernor()

        # Do not hit the limit
        governor.process(self.METRIC_PAYLOAD[0:1], report=True)

        self.assertFalse(mock_post_warning.called)

        # Hit the limit
        governor.process(self.METRIC_PAYLOAD, report=True)
        self.assertTrue(mock_post_warning.called)

    #####################################################
    # Governor as a decorator  for `real-time` analysis #
    #####################################################

    def test_aggregators_contamination(self):
        """
        No cross contamination between != metric aggregators
        """
        Governor.init(self.LIMIT_METRIC_NB)

        self.assertTrue(len(Governor.get_all_limiters()) == 1)

        m1 = MockMetricAggregator()
        m2 = MockMetricAggregator()

        self.assertTrue(m1.submit_metric('my_metric'))
        self.assertFalse(m1.submit_metric('another_metric'))    # Blocked !
        self.assertTrue(m1.submit_metric('my_metric'))          # Not blocked !

        self.assertTrue(m2.submit_metric('another_metric'))     # Not blocke


class LimiterTestCase(unittest.TestCase):
    @staticmethod
    def generate_metric(v1, v2):
        """
        Helper to return a metric with
        """
        return {
            'key1': v1,
            'key2': v2,
        }

    def test_limit(self):
        """
        Check incoming metrics against the limit set
        """
        limiter = MockLimiter('key1', 'key2', 1)
        limiter.check = partial(limiter.check, 0)

        # Check limiter task
        self.assertTrue(limiter.check(self.generate_metric("scope1", "selection1")))
        self.assertFalse(limiter.check(self.generate_metric("scope1", "selection2")))
        self.assertTrue(limiter.check(self.generate_metric("scope1", "selection1")))

        # Check trace
        self.assertTrue(limiter._overflow_metrics == 1)

    def test_no_limit(self):
        """
        Always accept metrics when no limit is set
        """
        limiter = MockLimiter('key1', 'key2')
        limiter.check = partial(limiter.check, 0)

        for x in xrange(10000):
            self.assertTrue(limiter.check(
                self.generate_metric("scope1", "selection_" + str(x))))

    def test_limiter_trace(self):
        """
        Generate a trace from submitted metrics
        """

        limiter = MockLimiter('key1', 'key2', 3)
        limiter.check = partial(limiter.check, 0)

        # Check trace definition
        definition = limiter.get_status()['definition']
        self.assertTrue(definition['scope'] == ('key1',))
        self.assertTrue(definition['selection'] == ('key2',))
        self.assertTrue(definition['limit'] == 3)

        # Submit metrics
        limiter.check(self.generate_metric("scope1", "selection1"))
        limiter.check(self.generate_metric("scope1", "selection2"))
        limiter.check(self.generate_metric("scope1", "selection3"))  # We reached the max
        limiter.check(self.generate_metric("scope1", "selection4"))  # Blocked !
        limiter.check(self.generate_metric("scope1", "selection2"))  # Has no effect

        limiter.check(self.generate_metric("scope2", "selection1"))
        limiter.check(self.generate_metric("scope2", "selection2"))

        # Check trace
        trace = limiter.get_status()['trace']
        self.assertTrue(trace['scope_cardinal'] == 2)
        self.assertTrue(trace['overflow_metrics'] == 1)
        self.assertTrue(trace['scope_overflow_cardinal'] == 1)
        self.assertTrue(trace['max_selection_scope'] == ("scope1",))
        self.assertTrue(trace['max_selection_cardinal'] == 3)

    def test_key_extractor(self):
        """
        Extract scope and selection keys from metrics
        """
        limiter1 = MockLimiter(('key1', 'key3'), ('key4', 'key5'), 1)
        limiter2 = MockLimiter('key1', 'key4', 1)

        metric = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3',
            'key4': 'value4',
            'key5': 'value5'
        }

        # Test _to_scope_key
        scope_value1, limit_value1 = limiter1._extract_metric_keys(metric)
        self.assertTrue(scope_value1 == ('value1', 'value3'))
        self.assertTrue(limit_value1 == ('value4', 'value5'))

        scope_value2, limit_value2 = limiter2._extract_metric_keys(metric)
        self.assertTrue(scope_value2 == ('value1',))
        self.assertTrue(limit_value2 == ('value4',))

    def test_hashable_value(self):
        """
        Selection values should always be hashable
        """
        metric = {
            'key1': 'scope_value',
            'key2': ["v1", "v2"],
        }

        limiter = MockLimiter('key1', 'key2', 1)
        _, limit_value = limiter._extract_metric_keys(metric)
        self.assertTrue(limit_value == (("v1", "v2"),), limit_value)


class ExpiringSelectionTestCase(unittest.TestCase):
    def test_active_selection(self):
        """
        Count number of active selections
        """
        expiring_selection = ExpiringSelection()

        expiring_selection.add('selection1', 1)  # New selection
        expiring_selection.add('selection2', 1)  # New selection
        expiring_selection.add('selection1', 2)  # Active selection

        self.assertTrue(len(expiring_selection), 2)

    def test_flush(self):
        """
        Expired selections are flushed
        """
        expiring_selection = ExpiringSelection()
        expiring_selection.add('selection1', 1)
        expiring_selection.add('selection2', 1)
        expiring_selection.add('selection1', 2)

        self.assertTrue(len(expiring_selection), 2)
        expiring_selection.flush(1)
        self.assertTrue(len(expiring_selection), 1)


class LimiterParserTestCase(unittest.TestCase):
    LIMIT_CONFIG = {
        'limiters': [
            {
                'scope': 'name',
                'selection': 'tags',
                'limit': 3
            },
            {
                'scope': ('name', 'check'),
                'selection': 'tags',
                'limit': 5
            },
            {
                'scope': 'check',
                'selection': 'tags',
                'limit': 10
            },
            {
                'scope': 'check',
                'selection': 'name',
                'limit': 10
            }
        ]
    }

    NO_SCOPE_CONFIG = {
        'limiters': [
            {
                'selection': 'tags',
                'limit': 3
            }
        ]
    }

    NO_LIMIT_CONFIG = {
        'limiters': [
            {
                'scope': 'check',
                'selection': 'tags',
            }
        ]
    }

    UNKOWN_SCOPE_CONFIG = {
        'limiters': [
            {
                'scope': ('name', 'unknown_scope'),
                'selection': 'tags',
                'limit': 3
            }
        ]
    }

    NO_CONFIG = {}

    def test_rule_parser(self):
        """
        Parse limiters
        """
        # Incorrect config
        self.assertRaises(LimiterConfigError, LimiterParser.parse_limiters,
                          self.NO_SCOPE_CONFIG)
        self.assertRaises(LimiterConfigError, LimiterParser.parse_limiters,
                          self.UNKOWN_SCOPE_CONFIG)

        # Correct config
        check_limiters, agent_limiters = LimiterParser.parse_limiters(self.LIMIT_CONFIG)
        self.assertTrue(len(check_limiters) == 3)
        self.assertTrue(len(agent_limiters) == 1)

        # No config is a correct config
        self.assertTrue(LimiterParser.parse_limiters(self.NO_CONFIG) == ([], []))

        # No limit is a correct config
        check_limiters, _ = LimiterParser.parse_limiters(self.NO_LIMIT_CONFIG)
        self.assertTrue(len(check_limiters) == 1)
