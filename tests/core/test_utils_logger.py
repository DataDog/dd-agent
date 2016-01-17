# stdlib
import logging
import unittest

# 3p
from mock import Mock

# datadog
from utils.logger import log_exceptions, RedactedLogRecord


class MockLoggingHandler(logging.Handler, object):
    """
    Mock logging handler to check for expected logs.
    """

    def __init__(self, *args, **kwargs):
        super(MockLoggingHandler, self).__init__(*args, **kwargs)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())

    def pop(self):
        """
        Return the last message logged.
        """
        if not self.messages:
            return None

        return self.messages.pop()


class TestUtilsLogger(unittest.TestCase):

    def test_log_exception(self):
        """
        Catch any exception and log it.
        """
        mock_logger = Mock()

        @log_exceptions(mock_logger)
        def raise_exception():
            """
            Raise an exception.
            """
            raise Exception(u"Bad exception.")

        self.assertRaises(Exception, raise_exception)
        self.assertTrue(mock_logger.exception.called)

    def test_api_key_log_obfuscation(self):
        """
        `RedactedLogRecord` custom LogRecord obfuscates API key logging.
        """
        # Initialize a logger with `RedactedLogRecord` custom LogRecord
        logging.LogRecord = RedactedLogRecord

        logger = logging.getLogger()
        handler = MockLoggingHandler()

        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # Attempt to log an API key
        def log_api_key():
            """
            Log things, including an API key.
            """
            mtype = "metrics"
            endpoint = "dd_url"
            url = "https://x-x-x-app.agent.datadog.com/intake/?api_key=foobar"

            logger.info(
                u"Sending %s to endpoint %s at %s",
                mtype, endpoint, url
            )

        log_api_key()

        # API key is obfuscated
        result = handler.pop()
        expected_result = u"Sending metrics to endpoint dd_url at "\
            "https://x-x-x-app.agent.datadog.com/intake/?api_key=*************************oobar"

        self.assertEquals(result, expected_result)
