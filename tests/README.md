Testing & dd-agent
==================

[![Build Status](https://travis-ci.org/DataDog/dd-agent.svg)](https://travis-ci.org/DataDog/dd-agent)

# Lint

Your code should always be clean when doing `rake lint`.
The pylint configuration is not really aggressive so you're most welcome to use your own pylint config or tools like pep8 or pyflakes (we plan to plug in more restrictive stuff about that to try to keep sane defaults in the codebase)

# Unit tests

They mainly concern the core of the Datadog agent:

* how metrics are handled/submitted/aggregated
* how we run checks, handle failures
* more generic testing on the agent behavior and resilience
* system-oriented checks (may be considered as integration tests..)

```
# Run the suite
rake ci:run
```

# Integration tests

They ensure that the agent is correctly talking to third party software which is necessary for most checks.

They are great because they mimic a real setup where someone would enable a check on a machine with this service running. Using mocks or pre-saved responses often hides corner-cases and are the source of lots of issues.

We run these tests by creating a build machine "flavor" (see Travis section), basically each flavor is defined by the third party software we install on this machine.

Most of the times `flavor == check_name`

Each flavor is defined in `ci/flavor.rb`, and we set different steps for running the flavor build :

* **before_install** needs to be run before installation
* **install** installs the 3p software
* **before_script** generally setups the software and launch it in background
* **script** runs nosetests with a filter (see how to write tests)
* **cleanup** stops the software and remove unnecessary data (not running on Travis, because the buildboxes are disposable)

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

To create rake tasks for a new flavor you can use this [skeleton file](https://github.com/DataDog/dd-agent/blob/master/ci/skeleton.rb)


# Travis

It's only running the exact same command described above. With the restriction of one flavor + version per build.

We use the newly released [docker-based infrastructure](http://blog.travis-ci.com/2014-12-17-faster-builds-with-container-based-infrastructure/)

In the future, if Travis allows more custom docker containers, we might consider moving from rake to Dockerfiles to setup the flavors.

Your Pull Request **must** always pass the Travis tests before being merged, if you think the error is not due to your changes, you can have a talk with us on IRC (#datadog freenode) or send us an email to support _at_ datadoghq _dot_ com)
