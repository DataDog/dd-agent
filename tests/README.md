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

All integrations, except for the kubernates and docker ones, have been moved to the [Integration SDK](https://github.com/DataDog/integrations-core). Please look there to see the Integrations Tests.


# Travis

Its configuration is stored in [.travis.yml](../.travis.yml).

It's running the exact same command described above (`rake ci:run[flavor]`), with the restriction of one flavor + version per build. (we use the [build matrix](http://docs.travis-ci.com/user/customizing-the-build/#Build-Matrix) to split flavors)

We use the newly released [docker-based infrastructure](http://blog.travis-ci.com/2014-12-17-faster-builds-with-container-based-infrastructure/).


# Appveyor

Its configuration is stored in [appveyor.yml](../appveyor.yml).

It's using the same command as Travis, `rake ci:run[flavor]`, but runs only tests with the `windows` attr: `@attr('windows', requires='flavor')`. It tests only Windows-specific checks, with python 2.7 (32 and 64 bits).

Third parties softwares are not build from source, instead it uses [pre-installed programs](http://www.appveyor.com/docs/installed-software#services-and-databases).

Appveyor is caching gems & pywin32 exe (needed for WMI), there is no custom caching.
