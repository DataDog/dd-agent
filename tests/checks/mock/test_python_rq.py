# stdlib
import mock
import unittest

# project
from tests.checks.common import AgentCheckTest, get_check_class


class TestRQCheck(AgentCheckTest):
    CHECK_NAME = 'python_rq'

    def mock_get_workers_status(self, connection):
        return {
            'idle': 2,
            'busy': 4,
            'suspended': 1,
            'started': 3,
        }

    def mock_get_queues_name(self, connection):
        return ['low', 'high']

    def mock_get_cardinality(self, connection, name, prefix):
        if 'queue' in prefix:
            return 5
        elif 'wip' in prefix:
            return 10
        elif 'deferred' in prefix:
            return 15
        elif 'finished' in prefix:
            return 20
        else:
            return 25

    def test_improperly_configured(self):
        """
        Ensure that it raises an exception if the instance configuration
        is improperly configured
        """
        config = {
            'init_config': {},
            'instances' : [{}]
        }
        self.assertRaises(Exception, self.run_check, config)

    @mock.patch('redis.Redis')
    def test_config_host_port_ok(self, *args):
        """
        Ensure that using just a 'host' and 'port' keywords is enough
        to launch the check
        """
        config = {
            'init_config': {},
            'instances' : [{
                'host': 'localhost',
                'port': '6379',
            }]
        }
        self.run_check(config)

    @mock.patch('redis.Redis')
    def test_config_unix_socket_ok(self, *args):
        """
        Ensure that using just a 'unix_socket_path' is enough to launch
        the check
        """
        config = {
            'init_config': {},
            'instances' : [{
                'unix_socket_path': '/var/run/redis/redis',
            }]
        }
        self.run_check(config)

    @mock.patch('redis.Redis')
    def test_workers_metrics(self, *args):
        """
        Collects the metrics related to RQ workers. These metrics must
        be tagged according to the worker status
        """
        mocks = {
            '_get_workers_status': self.mock_get_workers_status,
        }
        config = {
            'init_config': {},
            'instances' : [{
                'host': 'localhost',
                'port': '6379',
            }]
        }
        self.run_check(config, mocks=mocks)
        self.assertMetric('python_rq.workers', value=2, tags=['status:idle'])
        self.assertMetric('python_rq.workers', value=3, tags=['status:started'])
        self.assertMetric('python_rq.workers', value=1, tags=['status:suspended'])
        self.assertMetric('python_rq.workers', value=4, tags=['status:busy'])

    @mock.patch('redis.Redis')
    def test_failed_jobs_metrics(self, *args):
        """
        Collects the metrics related to the number of failed jobs
        """
        mocks = {
            '_get_cardinality': self.mock_get_cardinality,
        }
        config = {
            'init_config': {},
            'instances' : [{
                'host': 'localhost',
                'port': '6379',
            }]
        }
        self.run_check(config, mocks=mocks)
        self.assertMetric('python_rq.queue.failed', value=5)

    @mock.patch('redis.Redis')
    def test_all_queues_status(self, *args):
        """
        Collects the metrics related to each queue, ensuring that if no
        queues parameter is configured in the config file, all queues
        are handled
        """
        mocks = {
            '_get_queues_names': self.mock_get_queues_name,
            '_get_cardinality': self.mock_get_cardinality,
        }
        config = {
            'init_config': {},
            'instances' : [{
                'host': 'localhost',
                'port': '6379',
            }]
        }
        self.run_check(config, mocks=mocks)
        self.assertMetric('python_rq.queue.enqueued', value=5, tags=['queue:low'])
        self.assertMetric('python_rq.queue.in_progress', value=10, tags=['queue:low'])
        self.assertMetric('python_rq.queue.deferred', value=15, tags=['queue:low'])
        self.assertMetric('python_rq.queue.finished', value=20, tags=['queue:low'])

        self.assertMetric('python_rq.queue.enqueued', value=5, tags=['queue:high'])
        self.assertMetric('python_rq.queue.in_progress', value=10, tags=['queue:high'])
        self.assertMetric('python_rq.queue.deferred', value=15, tags=['queue:high'])
        self.assertMetric('python_rq.queue.finished', value=20, tags=['queue:high'])

    @mock.patch('redis.Redis')
    def test_chosen_queues_status(self, *args):
        """
        Collects the metrics related to each queue, ensuring that if queues
        parameter is configured in the config file, only these queues are
        handled
        """
        mocks = {
            '_get_queues_names': self.mock_get_queues_name,
            '_get_cardinality': self.mock_get_cardinality,
        }
        config = {
            'init_config': {},
            'instances' : [{
                'host': 'localhost',
                'port': '6379',
                'queues': ['high'],
            }]
        }
        self.run_check(config, mocks=mocks)
        self.assertMetric('python_rq.queue.enqueued', count=0, tags=['queue:low'])
        self.assertMetric('python_rq.queue.in_progress', count=0, tags=['queue:low'])
        self.assertMetric('python_rq.queue.deferred', count=0, tags=['queue:low'])
        self.assertMetric('python_rq.queue.finished', count=0, tags=['queue:low'])

        self.assertMetric('python_rq.queue.enqueued', value=5, tags=['queue:high'])
        self.assertMetric('python_rq.queue.in_progress', value=10, tags=['queue:high'])
        self.assertMetric('python_rq.queue.deferred', value=15, tags=['queue:high'])
        self.assertMetric('python_rq.queue.finished', value=20, tags=['queue:high'])


