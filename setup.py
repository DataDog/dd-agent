# stdlib
from datetime import date
import os
import sys

# 3p
from setuptools import find_packages, setup
from requests.certs import where

# project
from config import get_version
from utils.jmx import JMX_FETCH_JAR_NAME

# Extra arguments to pass to the setup function
extra_args = {}

# Prereqs of the build. Won't get installed when deploying the egg.
setup_requires = []

# Prereqs of the install. Will install when deploying the egg.
install_requires = []

# Modified on mac
app_name = 'datadog-agent'
# plist (used only on mac)
plist = None

if sys.platform == 'win32':
    from glob import glob
    # noqa for flake8, these imports are probably here to force packaging of these modules
    import py2exe  # noqa
    import pysnmp_mibs  # noqa
    import pyVim  # noqa
    import pyVmomi  # noqa

    # That's just a copy/paste of requirements.txt
    for reqfile in ('requirements.txt', 'requirements-opt.txt'):
        with open(reqfile) as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                # we skip psycopg2 now because don't want to install PG
                # on windows
                if 'psycopg2' in line:
                    continue
                install_requires.append(line)

    # windows-specific deps
    install_requires.append('pywin32==217')

    # Modules to force-include in the exe
    include_modules = [
        # 3p
        'wmi',
        'win32service',
        'win32serviceutil',
        'win32event',
        'simplejson',
        'adodbapi',
        'pycurl',
        'tornado.curl_httpclient',
        'pymongo',
        'pymysql',
        'psutil',
        'pg8000',
        'redis',
        'requests',
        'pysnmp',
        'pysnmp.smi.mibs.*',
        'pysnmp.smi.mibs.instances.*',
        'pysnmp_mibs.*',
        'pysnmp.entity.rfc3413.oneliner.*',
        'pyVim.*',
        'pyVmomi.*',
        'paramiko',
        'Crypto',
        'winrandom',
        'uptime',
        'pythoncom',

        # agent
        'checks.network_checks',
        'checks.wmi_check',
        'checks.libs.vmware.*',
        'httplib2',
        'utils.containers',

        # pup
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
                'excludes': ['numpy'],
                'dll_excludes': ["IPHLPAPI.DLL", "NSI.dll",  "WINNSI.DLL",  "WTSAPI32.dll"],
                'ascii':False,
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
            ('jmxfetch', [r'checks\libs\%s' % JMX_FETCH_JAR_NAME]),
            ('gohai', [r'gohai\gohai.exe']),
            ('', [where()]),  # CA certificates bundled with `requests`
        ],
    }

elif sys.platform == 'darwin':
    app_name = 'Datadog Agent'

    from plistlib import Plist
    plist = Plist.fromFile(os.path.dirname(os.path.realpath(__file__)) + '/packaging/Info.plist')
    plist.update(dict(
        CFBundleGetInfoString="{0}, Copyright (c) 2009-{1}, Datadog Inc.".format(
            get_version(), date.today().year),
        CFBundleVersion=get_version()
    ))

    extra_args = {
        'app': ['gui.py'],
        'data_files': [
            'images',
            'status.html',
        ],
        'options': {
            'py2app': {
                'optimize': 0,
                'iconfile': 'packaging/Agent.icns',
                'plist': plist
            }
        }
    }


setup(
    name=app_name,
    version=get_version(),
    description="DevOps' best friend",
    author='DataDog',
    author_email='dev@datadoghq.com',
    url='http://www.datadoghq.com',
    install_requires=install_requires,
    setup_requires=setup_requires,
    packages=find_packages(),
    include_package_data=True,
    test_suite='nose.collector',
    zip_safe=False,
    **extra_args
)
