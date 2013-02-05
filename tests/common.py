from checks import AgentCheck
from config import get_checksd_path, get_confd_path
from util import get_os
from pprint import pprint
import sys
import inspect
import os
import signal

def load_check(name, config, agentConfig):
    checksd_path = get_checksd_path(get_os())
    if checksd_path not in sys.path:
        sys.path.append(checksd_path)

    check_module = __import__(name)
    check_class = None
    classes = inspect.getmembers(check_module, inspect.isclass)
    for name, clsmember in classes:
        if clsmember == AgentCheck:
            continue
        if issubclass(clsmember, AgentCheck):
            check_class = clsmember
            if AgentCheck in clsmember.__bases__:
                continue
            else:
                break
    if check_class is None:
        raise Exception("Unable to import check %s. Missing a class that inherits AgentCheck" % name)

    init_config = config.get('init_config', None)
    instances = config.get('instances')

    # init the check class
    try:
        return check_class(name, init_config=init_config, agentConfig=agentConfig, instances=instances)
    except:
        # Backwards compatitiblity for old checks that don't support the
        # instances argument.
        c = check_class(name, init_config=init_config, agentConfig=agentConfig)
        c.instances = instances
        return c

def kill_subprocess(process_obj):
    try:
        process_obj.terminate()
    except AttributeError:
        # py < 2.6 doesn't support process.terminate()
        if get_os() == 'windows':
            import ctypes
            PROCESS_TERMINATE = 1
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False,
                process_obj.pid)
            ctypes.windll.kernel32.TerminateProcess(handle, -1)
            ctypes.windll.kernel32.CloseHandle(handle)
        else:
            os.kill(process_obj.pid, signal.SIGKILL)

def get_check(name, config_str):
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

def run_check(name, path=None):
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
