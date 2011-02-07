#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
from agent import get_config

agentConfig, _ = get_config()

setup(name='datadog-agent',
      version=agentConfig['version'],
      description='Datatadog monitoring agent',
      author='Datadog',
      author_email='info@datadoghq.com',
      url='http://datadoghq.com/',
      packages=['checks'],
      scripts=['agent.py', 'daemon.py', 'minjson.py', 'common.py', 'emitter.py', 'config.py'],
      data_files=[('/etc/dd-agent/', ['datadog.conf.example']), ('/etc/init.d', ['redhat/datadog-agent'])]
     )
