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
require './ci/go_expvar'
require './ci/haproxy'
require './ci/lighttpd'
require './ci/memcache'
require './ci/mongo'
require './ci/mysql'
require './ci/nginx'
require './ci/pgbouncer'
require './ci/phpfpm'
require './ci/postgres'
require './ci/rabbitmq'
require './ci/redis'
require './ci/riak'
require './ci/snmpd'
require './ci/ssh'
require './ci/supervisord'
require './ci/sysstat'
require './ci/tokumx'
require './ci/tomcat'
require './ci/varnish'
require './ci/zookeeper'

CLOBBER.include '**/*.pyc'

# Travis-like environment for local use

unless ENV['TRAVIS']
  rakefile_dir = File.dirname(__FILE__)
  ENV['TRAVIS_BUILD_DIR'] = rakefile_dir
  ENV['INTEGRATIONS_DIR'] = File.join(rakefile_dir, 'embedded')
  ENV['PIP_CACHE'] = File.join(rakefile_dir, '.cache/pip')
  ENV['VOLATILE_DIR'] = '/tmp/dd-agent-testing'
  ENV['CONCURRENCY'] = ENV['CONCURRENCY'] || '2'
  ENV['NOSE_FILTER'] = 'not windows'
end

desc 'Setup a development environment for the Agent'
task 'setup_env' do
   `mkdir -p venv`
   `wget -O venv/virtualenv.py https://raw.github.com/pypa/virtualenv/1.11.6/virtualenv.py`
   `python venv/virtualenv.py  --no-site-packages --no-pip --no-setuptools venv/`
   `wget -O venv/ez_setup.py https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py`
   `venv/bin/python venv/ez_setup.py`
   `wget -O venv/get-pip.py https://raw.github.com/pypa/pip/master/contrib/get-pip.py`
   `venv/bin/python venv/get-pip.py`
   `venv/bin/pip install -r requirements.txt`
   `venv/bin/pip install -r requirements-opt.txt`
end

namespace :test do
  desc 'Run dogstatsd tests'
  task 'dogstatsd' do
    sh 'nosetests tests/core/test_dogstatsd.py'
  end

  desc 'Run performance tests'
  task 'performance' do
    sh 'nosetests --with-xunit --xunit-file=nosetests-performance.xml tests/core/benchmark*.py'
  end

  desc 'cProfile unit tests (requires \'nose-cprof\')'
  task 'profile' do
    sh 'nosetests --with-cprofile tests/core/benchmark*.py'
  end

  desc 'cProfile tests, then run pstats'
  task 'profile:pstats' => ['test:profile'] do
    sh 'python -m pstats stats.dat'
  end

  desc 'Display test coverage for checks'
  task 'coverage' => 'ci:default:coverage'
end

desc 'Lint the code through pylint'
task 'lint' => 'ci:default:lint'

desc 'Run the Agent locally'
task 'run' do
  sh('supervisord -n -c supervisord.dev.conf')
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
