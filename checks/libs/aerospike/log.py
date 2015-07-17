yaml_flag = True
try:
    import yaml
except ImportError:
    yaml_flag = False
log_mode = None

from constants import CONFIG_PATH


def get_log_mode():

    if yaml_flag:
        global log_mode
        f = open(CONFIG_PATH, 'r')
        data = yaml.load(f)
        first_instance = data['instances'][0]
        log_mode = first_instance['debug_mode']
        return log_mode
    return None


def print_log(obj, message, error_flag=False):

    global log_mode
    if log_mode is None:
        mode = get_log_mode()
    if log_mode:
        if error_flag:
            obj.log.error('DEBUG:   ' + str(message))
        else:
            obj.log.debug('DEBUG:   ' + str(message))
    else:
        if error_flag:
            obj.log.error(message)
