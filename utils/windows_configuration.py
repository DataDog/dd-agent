# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging
import os
import shutil
import tempfile
try:
    import _winreg
except ImportError:
    pass


WINDOWS_REG_PATH = 'SOFTWARE\\Datadog\\Datadog Agent'
SDK_REG_PATH = WINDOWS_REG_PATH + '\\Integrations\\'


log = logging.getLogger(__name__)

config_attributes = ['api_key', 'tags', 'hostname', 'proxy_host', 'proxy_port', 'proxy_user', 'proxy_password']

def remove_registry_conf():
    try:
        with _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                             WINDOWS_REG_PATH, 0, _winreg.KEY_WRITE) as reg_key:
            for attribute in config_attributes:
                try:
                    _winreg.DeleteValue(reg_key, attribute)
                except Exception as e:
                    log.error("Failed to delete value %s %s", attribute, str(e))
                    # it's ok if it's not there.
                    pass
    except Exception:
        # also OK if the whole tree isn't there
        pass

def get_registry_conf(agentConfig):
    registry_conf = {}
    try:
        with _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                             WINDOWS_REG_PATH) as reg_key:
            for attribute in config_attributes:
                option = _winreg.QueryValueEx(reg_key, attribute)[0]
                if option != '':
                    registry_conf[attribute] = option
    except (ImportError, WindowsError) as e:
        # don't log this as an error.  Since the keys are deleted after
        # they're used, they're almost certain to not be there.
        # however, log as `info` so it will show by default after install
        # (i.e. before user has had a chance to change the config file)
        # so it can be seen if necessary
        log.info('Unable to get config keys from Registry (this is probably OK): %s', e)

    return registry_conf

def get_sdk_integration_path(hkey, reg_path):
    with _winreg.OpenKey(hkey, reg_path) as reg_key:
        directory = _winreg.QueryValueEx(reg_key, "InstallPath")[0]

    return directory

def get_windows_sdk_check(name):
    sdk_reg_path = SDK_REG_PATH + name
    try:
        directory = get_sdk_integration_path(_winreg.HKEY_LOCAL_MACHINE, sdk_reg_path)
        return (os.path.join(directory, 'check.py'),
                os.path.join(directory, 'manifest.json'))
    except WindowsError:
        pass

    return None, None

def subkeys(key):
    i = 0
    while True:
        try:
            subkey = _winreg.EnumKey(key, i)
            yield subkey
            i += 1
        except WindowsError:
            break

def get_sdk_integration_paths():
    integrations = {}
    try:
        with _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, SDK_REG_PATH) as reg_key:
            for integration_subkey in subkeys(reg_key):
                integration_name = integration_subkey.split('\\')[-1]
                try:
                    directory = get_sdk_integration_path(reg_key, integration_subkey)
                    integrations[integration_name] = directory
                except WindowsError as e:
                    log.error('Unable to get keys from Registry for %s: %s', integration_name, e)
    except WindowsError as e:
        # don't log this as an error.  Unless someone has installed a standalone
        # integration, this key won't be present.
        log.debug('Unable to get config keys from Registry: %s', e)

    return integrations

def update_conf_file(registry_conf, config_path):
    config_dir = os.path.dirname(config_path)
    config_bkp = os.path.join(config_dir, 'datadog.conf.bkp')
    try:
        if os.path.exists(config_bkp):
            os.remove(config_bkp)
        shutil.copy(config_path, config_bkp)
    except OSError as e:
        log.debug('Unable to back up datadog.conf: %s', e)
    temp_config, temp_config_path = tempfile.mkstemp(prefix='config-', text=True)
    temp_config = os.fdopen(temp_config, 'w')
    log.debug('Temporary conf path: %s', temp_config_path)
    with open(config_path, 'r') as f:
        for line in f:
            for k, v in registry_conf.iteritems():
                if k + ":" in line:
                    line = '{}: {}\n'.format(k, v)
            temp_config.write(line)
    temp_config.close()
    try:
        os.remove(config_path)
        os.rename(temp_config_path, config_path)
    except OSError as e:
        log.exception('Unable to save new datadog.conf')
        raise
    else:
        log.debug('Successfully saved the new datadog.conf')
