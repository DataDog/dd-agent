import platform
import sys
from config import *

try:
    from setuptools import setup, find_packages

    # required to build the cython extensions
    from distutils.extension import Extension

except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

# Extra arguments to pass to the setup function
extra_args = {}

# Prereqs of the build. Won't get installed when deploying the egg.
setup_requires = [
]

# Prereqs of the install. Will install when deploying the egg.
install_requires=[
]

if sys.platform == 'win32':
    from glob import glob
    import py2exe
    install_requires.extend([
        'tornado==2.1',
        'pywin32==217',
        'wmi==1.4.9',
        'simplejson==2.6.1',
        'mysql-python==1.2.3',
        'pymongo==2.3',
        'psycopg2==2.4.5',
        'python-memcached==1.48',
        'redis==2.6.2',
        'adodbapi'
        'elementtree'
    ])

    # Modules to force-include in the exe
    include_modules = [
        # 3p
        'win32service',
        'win32serviceutil',
        'win32event',
        'simplejson',
        'adodbapi',
        'elementtree',

        # agent
        'checks.services_checks',
        'checks.libs.httplib2',
    ]

    class Target(object):
        def __init__(self, **kw):
            self.__dict__.update(kw) 
            self.version = get_version()
            self.company_name = 'Datadog, Inc.'
            self.copyright = 'Copyright 2012 Datadog, Inc.'
            self.cmdline_style = 'pywin32'

    agent_svc = Target(name='Datadog Agent', modules='win32.agent')

    extra_args = {
        'options': {
            'py2exe': {
                'includes': ','.join(include_modules),
                'optimize': 2,
                'compressed': 1,
                'bundle_files': 1,
            },
        },
        'console': ['win32\shell.py'],
        'service': [agent_svc],
        'zipfile': None,
        'data_files': [("Microsoft.VC90.CRT", glob(r'C:\Python27\redist\*.*'))],
    }

setup(
    name='datadog-agent',
    version=get_version(),
    description="DevOps' best friend",
    author='DataDog',
    author_email='dev@datadoghq.com',
    url='http://www.datadoghq.com',
    install_requires=install_requires,
    setup_requires=setup_requires,
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='nose.collector',
    zip_safe=False,
    **extra_args
)
