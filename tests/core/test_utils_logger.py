# stdlib
import unittest

# 3p
from mock import Mock

# datadog
from utils.logger import log_exceptions, log_no_api_key


class TestUtilsLogger(unittest.TestCase):

    def test_log_exception(self):
        """
        Catch any exception and log it.
        """
        mock_logger = Mock()

        @log_exceptions(mock_logger)
        def raise_exception():
            """
            Raise an exception
            """
            raise Exception(u"Bad exception.")

        self.assertRaises(Exception, raise_exception)
        self.assertTrue(mock_logger.exception.called)

    def test_log_no_api(self):
        """
        Log no API key in the method scope.
        """
        # Mock a logger
        _logging = []
        mock_logger = Mock(
            _log=lambda level, msg, args, **kwargs: _logging.append(args),
            get_logging=lambda: _logging.pop(),
        )

        #
        def log_args(*args):
            """
            Log arguments and return logging.
            """
            level = 0
            msg = u""

            mock_logger._log(level, msg, *args)

        log_arg_wo_api_keys = log_no_api_key(mock_logger)(log_args)

        # Run tests
        args_to_log = (
            "Sending metrics to endpoint dd_url at https://x-x-x-app.agent.datadog.com/intake/?api_key=foobar",  # noqa
            "200 POST /intake/?api_key=foobar (127.0.0.1) 67.70ms",
            "Transaction 1 completed",
        )

        args_wo_api_keys = (
            "Sending metrics to endpoint dd_url at https://x-x-x-app.agent.datadog.com/intake/?api_key=*************************oobar",  # noqa
            "200 POST /intake/?api_key=*************************oobar (127.0.0.1) 67.70ms",
            "Transaction 1 completed",
        )

        log_arg_wo_api_keys(args_to_log)
        self.assertEquals(mock_logger.get_logging(), args_wo_api_keys)

        log_args(args_to_log)
        self.assertEquals(mock_logger.get_logging(), args_to_log)
