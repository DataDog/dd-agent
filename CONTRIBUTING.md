# Contributing to Datadog Agent

:tada: First of all, thanks for contributing! :tada:

This document aims to provide some basic guidelines to contribute to this repository, but keep in mind that these are just guidelines, not rules; use your best judgment and feel free to propose changes to this document in a pull request.

Want help with your PRs on this project? We offer [office hours](https://github.com/DataDog/dd-agent/wiki/Community-Office-Hours) twice a month via Slack and Google Hangouts.

## Submitting issues

- You can first take a look at the [Troubleshooting](https://datadog.zendesk.com/hc/en-us/sections/200766955-Troubleshooting) section of our [Knowledge base](https://datadog.zendesk.com/hc/en-us).
- If you can't find anything useful, please contact our [support](http://docs.datadoghq.com/help/) and [send them your logs](https://github.com/DataDog/dd-agent/wiki/Send-logs-to-support).
- Finally, you can open a Github issue respecting this [convention](#commits-titles) (it helps us triage).


## Pull Requests

You wrote some code/added a new check and want to share it? Thanks a lot for your interest!

In order to ease/speed up our review, here are some items you can check/improve when submitting your PR:

- [ ] have a [proper commit history](#commits) (we advise you to rebase if needed).
- [ ] write [tests](tests/README.md) for the code you wrote.
- [ ] preferably make sure that all [tests pass locally](tests/README.md).
- [ ] summarize your PR with a [good title](#commits-titles) and a message describing your changes, cross-referencing any related bugs/PRs.

Your Pull Request **must** always pass the Travis/Appveyor tests before being merged, if you think the error is not due to your changes, you can have a talk with us on IRC (#datadog freenode) or send us an email to support _at_ datadoghq _dot_ com)

_If you are adding a dependency (python module, library, ...), please check the [corresponding section](#add-dependencies)._

## [Integrations](https://github.com/DataDog/integrations-core)

All checks have been moved to the [Integration SDK](https://github.com/DataDog/integrations-core). Please look there to submit related issues, PRs, or review the latest changes.

For new integrations, please open a pull request in the [integrations extras repo](https://github.com/DataDog/integrations-extras)

## Commits

### Keep it small, focused

Avoid changing too many things at once, for instance if you're fixing the redis integration and at the same time shipping a dogstatsd improvement, it makes reviewing harder (devs specialize in different parts of the code) and the change _time-to-release_ longer.

### Bisectability

Every commit should lead to a valid code, at least a code in a better state than before. That means that every revision should be able to pass unit and integration tests ([more about testing](#tests))

An **example** of something which breaks bisectability:
* commit 1: _Added check X_
* commit 2: _forgot column_
* commit 3: _fix typo_

To avoid that, please rebase your changes and create valid commits. It keeps history cleaner, it's easier to revert things, and it makes developers happier too.


### Messages

Please don't use `git commit -m "Fixed stuff"`, it usually means that you just wrote the very first thing that came to your mind without much thought. Also it makes navigating through the code history harder.

Instead, the commit shortlog should focus on describing the change in a sane way (see [commits titles](#commits-titles)) and be **short** (72 columns is best).

The commit message should describe the reason for the change and give extra details that will allow someone later on to understand in 5 seconds the thing you've been working on for a day.

If your commit is only shipping documentation changes or example files, and is a complete no-op for the test suite, please add **[skip ci]** in the commit message body to skip the build and let you build slot to someone else _in need :wink:_

Examples, see:
  * https://github.com/DataDog/dd-agent/commit/44bc927aaaf2925ef081768b5888bbb20a5bb3bd
  * https://github.com/DataDog/dd-agent/commit/677417fe12b1914e4322ac2c1fd1645cb0f1de31
  * and for more general guidance, [this should help](http://chris.beams.io/posts/git-commit/)

### Commits titles

Every commit title, PR or issue should be named like the following example:
```
[category] short description of the matter
```

`category` can be:
* _core_: for the agent internals, or the common interfaces
* _dogstatsd_: for the embedded dogstatsd server
* _tests_: related to CI, integration & unit testing
* _dev_: related to development or tooling
* _check_name_: specific to one check

For descriptions, keep it short keep it meaningful. Here are a few examples to illustrate.

#### Bad descriptions

* [mysql] mysql check does not work
* [snmp] improved snmp
* [core] refactored stuff

#### Good descriptions

* [mysql] exception ValueError on mysql 5.4
* [snmp] added timeouts to snmpGet calls
* [core] add config option to common metric interface

## Tests

Please refer to this [document](tests/README.md).

## Add dependencies

You wrote a new agent check which uses a python module not embedded in the agent yet? You're at the right place to correct this!

We use [Omnibus](https://github.com/chef/omnibus) to build our agent and bundle all dependencies.
We define what are the agent dependencies in the [dd-agent-omnibus](https://github.com/DataDog/dd-agent-omnibus) repository, and we define how to build/add these dependencies in the [omnibus-software](https://github.com/DataDog/omnibus-software) repository.

To add a new module, you will have to update both.


### Python module without external dependencies

If you want to add a module which is pure python, installed with `pip`, without any compilation/external dependencies, it's really easy.

#### omnibus-software

First, fork `omnibus-software`, create your branch, and add a `my_module.rb` file in `config/software/`.

Then copy/paste these instructions:
```ruby
name "my_module"
default_version "9.9.9"

dependency "python"
dependency "pip"

build do
  license "https://url.to.my/LICENSE.txt"
  command "#{install_dir}/embedded/bin/pip install -I --install-option=\"--install-scripts=#{install_dir}/bin\" #{name}==#{version}"
end
```

And replace, `my_module` with your module name, `default_version` by the version you want, then provide a URL to the module license (replacing `"https://url.to.my/LICENSE.txt"`).

And it's done for `omnibus-software`!

#### dd-agent-omnibus

First, fork `omnibus-software`, and create your branch.

Then add `dependency "my_module"` to `config/projects/datadog-agent.rb`: (please respect alphabetical sort)
```ruby
# Check dependencies
dependency "kafka-python"
dependency "kazoo"
dependency "my_module"
dependency "paramiko"
dependency "pg8000"
```

And it's over! Don't forget to submit your two PRs (and to cross-reference them).

### Python module with external dependency

Your python module also needs an external lib? That's not a problem with Omnibus, it just needs a little more work.

#### omnibus-software

First, fork `omnibus-software` and create your branch.

Let's keep it simple, and suppose that you want to add a python module `my_module` which depends on a library `my_lib`.

Create a `my_lib.rb` file in `config/software/`.

Then add instructions to compile it from source and install it at the right place (this is for instance `libsqlite3.rb`):
```ruby
name "my_lib"
default_version "9.9.9"

source :git => 'git://github.com/my_lib/my_lib.git'

relative_path 'my_lib'

env = {
  "LDFLAGS" => "-L#{install_dir}/embedded/lib -I#{install_dir}/embedded/include",
  "CFLAGS" => "-L#{install_dir}/embedded/lib -I#{install_dir}/embedded/include",
  "LD_RUN_PATH" => "#{install_dir}/embedded/lib"
}

build do
  command(["./configure",
       "--prefix=#{install_dir}/embedded",
       "--disable-nls"].join(" "),
    :env => env)
  command "make -j #{workers}", :env => {"LD_RUN_PATH" => "#{install_dir}/embedded/lib"}
  command "sudo make install"
end
```

_You will probably have to adapt the build instructions, depending on your lib._

Then create the `my_module.rb` file and copy/paste these instructions:
```ruby
name "my_module"
default_version "9.9.9"

dependency "my_lib"
dependency "python"
dependency "pip"

build do
  license "https://url.to.my/LICENSE.txt"
  command "#{install_dir}/embedded/bin/pip install -I --install-option=\"--install-scripts=#{install_dir}/bin\" #{name}==#{version}"
end
```

And replace, `my_module` with your module name, `default_version` with the version you want, `my_lib` with the name of the required lib, then provide a URL to the module license (replacing `"https://url.to.my/LICENSE.txt"`).

If you need to install it with `python setup.py install`, take a look at this [example](https://github.com/DataDog/omnibus-software/blob/macos-clean/config/software/guidata.rb). (which also demonstrate the use of a patch).

And it's done for `omnibus-software`!

#### dd-agent-omnibus

First, fork `omnibus-software`, and create your branch.

Then add `dependency "my_module"` to `config/projects/datadog-agent.rb`: (please respect alphabetical sort)
```ruby
# Check dependencies
dependency "kafka-python"
dependency "kazoo"
dependency "my_module"
dependency "paramiko"
dependency "pg8000"
```

And it's over! Don't forget to submit your two PRs (and to cross-reference them).
