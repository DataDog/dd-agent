#!/usr/bin/env python

from distutils.core import setup

setup(name='datadog-agent',
      version='1.9.0',
      description='Datatadog monitoring agent',
      author='Datadog',
      author_email='datadog@datadoghq.com',
      url='http://www.datadoghq.com/',
      packages=['checks'],
      scripts=['agent.py', 'daemon.py', 'minjson.py'],
      data_files=[('/etc/dd-agent/', ['config.cfg.example'])]
     )
