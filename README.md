[![Build Status](https://travis-ci.org/DataDog/dd-agent.svg?branch=master)](https://travis-ci.org/DataDog/dd-agent)

# Important note

This repository contains the source code for the Datadog Agent until major version 5.
Although still supported, no major feature is planned for this release line and we
encourage users and contributors to refer to the new Agent codebase, introduced
with the release of version 6.0.0 and tracked in
[a different git repository](https://github.com/DataDog/datadog-agent).

## Changes

Please refer to the [Change log](https://github.com/DataDog/dd-agent/blob/master/CHANGELOG.md)
for more details about the changes introduced at each release.

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
