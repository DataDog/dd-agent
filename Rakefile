#!/usr/bin/env rake
# encoding: utf-8

require 'rake/clean'

CLOBBER.include '**/*.pyc'

desc "Run tests"
task :test, [:attrs] do |t, args|
  attrs = args.attrs ? "-a #{args.attrs}" : ""
  cmd = "nosetests #{attrs}"
  sh cmd
end

namespace :test do
  desc 'Run dogstatsd tests'
  task 'dogstatsd' do
    sh 'nosetests tests/test_dogstatsd.py'
  end

  desc 'Run performance tests'
  task 'performance' do
    sh 'nosetests --with-xunit --xunit-file=nosetests-performance.xml tests/performance/benchmark*.py'
  end

  desc 'cProfile unit tests (requires \'nose-cprof\')'
  task 'profile' do
    sh 'nosetests --with-cprofile tests/performance/benchmark*.py'
  end

  desc 'cProfile tests, then run pstats'
  task 'profile:pstats' => ['test:profile'] do
    sh 'python -m pstats stats.dat'
  end
end

desc "Lint the code through pylint"
task "lint" do
  sh("find . -name \\*.py -type f -not -path \\*tests\\* -exec pylint --rcfile=.pylintrc --reports=n --output-format=parseable {} \\;")
end

desc "Run the Agent locally"
task "run" do
  sh("supervisord -n -c supervisord.dev.conf")
end

desc "Update pup release tag to the current commit"
task "pup:tag" do
  # This is an abomination. We distributed our install pup script via bitly
  # (which can't change) which is hardcoded to a github url (add-pup). Matt
  # Perpick made this worse by trying to change it and adding another one
  # (pup-release). We can't do anything about this now, because both links are
  # in the wild.
  tag = "pup-release"
  sh("git tag -f #{tag}")
  sh("git push origin --tags")
  sh("git co add-pup && git merge pup-release")
  sh("git push origin add-pup")
end

task :default => [:test]
