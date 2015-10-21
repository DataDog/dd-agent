# stdlib
from functools import wraps
from pprint import pprint
import inspect
import logging
import os
import sys


log = logging.getLogger(__name__)


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


def logged(func):
    """
    Add DEBUG logging to a function.
    """
    @wraps(func)
    def wrapper(*params, **kwargs):
        fc = "%s(%s)" % (func.__name__, ', '.join(
            [a.__repr__() for a in params] +
            ["%s = %s" % (a, b) for a, b in kwargs.items()]
        ))
        log.debug("%s called" % fc)
        return func(*params, **kwargs)
    return wrapper


def run_check(name, path=None):
    """
    Test custom checks on Windows.
    """
    from config import get_confd_path
    from util import get_os

    # Read the config file
    confd_path = path or os.path.join(get_confd_path(get_os()), '%s.yaml' % name)

    try:
        f = open(confd_path)
    except IOError:
        raise Exception('Unable to open configuration at %s' % confd_path)

    config_str = f.read()
    f.close()

    # Run the check
    check, instances = get_check(name, config_str)
    if not instances:
        raise Exception('YAML configuration returned no instances.')
    for instance in instances:
        check.check(instance)
        if check.has_events():
            print "Events:\n"
            pprint(check.get_events(), indent=4)
        print "Metrics:\n"
        pprint(check.get_metrics(), indent=4)


def get_check(name, config_str):
    from checks import AgentCheck
    from config import get_checksd_path
    from util import get_os

    checksd_path = get_checksd_path(get_os())
    if checksd_path not in sys.path:
        sys.path.append(checksd_path)
    check_module = __import__(name)
    check_class = None
    classes = inspect.getmembers(check_module, inspect.isclass)
    for name, clsmember in classes:
        if AgentCheck in clsmember.__bases__:
            check_class = clsmember
            break
    if check_class is None:
        raise Exception("Unable to import check %s. Missing a class that inherits AgentCheck" % name)

    agentConfig = {
        'version': '0.1',
        'api_key': 'tota'
    }

    return check_class.from_yaml(yaml_text=config_str, check_name=name,
                                 agentConfig=agentConfig)
