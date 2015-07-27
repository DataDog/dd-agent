Testing & dd-agent
==================

[![Build Status](https://travis-ci.org/DataDog/dd-agent.svg)](https://travis-ci.org/DataDog/dd-agent) [![Build status](https://ci.appveyor.com/api/projects/status/y7v5la94393mi5lc?svg=true)](https://ci.appveyor.com/project/Datadog/dd-agent)

# Lint

Your code should always be clean when doing `rake lint`. It runs `flake8`, ignoring these [rules](../tox.ini).


# Organisation of the tests directory

```bash
tests
├── checks # tests of checks.d/*
│   ├── integration # contains all real integration tests (run on Travis/Appveyor)
│   ├── mock # contains mocked tests (run on Travis)
│   └── fixtures # files needed by tests (conf files, mocks, ...)
└── core # core agent tests (unit and integration tests, run on Travis)
    └── fixtures # files needed by tests
```

We use [rake](http://docs.seattlerb.org/rake/) & [nosetests](https://nose.readthedocs.org/en/latest/) to manage the tests.

To run individual tests:
```
# Whole file
nosetests tests/checks/mock/test_system_swap.py
# Whole class
nosetests tests/checks/mock/test_system_swap.py:SystemSwapTestCase
# Single test case
nosetests tests/checks/mock/test_system_swap.py:SystemSwapTestCase.test_system_swap
```

To run a specific ci flavor (our way of splitting tests, for more details see [integration tests](#integration-tests)):
```
# Run the flavor my_flavor
rake ci:run[my_flavor]
```

# Unit tests

They are split in different flavors:
```
# Run the mock/unit core tests
rake ci:run

# Run mock/unit checks tests
rake ci:run[checks_mock]

# Agent core integration tests (can take more than 5min)
rake ci:run[core_integration]
```


# Integration tests

They ensure that the agent is correctly talking to third party software which is necessary for most checks.

They are great because they mimic a real setup where someone would enable a check on a machine with this service running. Using mocks or pre-saved responses often hides corner-cases and are the source of lots of issues.

We run these tests by creating a build machine "flavor" (see Travis/Appveyor section), basically each flavor is defined by the third party software we install on this machine.

Most of the times `flavor == check_name`.

Each flavor is defined in `ci/flavor.rb`, and we set different steps for running the flavor build :

* **before_install** needs to be run before installation
* **install** installs the 3p software
* **before_script** generally setups the software and launch it in background
* **script** runs nosetests with a filter (see how to write tests)
* **cleanup** stops the software and remove unnecessary data (not running on Travis/Appveyor, because the buildboxes are disposable)
* **before_cache** is run on Travis _(not run on Appveyor)_ to delete logs files, configuration files, ... before caching
* **cache** tars and uploads the cache to S3 _(not run on Appveyor)_

Your test cases must be written in `tests/test_flavor.py` and they must use the nose `attr` decorator to be filtered by the flavors.

```
from nose.plugins.attrib import attr

@attr(requires='bone')
class TestCheckBone(unittest.TestCase):
    def test_fetch(self):
```

To run the tests locally:
```
rake ci:run[bone]
```

To create rake tasks for a new flavor you can use this [skeleton file](../ci/skeleton.rb).


# Travis

Its configuration is stored in [.travis.yml](../.travis.yml).

It's running the exact same command described above (`rake ci:run[flavor]`), with the restriction of one flavor + version per build. (we use the [build matrix](http://docs.travis-ci.com/user/customizing-the-build/#Build-Matrix) to split flavors)

Travis is configured to cache python libs and ruby gems between runs. We use a custom cache for third party software dependencies (PostgreSQL, Apache, ...), which are built from source.

We use the newly released [docker-based infrastructure](http://blog.travis-ci.com/2014-12-17-faster-builds-with-container-based-infrastructure/).

To add a new flavour, append your `TRAVIS_FLAVOR` to [.travis.yml](../.travis.yml).


# Appveyor

Its configuration is stored in [appveyor.yml](../appveyor.yml).

It's using the same command as Travis, `rake ci:run[flavor]`, but runs only tests with the `windows` attr: `@attr('windows', requires='flavor')`. It tests only Windows-specific checks, with python 2.7 (32 and 64 bits).

Third parties softwares are not build from source, instead it uses [pre-installed programs](http://www.appveyor.com/docs/installed-software#services-and-databases).

Appveyor is caching gems & pywin32 exe (needed for WMI), there is no custom caching.

To add a new flavour, append the flavor to the comma-separated list of `FLAVORS` to [appveyor.yml](../appveyor.yml).


# Add an integration test

Please read first the [integration test description](#integration-tests).

It's really straightforward if the integration you want to add can be easily installed from source. Otherwise, it might be more complicated.

Copy `ci/skeleton.rb` in `ci/flavor.rb` (`flavor` being the name of your check). Then you can follow the example of `ci/lighttpd.rb` to see how to install your `flavor` and configure it.

All configuration files needed for the ci to run should be in `ci/resources/flavor/`, and then before the test run copied to the right directory (generally `$INTEGRATIONS_DIR/flavor_version`). `$VOLATILE_DIR` should receive all temporary files (such as pid file, data files, ...), and `$INTEGRATIONS_DIR/flavor_version` should contain the program once compiled, ready to be cached and speed up the build on Travis.

Then add your `flavor` in [Rakefile](../Rakefile) (`require ./ci/flavor`).

You can test it by runnnig `rake ci:run[flavor]`.
