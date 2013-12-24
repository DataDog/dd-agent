Looking to contribute code to the agent? Thank you! Here are a few guidelines to help you get your code merged in the mainline.

(Colophon: inspired by [gunicorn](https://github.com/benoitc/gunicorn))

## Contribution guidelines

### Pull requests are always welcome

We are always thrilled to receive pull requests, and do our best to
process them as fast as possible. Not sure if that typo is worth a pull
request? Do it! We will appreciate it.

If your pull request is not accepted on the first try, don't be
discouraged! If there's a problem with the implementation, hopefully you
received feedback on what to improve.

### Create issues...

Any significant improvement should be documented as [a github
issue](https://github.com/DataDog/dd-agent/issues) before anybody starts
working on it.

### ...but check for existing issues first!

Please take a moment to check that an issue doesn't already exist
documenting your bug report or improvement proposal. If it does, it
never hurts to add a quick "+1" or "I have this problem too". This will
help prioritize the most common problems and requests.

### Conventions

Fork the repo and make changes on your fork in a feature branch:

- If it's a bugfix branch, name it XXX-something where XXX is the number
  of the issue
- If it's a feature branch, create an enhancement issue to announce your
  intentions, and name it XXX-something where XXX is the number of the
issue.

Submit unit tests for your changes. Python has a great test framework built
in; use it! Take a look at existing tests for inspiration. Run the full
test suite on your branch before submitting a pull request.

Make sure you include relevant updates or additions to documentation
when creating or modifying features.

Write clean code. 

Pull requests descriptions should be as clear as possible and include a
reference to all the issues that they address.

Code review comments may be added to your pull request. Discuss, then
make the suggested modifications and push additional commits to your
feature branch. Be sure to post a comment after pushing. The new commits
will show up in the pull request automatically, but the reviewers will
not be notified unless you comment.

Before the pull request is merged, make sure that you squash your
commits into logical units of work using `git rebase -i` and `git push
-f`. After every commit the test suite should be passing. Include
documentation changes in the same commit so that a revert would remove
all traces of the feature or fix.

Commits that fix or close an issue should include a reference like
`Closes #XXX` or `Fixes #XXX`, which will automatically close the issue
when merged.

Add your name to the THANKS file, but make sure the list is sorted and
your name and email address match your git configuration. The THANKS
file is regenerated occasionally from the git commit history, so a
mismatch may result in your changes being overwritten.

## Decision process

### How are decisions made?

Short answer: with pull requests to the gunicorn repository.

All decisions affecting gunicorn, big and small, follow the same 3 steps:

* Step 1: Open a pull request. Anyone can do this.

* Step 2: Discuss the pull request. Anyone can do this.

* Step 3: Accept or refuse a pull request. At the moment the Datadog engineering team does this. We hope to open the gates to outside maintainers in the future.
