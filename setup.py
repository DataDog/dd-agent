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

# Prereqs of the build. Won't get installed when deploying the egg.
setup_requires = [
]

# Prereqs of the install. Will install when deploying the egg.
install_requires=[
]

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
)
