from config import get_checksd_path
import sys

def load_check(name, config, agentConfig):
    checksd_path = get_checksd_path()
    if checksd_path not in sys.path:
        sys.path.append(checksd_path)

    check_module = __import__(name)
    check_cls = getattr(check_module, check_module.CHECK)
    init_config = config.get('init_config', None)

    # init the check class
    return check_cls(name, init_config=init_config, agentConfig=agentConfig)
