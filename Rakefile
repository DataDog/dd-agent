#!/usr/bin/env rake
# encoding: utf-8
# 3p
require 'rake/clean'
require 'rubocop/rake_task'

# Flavored Travis CI jobs
require './ci/apache'
require './ci/activemq'
require './ci/cassandra'
require './ci/checks_mock'
require './ci/core_integration'
require './ci/couchdb'
require './ci/default'
require './ci/elasticsearch'
require './ci/etcd'
require './ci/fluentd'
require './ci/gearman'
require './ci/go_expvar'
require './ci/haproxy'
require './ci/kong'
require './ci/lighttpd'
require './ci/memcache'
require './ci/mongo'
require './ci/mysql'
require './ci/nginx'
require './ci/pgbouncer'
require './ci/phpfpm'
require './ci/postgres'
require './ci/powerdns_recursor'
require './ci/rabbitmq'
require './ci/redis'
require './ci/riak'
require './ci/snmp'
require './ci/ssh'
require './ci/supervisord'
require './ci/system'
require './ci/tokumx'
require './ci/tomcat'
require './ci/varnish'
require './ci/windows'
require './ci/zookeeper'
require './ci/docker_daemon'

CLOBBER.include '**/*.pyc'

# CI-like environment for local use
unless ENV['CI']
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
  `python venv/virtualenv.py -p python2 --no-site-packages --no-pip --no-setuptools venv/`
  `wget -O venv/ez_setup.py https://bootstrap.pypa.io/ez_setup.py`
  `venv/bin/python venv/ez_setup.py --version="20.9.0"`
  `wget -O venv/get-pip.py https://bootstrap.pypa.io/get-pip.py`
  `venv/bin/python venv/get-pip.py`
  `venv/bin/pip install -r requirements.txt`
  `venv/bin/pip install -r requirements-test.txt`
  # These deps are not really needed, so we ignore failures
  ENV['PIP_COMMAND'] = 'venv/bin/pip'
  `./utils/pip-allow-failures.sh requirements-opt.txt`
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

RuboCop::RakeTask.new(:rubocop) do |t|
  t.patterns = ['ci/**/*.rb', 'Gemfile', 'Rakefile']
end

desc 'Lint the code through pylint'
task 'lint' => ['ci:default:lint'] do
end

desc 'Run the Agent locally'
task 'run' do
  sh('supervisord -n -c supervisord.dev.conf')
end

namespace :ci do
  desc 'Run integration tests'
  task :run, :flavor do |_, args|
    puts 'Assuming you are running these tests locally' unless ENV['TRAVIS']
    flavor = args[:flavor] || ENV['TRAVIS_FLAVOR'] || 'default'
    flavors = flavor.split(',')
    flavors.each { |f| Rake::Task["ci:#{f}:execute"].invoke }
  end
end

task default: ['lint', 'ci:run']
