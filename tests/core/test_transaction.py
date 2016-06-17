# stdlib
from datetime import datetime, timedelta
import threading
import time
import unittest

# 3rd party
from nose.plugins.attrib import attr
import requests
import simplejson as json
from tornado.web import Application

# project
from config import get_version
from ddagent import (
    APIMetricTransaction,
    APIServiceCheckTransaction,
    MAX_QUEUE_SIZE,
    MetricTransaction,
    THROTTLING_DELAY,
)
from transaction import Transaction, TransactionManager


class memTransaction(Transaction):
    def __init__(self, size, manager):
        Transaction.__init__(self)
        self._trManager = manager
        self._size = size
        self._flush_count = 0
        self._endpoint = 'https://example.com'
        self._api_key = 'a' * 32

        self.is_flushable = False

    def flush(self):
        self._flush_count = self._flush_count + 1
        if self.is_flushable:
            self._trManager.tr_success(self)
        else:
            self._trManager.tr_error(self)

        self._trManager.flush_next()


class SleepingTransaction(Transaction):
    def __init__(self, manager, delay=0.5):
        Transaction.__init__(self)
        self._trManager = manager
        self._size = 1
        self._flush_count = 0
        self._endpoint = 'https://example.com'
        self._api_key = 'a' * 32
        self.delay = delay

        self.is_flushable = False

    def flush(self):
        threading.Timer(self.delay, self.post_flush).start()

    def post_flush(self):
        self._flush_count = self._flush_count + 1
        if self.is_flushable:
            self._trManager.tr_success(self)
        else:
            self._trManager.tr_error(self)

        self._trManager.flush_next()


