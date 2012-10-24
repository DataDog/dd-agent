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
    ''' Load the data files from checks.d '''
    import glob
    curpath = os.path.dirname(os.path.join(os.path.realpath(__file__)))
    checksd_path = os.path.join(curpath, 'checks.d')
    checksd_glob = os.path.join(checksd_path, '*.py')

    # Find all py files in the checks.d directory
    checks = []
    for check in glob.glob(checksd_glob):
        check = os.path.basename(check)
        checks.append(check)

    return [('share/datadog/agent/checks.d', ['checks.d/%s' % c for c in checks])]

if __name__ == "__main__":
    setup(name='datadog-agent-lib',
          version=getVersion(),
          description='Datatadog monitoring agent check library',
          author='Datadog',
          author_email='info@datadoghq.com',
          url='http://datadoghq.com/',
          packages=['checks', 'checks/db', 'checks/system', 'dogstream','pup', 'yaml', 'checks/libs/httplib2'],
          package_data={'checks': ['libs/*'], 'pup' : ['static/*', 'pup.html']},
          data_files=getDataFiles()
         )
