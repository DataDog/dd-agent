# stdlib
from functools import wraps
import re


API_KEY_PATTERN = re.compile('api_key=*\w+(\w{5})')
API_KEY_REPLACEMENT = r'api_key=*************************\1'


def log_exceptions(logger):
    """
    A decorator that catches any exceptions thrown by the decorated function and
    logs them along with a traceback.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
            except Exception:
                logger.exception(
                    u"Uncaught exception while running {0}".format(func.__name__)
                )
                raise
            return result
        return wrapper
    return decorator


def log_no_api_key(logger):
    """
    A decorator that patches a logger in a method scope to obfuscate API keys.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Patch logger
            tmp = logger._log
            logger._log = _obfuscate_api_keys(logger._log)

            # Run method
            result = func(*args, **kwargs)

            # Unpatch logger
            logger._log = tmp

            return result
        return wrapper
    return decorator


def _obfuscate_api_keys(func):
    """
    A decorator that obfuscate API keys among the method arguments.
    """
    @wraps(func)
    def wrapper(level, msg, args, **kwargs):
        # Obfuscate API keys among logger arguments
        sanitized_args = [re.sub(API_KEY_PATTERN, API_KEY_REPLACEMENT, arg)
                          if isinstance(arg, basestring) else arg
                          for arg in args]

        return func(level, msg, tuple(sanitized_args), **kwargs)
    return wrapper
