#!/usr/bin/env rake
# encoding: utf-8

require 'rake/clean'

# Flavored Travis CI jobs
require './ci/apache'
require './ci/cassandra'
require './ci/couchdb'
require './ci/default'
require './ci/elasticsearch'
require './ci/etcd'
require './ci/fluentd'
require './ci/gearman'
require './ci/haproxy'
require './ci/lighttpd'
require './ci/memcache'
require './ci/mongo'
require './ci/mysql'
require './ci/nginx'
require './ci/postgres'
require './ci/rabbitmq'
require './ci/redis'
require './ci/snmpd'
require './ci/sysstat'
require './ci/ssh'
require './ci/tomcat'

CLOBBER.include '**/*.pyc'

# Travis-like environment for local use

unless ENV['IS_TRAVIS']
  rakefile_dir = File.dirname(__FILE__)
  ENV['TRAVIS_BUILD_DIR'] = rakefile_dir
  ENV['INTEGRATIONS_DIR'] = File.join(rakefile_dir, 'embedded')
  ENV['PIP_CACHE'] = File.join(rakefile_dir, '.pip-cache')
  ENV['VOLATILE_DIR'] = '/tmp/dd-agent-testing'
  ENV['CONCURRENCY'] = ENV['CONCURRENCY'] || '2'
  ENV['NOSE_FILTER'] = 'not windows'
end

desc 'Setup a development environment for the Agent'
task "setup_env" do
   `mkdir -p venv`
   `wget -O venv/virtualenv.py https://raw.github.com/pypa/virtualenv/1.11.6/virtualenv.py`
   `python venv/virtualenv.py  --no-site-packages --no-pip --no-setuptools venv/`
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
  sh %{find . -name '*.py' -type f -not -path '*venv*' -not -path '*embedded*' -exec pylint --rcfile=./.pylintrc {} \\;}
end

desc "Run the Agent locally"
task "run" do
  sh("supervisord -n -c supervisord.dev.conf")
end

namespace :ci do
  desc 'Run integration tests'
  task :run, :flavor  do |t, args|
    puts "Assuming you are running these tests locally" unless ENV['TRAVIS']
    flavor = args[:flavor] || ENV['TRAVIS_FLAVOR'] || 'default'
    flavors = flavor.split(',')
    flavors.each { |f| Rake::Task["ci:#{f}:execute"].invoke}
  end
end

task :default => [:test]
