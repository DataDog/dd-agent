# stdlib
import unittest
from datetime import timedelta, datetime
import time

# 3rd party
from tornado.web import Application
import tornado.httpclient
import requests
import simplejson as json

# project
from transaction import Transaction, TransactionManager
from ddagent import (MAX_WAIT_FOR_REPLAY, MAX_QUEUE_SIZE, THROTTLING_DELAY,
    MetricTransaction, APIMetricTransaction)
from config import get_version
from util import get_tornado_ioloop


class memTransaction(Transaction):
    def __init__(self, size, manager):
        Transaction.__init__(self)
        self._trManager = manager
        self._size = size
        self._flush_count = 0

        self.is_flushable = False

    def flush(self):
        self._flush_count = self._flush_count + 1
        if self.is_flushable:
            self._trManager.tr_success(self)
        else:
            self._trManager.tr_error(self)

        self._trManager.flush_next()


class TestTransaction(unittest.TestCase):

    def setUp(self):
        pass

    def testMemoryLimit(self):
        """Test memory limit as well as simple flush"""

        # No throttling, no delay for replay
        trManager = TransactionManager(timedelta(seconds = 0), MAX_QUEUE_SIZE, timedelta(seconds=0))
       
        step = 10
        oneTrSize = (MAX_QUEUE_SIZE / step) - 1
        for i in xrange(step):
            tr = memTransaction(oneTrSize, trManager)
            trManager.append(tr)

        trManager.flush()

        # There should be exactly step transaction in the list, with
        # a flush count of 1
        self.assertEqual(len(trManager._transactions), step)
        for tr in trManager._transactions:
            self.assertEqual(tr._flush_count,1)

        # Try to add one more
        tr = memTransaction(oneTrSize + 10, trManager)
        trManager.append(tr)

        # At this point, transaction one (the oldest) should have been removed from the list 
        self.assertEqual(len(trManager._transactions), step)
        for tr in trManager._transactions:
            self.assertNotEqual(tr._id,1)

        trManager.flush()
        self.assertEqual(len(trManager._transactions), step)
        # Check and allow transactions to be flushed
        for tr in trManager._transactions:
            tr.is_flushable = True
            # Last transaction has been flushed only once
            if tr._id == step + 1:
                self.assertEqual(tr._flush_count,1)
            else:
                self.assertEqual(tr._flush_count,2)

        trManager.flush()
        self.assertEqual(len(trManager._transactions), 0)

        
    def testThrottling(self):
        """Test throttling while flushing"""
 
        # No throttling, no delay for replay
        trManager = TransactionManager(timedelta(seconds = 0), MAX_QUEUE_SIZE, THROTTLING_DELAY)
        trManager._flush_without_ioloop = True # Use blocking API to emulate tornado ioloop

        # Add 3 transactions, make sure no memory limit is in the way
        oneTrSize = MAX_QUEUE_SIZE / 10
        for i in xrange(3):
            tr = memTransaction(oneTrSize, trManager)
            trManager.append(tr)

        # Try to flush them, time it
        before = datetime.now()
        trManager.flush()
        after = datetime.now()
        self.assertTrue( (after-before) > 3 * THROTTLING_DELAY - timedelta(microseconds=100000), 
            "before = %s after = %s" % (before, after))


    def testCustomEndpoint(self):
        MetricTransaction._endpoints = []
        
        config = {
            "dd_url": "https://foo.bar.com",
            "api_key": "foo",
            "use_dd": True
        }

        app = Application()
        app.skip_ssl_validation = False
        app._agentConfig = config
        app.use_simple_http_client = True

        trManager = TransactionManager(timedelta(seconds = 0), MAX_QUEUE_SIZE, THROTTLING_DELAY)
        trManager._flush_without_ioloop = True # Use blocking API to emulate tornado ioloop
        MetricTransaction._trManager = trManager
        MetricTransaction.set_application(app)
        MetricTransaction.set_endpoints()
        
        transaction = MetricTransaction(None, {})
        endpoints = [transaction.get_url(e) for e in transaction._endpoints]
        expected = ['https://foo.bar.com/intake?api_key=foo']
        self.assertEqual(endpoints, expected, (endpoints, expected))



    def testEndpoints(self):
        """Tests that the logic behind the agent version specific endpoints is ok.
        Also tests that these endpoints actually exist.
        """
        MetricTransaction._endpoints = []

        config = {
            "dd_url": "https://app.datadoghq.com",
            "api_key": "foo",
            "use_dd": True
        }

        app = Application()
        app.skip_ssl_validation = False
        app._agentConfig = config
        app.use_simple_http_client = True

        trManager = TransactionManager(timedelta(seconds = 0), MAX_QUEUE_SIZE, THROTTLING_DELAY)
        trManager._flush_without_ioloop = True # Use blocking API to emulate tornado ioloop
        MetricTransaction._trManager = trManager
        MetricTransaction.set_application(app)
        MetricTransaction.set_endpoints()
        
        transaction = MetricTransaction(None, {})
        endpoints = [transaction.get_url(e) for e in transaction._endpoints]
        expected = ['https://{0}-app.agent.datadoghq.com/intake?api_key=foo'.format(
            get_version().replace(".","-"))]
        self.assertEqual(endpoints, expected, (endpoints, expected))

        for url in endpoints:
            r = requests.post(url, data=json.dumps({"foo":"bar"}), 
                headers={'Content-Type': "application/json"})
            r.raise_for_status()


        transaction = APIMetricTransaction(None, {})
        endpoints = [transaction.get_url(e) for e in transaction._endpoints]
        expected = ['https://{0}-app.agent.datadoghq.com/api/v1/series/?api_key=foo'.format(
            get_version().replace(".","-"))]
        self.assertEqual(endpoints, expected, (endpoints, expected))

        for url in endpoints:
            r = requests.post(url, data=json.dumps({"foo":"bar"}), 
                headers={'Content-Type': "application/json"})
            r.raise_for_status()
            

if __name__ == '__main__':
    unittest.main()

