#!/usr/bin/env python

from distutils.core import setup

setup(name='datadog-agent',
      version='1.9.0',
      description='Datatadog monitoring agent',
      author='Datadog',
      author_email='info@datadoghq.com',
      url='http://datadoghq.com/',
      packages=['checks'],
      scripts=['agent.py', 'daemon.py', 'minjson.py'],
      data_files=[('/etc/dd-agent/', ['datadog.conf.example']), ('/etc/init.d', ['redhat/datadog-agent'])]
     )
