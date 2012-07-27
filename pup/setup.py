# setup.py for Datadog Pup.py package.

from setuptools import setup, find_packages
import os

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
	    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
	name = "pup",
	version = "0.1",
	packages = find_packages(),

	# install_requires, then list what might be needed.
	
	author = "Datadog, Inc.",
	author_email = "packages@datadoghq.com",
	license = "BSD",
	description = ("Collects and displays metrics at localhost from dogapi, StatsD, dd-agent and more."),
	long_description=read('README'),
	keywords = "datadog data",
	include_package_data = True,
	classifiers = [
		"Development Status :: 1 - Planning",
		"Topic :: Utilities",
	],
)
