#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

import os, sys

from distutils.command.install import INSTALL_SCHEMES

def getVersion():
    try:
        from config import get_version
    except ImportError:
        import sys
        sys.path.append("../..")
        from config import get_version
   
    return get_version()

def printVersion():
    print getVersion()

def getDataFiles():
    ''' Load the config data files '''
    agent_config = ('/etc/dd-agent/', ['../../datadog.conf.example'])

    # Include all of the .yaml.example files from conf.d
    import glob
    curpath = os.path.dirname(os.path.join(os.path.realpath(__file__)))
    confd_path = os.path.join(curpath, 'conf.d')
    confd_glob = os.path.join(confd_path, '*.yaml.example')

    # Find all py files in the checks.d directory
    configs = []
    for config in glob.glob(confd_glob):
        config = os.path.basename(config)
        configs.append(config)
    confd = ('/etc/dd-agent/conf.d/', ['conf.d/%s' % c for c in configs])
    return [agent_config, confd]

if __name__ == "__main__":

    setup(name='datadog-agent-base',
          version=getVersion(),
          description='Datatadog monitoring agent',
          author='Datadog',
          author_email='info@datadoghq.com',
          url='http://datadoghq.com/',
          packages=['resources', 'compat'],
          scripts=['agent.py', 'daemon.py', 'minjson.py', 'util.py', 
                    'emitter.py', 'config.py', 'graphite.py', 'modules.py'],
          data_files=getDataFiles()
         )
