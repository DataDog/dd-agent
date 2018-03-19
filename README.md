[![Build Status](https://travis-ci.org/DataDog/dd-agent.svg?branch=master)](https://travis-ci.org/DataDog/dd-agent)

# Important note

This repository contains the source code for the Datadog Agent up to and including
major version 5.
Although still supported, no major feature is planned for this release line and we
encourage users and contributors to refer to the new Agent codebase, introduced
with the release of version 6.0.0 and tracked in
[a different git repository](https://github.com/DataDog/datadog-agent).

## Changes

Please refer to the [Change log](https://github.com/DataDog/dd-agent/blob/master/CHANGELOG.md)
for more details about the changes introduced at each release.

## How to contribute code

Before submitting any code, please read our [contributing guidelines](CONTRIBUTING.md).
We'll keep accepting contributions as long as the major version 5 is supported
but please consider submitting new features to the new Agent codebase.

Please note that the Agent is licensed for simplicity's sake
under a simplified BSD license, as indicated in the `LICENSE` file.
Exceptions are marked with LICENSE-xxx where xxx is the component name.
If you do **not** agree with the licensing terms and wish to contribute code nonetheless,
please email us at <info@datadoghq.com> before submitting your
pull request.

### Setup your environment

Required:

* python 2.7
* bundler (to get it: `gem install bundler`)

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

## Integrations

All checks have been moved to the [Integrations Core](https://github.com/DataDog/integrations-core) repo.
Please look there to submit related issues, PRs, or review the latest changes.

## Tests

More about how to write tests and run them [here](tests/README.md)

## How to configure the Agent

If you are using packages on linux, the main configuration file lives
in `/etc/dd-agent/datadog.conf`. Per-check configuration files are in
`/etc/dd-agent/conf.d`. We provide an example in the same directory
that you can use as a template.

## How to write your own checks

Writing your own checks is easy using our checks.d interface. Read more about
how to use it on our [Guide to Agent Checks](http://docs.datadoghq.com/guides/agent_checks/).

## Contributors

```bash
git log --all | grep 'Author' | sort -u
```
