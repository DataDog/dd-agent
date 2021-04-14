# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

from config import get_version

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='datadog_agent_tk',
    # Version should always match one from an agent release
    version=get_version(),
    description='The Datadog Agent Toolkit',
    long_description=long_description,
    keywords='datadog agent check toolkit',

    # The project's main homepage.
    url='https://github.com/DataDog/dd-agent',

    # Author details
    author='Datadog',
    author_email='packages@datadoghq.com',

    # License
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],


    # Include all we need from the agent to run tests and
    # execute checks in a dedicated virtualenv.
    packages=find_packages(exclude=[
        "tests.checks.fixtures*",
        "tests.checks.mock*",
        "tests.core*",
        "dogstream",
        "venv",
        "win32",
    ]),

    # These are plain python modules, not packages, we need
    # to list them manually to include in the wheel.
    py_modules=[
        "config",
        "util",
        "tests.checks.common",
        "aggregator"
    ],

    # This is more than we would need but this is a POC, so...
    install_requires=[
        'requests==2.11.1',
        'pyyaml==3.11',
        'simplejson==3.6.5',
        'docker-py==1.10.6',
        'python-etcd==0.4.5',
        'python-consul==0.4.7',
        'kazoo==2.2.1',
    ],
)
