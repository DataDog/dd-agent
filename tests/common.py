from checks import AgentCheck
from config import get_checksd_path
import sys
import inspect

def load_check(name, config, agentConfig):
    checksd_path = get_checksd_path()
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

    init_config = config.get('init_config', None)

    # init the check class
    return check_class(name, init_config=init_config, agentConfig=agentConfig)