class TestRQInternals(unittest.TestCase):
    CHECK_NAME = 'python_rq'

    def test_init_defaults(self):
        """
        Ensure that default values are properly set
        """
        # config
        instances = [{
            'host': 'localhost',
            'port': '6379',
        }]
        # create check instance
        RQCheck = get_check_class(TestRQInternals.CHECK_NAME)
        rq_check = RQCheck(TestRQInternals.CHECK_NAME, {}, {}, instances)
        # test
        self.assertIn('socket_timeout', rq_check.instances[0])
        self.assertEqual(rq_check.instances[0]['socket_timeout'], 5)

    def test_get_workers_status(self):
        """
        Ensure that the workers status retrieval, returns the proper
        dictionary
        """
        # mocks
        workers = [
            'rq:worker:host.10000',
            'rq:worker:host.10001',
            'rq:worker:host.10002',
            'rq:worker:host.10003',
            'rq:worker:host.10004',
        ]
        states = {
            'rq:worker:host.10000': 'idle',
            'rq:worker:host.10001': 'started',
            'rq:worker:host.10002': 'busy',
            'rq:worker:host.10003': 'suspended',
            'rq:worker:host.10004': 'busy',
        }
        # config
        instances = [{
            'host': 'localhost',
            'port': '6379',
        }]
        # create check instance
        RQCheck = get_check_class(TestRQInternals.CHECK_NAME)
        rq_check = RQCheck(TestRQInternals.CHECK_NAME, {}, {}, instances)
        connection = mock.MagicMock()
        connection.smembers.return_value = workers
        connection.hget.side_effect = lambda x, y: states[x]
        # test
        result = rq_check._get_workers_status(connection)
        self.assertEqual(result, {'idle': 1, 'started': 1, 'busy': 2, 'suspended': 1})

    def test_get_queues_names(self):
        """
        Ensure that all queues names, except the 'failed' queue, are retrieved
        """
        # mocks
        queues = [
            'rq:queue:low',
            'rq:queue:high',
            'rq:queue:failed',
        ]
        # config
        instances = [{
            'host': 'localhost',
            'port': '6379',
        }]
        # create check instance
        RQCheck = get_check_class(TestRQInternals.CHECK_NAME)
        rq_check = RQCheck(TestRQInternals.CHECK_NAME, {}, {}, instances)
        connection = mock.MagicMock()
        connection.smembers.return_value = queues
        # test
        result = rq_check._get_queues_names(connection)
        self.assertEqual(result, ['low', 'high'])

    def test_get_queues_with_wrong_names(self):
        """
        Ensure that if there is a queue with a wrong name it will be discarded,
        while remaining queues are properly returned
        """
        # mocks
        queues = [
            'rq:queue:low',
            'rq:queue:high',
            'rq:queue:failed',
            'rq:quite:fast:queue',
            'rq:queue',
            'really_wrong_queue',
        ]
        # config
        instances = [{
            'host': 'localhost',
            'port': '6379',
        }]
        # create check instance
        RQCheck = get_check_class(TestRQInternals.CHECK_NAME)
        rq_check = RQCheck(TestRQInternals.CHECK_NAME, {}, {}, instances)
        connection = mock.MagicMock()
        connection.smembers.return_value = queues
        # test
        result = rq_check._get_queues_names(connection)
        self.assertEqual(result, ['low', 'high'])

    def test_get_cardinality_queue(self):
        """
        Ensure that any queues that begins with 'rq:queue' uses the Redis
        LLEN command
        """
        # config
        instances = [{
            'host': 'localhost',
            'port': '6379',
        }]
        # create check instance
        RQCheck = get_check_class(TestRQInternals.CHECK_NAME)
        rq_check = RQCheck(TestRQInternals.CHECK_NAME, {}, {}, instances)
        connection = mock.MagicMock()
        # test
        rq_check._get_cardinality(connection, 'default', 'rq:queue:')
        self.assertEqual(connection.llen.call_count, 1)

    def test_get_cardinality_others(self):
        """
        Ensure that any queues that doesn't begin with 'rq:queue' uses the Redis
        ZCARD command
        """
        # config
        instances = [{
            'host': 'localhost',
            'port': '6379',
        }]
        # create check instance
        RQCheck = get_check_class(TestRQInternals.CHECK_NAME)
        rq_check = RQCheck(TestRQInternals.CHECK_NAME, {}, {}, instances)
        connection = mock.MagicMock()
        # test
        rq_check._get_cardinality(connection, 'default', 'rq:wip:')
        rq_check._get_cardinality(connection, 'default', 'rq:deferred:')
        rq_check._get_cardinality(connection, 'default', 'rq:finished:')
        self.assertEqual(connection.zcard.call_count, 3)