@attr(requires='core_integration')
class TestTransaction(unittest.TestCase):

    def setUp(self):
        pass

    def testMemoryLimit(self):
        """Test memory limit as well as simple flush"""

        # No throttling, no delay for replay
        trManager = TransactionManager(timedelta(seconds=0), MAX_QUEUE_SIZE,
                                       timedelta(seconds=0), max_endpoint_errors=100)

        step = 10
        oneTrSize = (MAX_QUEUE_SIZE / step) - 1
        for i in xrange(step):
            trManager.append(memTransaction(oneTrSize, trManager))

        trManager.flush()

        # There should be exactly step transaction in the list, with
        # a flush count of 1
        self.assertEqual(len(trManager._transactions), step)
        for tr in trManager._transactions:
            self.assertEqual(tr._flush_count, 1)

        # Try to add one more
        trManager.append(memTransaction(oneTrSize + 10, trManager))

        # At this point, transaction one (the oldest) should have been removed from the list
        self.assertEqual(len(trManager._transactions), step)
        for tr in trManager._transactions:
            self.assertNotEqual(tr._id, 1)

        trManager.flush()
        self.assertEqual(len(trManager._transactions), step)
        # Check and allow transactions to be flushed
        for tr in trManager._transactions:
            tr.is_flushable = True
            # Last transaction has been flushed only once
            if tr._id == step + 1:
                self.assertEqual(tr._flush_count, 1)
            else:
                self.assertEqual(tr._flush_count, 2)

        trManager.flush()
        self.assertEqual(len(trManager._transactions), 0)

    def testThrottling(self):
        """Test throttling while flushing"""

        # No throttling, no delay for replay
        trManager = TransactionManager(timedelta(seconds=0), MAX_QUEUE_SIZE,
                                       THROTTLING_DELAY, max_endpoint_errors=100)
        trManager._flush_without_ioloop = True  # Use blocking API to emulate tornado ioloop

        # Add 3 transactions, make sure no memory limit is in the way
        oneTrSize = MAX_QUEUE_SIZE / 10
        for i in xrange(3):
            tr = memTransaction(oneTrSize, trManager)
            trManager.append(tr)

        # Try to flush them, time it
        before = datetime.utcnow()
        trManager.flush()
        after = datetime.utcnow()
        self.assertTrue((after - before) > 3 * THROTTLING_DELAY - timedelta(microseconds=100000),
                        "before = %s after = %s" % (before, after))

    def testCustomEndpoint(self):
        MetricTransaction._endpoints = []

        config = {
            "endpoints": {"https://foo.bar.com": ["foo"]},
            "dd_url": "https://foo.bar.com",
            "api_key": "foo",
            "use_dd": True
        }

        app = Application()
        app.skip_ssl_validation = False
        app._agentConfig = config
        app.use_simple_http_client = True

        trManager = TransactionManager(timedelta(seconds=0), MAX_QUEUE_SIZE,
                                       THROTTLING_DELAY, max_endpoint_errors=100)
        trManager._flush_without_ioloop = True  # Use blocking API to emulate tornado ioloop
        MetricTransaction._trManager = trManager
        MetricTransaction.set_application(app)
        MetricTransaction.set_endpoints(config['endpoints'])

        transaction = MetricTransaction(None, {}, "msgtype")
        endpoints = []
        for endpoint in transaction._endpoints:
            for api_key in transaction._endpoints[endpoint]:
                endpoints.append(transaction.get_url(endpoint, api_key))
        expected = ['https://foo.bar.com/intake/msgtype?api_key=foo']
        self.assertEqual(endpoints, expected, (endpoints, expected))

    def testEndpoints(self):
        """
        Tests that the logic behind the agent version specific endpoints is ok.
        Also tests that these endpoints actually exist.
        """
        MetricTransaction._endpoints = []
        api_key = "a" * 32
        config = {
            "endpoints": {"https://app.datadoghq.com": [api_key]},
            "dd_url": "https://app.datadoghq.com",
            "api_key": api_key,
            "use_dd": True
        }

        app = Application()
        app.skip_ssl_validation = False
        app._agentConfig = config
        app.use_simple_http_client = True

        trManager = TransactionManager(timedelta(seconds=0), MAX_QUEUE_SIZE,
                                       THROTTLING_DELAY, max_endpoint_errors=100)
        trManager._flush_without_ioloop = True  # Use blocking API to emulate tornado ioloop
        MetricTransaction._trManager = trManager
        MetricTransaction.set_application(app)
        MetricTransaction.set_endpoints(config['endpoints'])

        transaction = MetricTransaction(None, {}, "")
        endpoints = []
        for endpoint in transaction._endpoints:
            for api_key in transaction._endpoints[endpoint]:
                endpoints.append(transaction.get_url(endpoint, api_key))
        expected = ['https://{0}-app.agent.datadoghq.com/intake/?api_key={1}'.format(
            get_version().replace(".", "-"), api_key)]
        self.assertEqual(endpoints, expected, (endpoints, expected))

        for url in endpoints:
            r = requests.post(url, data=json.dumps({"foo": "bar"}),
                              headers={'Content-Type': "application/json"})
            r.raise_for_status()

        # API Metric Transaction
        transaction = APIMetricTransaction(None, {})
        endpoints = []
        for endpoint in transaction._endpoints:
            for api_key in transaction._endpoints[endpoint]:
                endpoints.append(transaction.get_url(endpoint, api_key))
        expected = ['https://{0}-app.agent.datadoghq.com/api/v1/series/?api_key={1}'.format(
            get_version().replace(".", "-"), api_key)]
        self.assertEqual(endpoints, expected, (endpoints, expected))

        for url in endpoints:
            r = requests.post(url, data=json.dumps({"foo": "bar"}),
                              headers={'Content-Type': "application/json"})
            r.raise_for_status()

        # API Service Check Transaction
        APIServiceCheckTransaction._trManager = trManager
        APIServiceCheckTransaction.set_application(app)
        APIServiceCheckTransaction.set_endpoints(config['endpoints'])

        transaction = APIServiceCheckTransaction(None, {})
        endpoints = []
        for endpoint in transaction._endpoints:
            for api_key in transaction._endpoints[endpoint]:
                endpoints.append(transaction.get_url(endpoint, api_key))
        expected = ['https://{0}-app.agent.datadoghq.com/api/v1/check_run/?api_key={1}'.format(
            get_version().replace(".", "-"), api_key)]
        self.assertEqual(endpoints, expected, (endpoints, expected))

        for url in endpoints:
            r = requests.post(url, data=json.dumps({'check': 'test', 'status': 0}),
                              headers={'Content-Type': "application/json"})
            r.raise_for_status()

    def test_endpoint_error(self):
        trManager = TransactionManager(timedelta(seconds=0), MAX_QUEUE_SIZE,
                                       timedelta(seconds=0), max_endpoint_errors=2)

        step = 10
        oneTrSize = (MAX_QUEUE_SIZE / step) - 1
        for i in xrange(step):
            trManager.append(memTransaction(oneTrSize, trManager))

        trManager.flush()

        # There should be exactly step transaction in the list,
        # and only 2 of them with a flush count of 1
        self.assertEqual(len(trManager._transactions), step)
        flush_count = 0
        for tr in trManager._transactions:
            flush_count += tr._flush_count
        self.assertEqual(flush_count, 2)

        # If we retry to flush, two OTHER transactions should be tried
        trManager.flush()

        self.assertEqual(len(trManager._transactions), step)
        flush_count = 0
        for tr in trManager._transactions:
            flush_count += tr._flush_count
            self.assertIn(tr._flush_count, [0, 1])
        self.assertEqual(flush_count, 4)

        # Finally when it's possible to flush, everything should go smoothly
        for tr in trManager._transactions:
            tr.is_flushable = True

        trManager.flush()
        self.assertEqual(len(trManager._transactions), 0)

    @attr('unix')
    def test_parallelism(self):
        step = 4
        trManager = TransactionManager(timedelta(seconds=0), MAX_QUEUE_SIZE,
                                       timedelta(seconds=0), max_parallelism=step,
                                       max_endpoint_errors=100)
        for i in xrange(step):
            trManager.append(SleepingTransaction(trManager))

        trManager.flush()
        self.assertEqual(trManager._running_flushes, step)
        self.assertEqual(trManager._finished_flushes, 0)
        # If _trs_to_flush != None, it means that it's still running as it should be
        self.assertEqual(trManager._trs_to_flush, [])
        time.sleep(1)

        # It should be finished
        self.assertEqual(trManager._running_flushes, 0)
        self.assertEqual(trManager._finished_flushes, step)
        self.assertIs(trManager._trs_to_flush, None)

    @attr('unix')
    def test_no_parallelism(self):
        step = 2
        trManager = TransactionManager(timedelta(seconds=0), MAX_QUEUE_SIZE,
                                       timedelta(seconds=0), max_parallelism=1,
                                       max_endpoint_errors=100)
        for i in xrange(step):
            trManager.append(SleepingTransaction(trManager, delay=1))
        trManager.flush()
        # Flushes should be sequential
        for i in xrange(step):
            self.assertEqual(trManager._running_flushes, 1)
            self.assertEqual(trManager._finished_flushes, i)
            self.assertEqual(len(trManager._trs_to_flush), step - (i + 1))
            time.sleep(1)

    def test_multiple_endpoints(self):
        config = {
            "endpoints": {
                "https://app.datadoghq.com": ['api_key'],
                "https://app.example.com":  ['api_key']
            },
            "dd_url": "https://app.datadoghq.com",
            "api_key": 'api_key',
            "use_dd": True
        }
        app = Application()
        app.skip_ssl_validation = False
        app._agentConfig = config
        app.use_simple_http_client = True
        trManager = TransactionManager(timedelta(seconds=0), MAX_QUEUE_SIZE,
                                       THROTTLING_DELAY, max_endpoint_errors=100)
        trManager._flush_without_ioloop = True  # Use blocking API to emulate tornado ioloop
        MetricTransaction._trManager = trManager
        MetricTransaction.set_application(app)
        MetricTransaction.set_endpoints(config['endpoints'])

        MetricTransaction({}, {})
        # 2 endpoints = 2 transactions
        self.assertEqual(len(trManager._transactions), 2)
