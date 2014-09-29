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

desc 'Setup a development environment for the Agent'
task "setup_env" do
   `mkdir -p venv`
   `wget -O venv/virtualenv.py https://raw.github.com/pypa/virtualenv/1.11.X/virtualenv.py`
   `python venv/virtualenv.py  --no-pip --no-setuptools venv/`
   `wget -O venv/ez_setup.py https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py`
   `venv/bin/python venv/ez_setup.py`
   `wget -O venv/get-pip.py https://raw.github.com/pypa/pip/master/contrib/get-pip.py`
   `venv/bin/python venv/get-pip.py`
   `venv/bin/pip install -r source-requirements.txt`
   `venv/bin/pip install -r optional-requirements.txt`
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

task :default => [:test]
