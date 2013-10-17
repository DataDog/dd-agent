import platform
import sys
from config import *
from jmxfetch import JMX_FETCH_JAR_NAME

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
        'tornado==3.0.1',
        'pywin32==217',
        'wmi==1.4.9',
        'simplejson==2.6.1',
        'mysql-python==1.2.3',
        'pymongo==2.3',
        'psycopg2==2.4.5',
        'python-memcached==1.48',
        'redis==2.6.2',
        'adodbapi'
        'elementtree',
        'pycurl',
        'MySQLdb',
    ])

    # Modules to force-include in the exe
    include_modules = [
        # 3p
        'win32service',
        'win32serviceutil',
        'win32event',
        'simplejson',
        'adodbapi',
        'elementtree.ElementTree',
        'pycurl',
        'tornado.curl_httpclient',
        'pymongo',
        'MySQLdb',

        # agent
        'checks.services_checks',
        'checks.libs.httplib2',

        # pup
        'pup',
        'pup.pup',
        'tornado.websocket',
        'tornado.web',
        'tornado.ioloop',
    ]

    class Target(object):
        def __init__(self, **kw):
            self.__dict__.update(kw) 
            self.version = get_version()
            self.company_name = 'Datadog, Inc.'
            self.copyright = 'Copyright 2013 Datadog, Inc.'
            self.cmdline_style = 'pywin32'

    agent_svc = Target(name='Datadog Agent', modules='win32.agent', dest_base='ddagent')

    extra_args = {
        'options': {
            'py2exe': {
                'includes': ','.join(include_modules),
                'optimize': 0,
                'compressed': True,
                'bundle_files': 3,
            },
        },
        'console': ['win32\shell.py'],
        'service': [agent_svc],
        'windows': [{'script': 'win32\gui.py',
                     'dest_base': "agent-manager",
                     'uac_info': "requireAdministrator", # The manager needs to be administrator to stop/start the service
                     'icon_resources': [(1, r"packaging\datadog-agent\win32\install_files\dd_agent_win_256.ico")],
                     }],
        'data_files': [
            ("Microsoft.VC90.CRT", glob(r'C:\Python27\redist\*.*')),
            ('pup', glob('pup/pup.html')),
            ('pup', glob('pup/status.html')),
            ('pup/static', glob('pup/static/*.*')),
            ('jmxfetch', glob('checks/libs/%s' % JMX_FETCH_JAR_NAME)),
        ],
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
