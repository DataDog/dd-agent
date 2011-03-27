#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
from config import get_version

from distutils.command.install import INSTALL_SCHEMES

setup(name='datadog-agent',
      version=get_version(),
      description='Datatadog monitoring agent',
      author='Datadog',
      author_email='info@datadoghq.com',
      url='http://datadoghq.com/',
      packages=['checks', 'checks/db', 'resources'],
      package_data={'checks': ['libs/*']},
      scripts=['agent.py', 'daemon.py', 'minjson.py', 'util.py', 'emitter.py', 'config.py'],
      data_files=[('/etc/dd-agent/', ['datadog.conf.example']), 
                  ('/etc/init.d', ['redhat/datadog-agent'])]
     )
