[![Build Status](https://travis-ci.org/DataDog/dd-agent.svg?branch=master)](https://travis-ci.org/DataDog/dd-agent)

# All Agent Checks are now frozen in preparation for the release of the [Integration SDK](https://github.com/DataDog/dd-agent/wiki/Integration-SDK).
## We will review and merge a few more PRs, but no new PRs will be accepted.
## All changes to checks from here on out should go to the [integrations-core repo](https://github.com/datadog/integrations-core) and all new checks should go to the [integrations-extras repo](https://github.com/datadog/integrations-extras). To learn more about how to contribute to them, please check out our [documentation](http://docs.datadoghq.com/guides/integration_sdk/).

The Datadog Agent faithfully collects events and metrics and brings
them to [Datadog](https://app.datadoghq.com) on your behalf so that
you can do something useful with your monitoring and performance data.

You're looking at the source code right now. We provide a number of
[pre-packaged binaries](https://app.datadoghq.com/account/settings#agent) for your convenience.

# [Change log](https://github.com/DataDog/dd-agent/blob/master/CHANGELOG.md)

# How to contribute code

First of all and most importantly, **thank you** for sharing.

If you want to submit code, please fork this repository and submit pull requests against the `master` branch.
For more information, please read our [contributing guidelines](CONTRIBUTING.md).

Please note that the Agent is licensed for simplicity's sake
under a simplified BSD license, as indicated in the `LICENSE` file.
Exceptions are marked with LICENSE-xxx where xxx is the component name.
If you do **not** agree with the licensing terms and wish to contribute code nonetheless,
please email us at <info@datadoghq.com> before submitting your
pull request.

# [Integration SDK](https://github.com/DataDog/integrations-core)

All integrations, except for the kubernates and docker ones, have been moved to the [Integration SDK](https://github.com/DataDog/integrations-core). Please look there to see and contribute to any Integrations.

## Setup your environment

Required:
- python 2.7
- bundler (to get it: `gem install bundler`)

```
# Clone the repository
git clone git@github.com:DataDog/dd-agent.git

# Create a virtual environment and install the dependencies:
cd dd-agent
bundle install
rake setup_env

# Activate the virtual environment
source venv/bin/activate

# Lint
bundle exec rake lint

# Run a flavored test
bundle exec rake ci:run[apache]
```

## Test suite

More about how to write tests and run them [here](tests/README.md)

# How to configure the Agent

If you are using packages on linux, the main configuration file lives
in `/etc/dd-agent/datadog.conf`. Per-check configuration files are in
`/etc/dd-agent/conf.d`. We provide an example in the same directory
that you can use as a template.

# How to write your own checks

Writing your own checks is easy using our checks.d interface. Read more about
how to use it on our [Guide to Agent Checks](http://docs.datadoghq.com/guides/agent_checks/).

# Contributors

```bash
git log --all | gawk '/Author/ {print}' | sort | uniq
```
