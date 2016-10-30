# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require 'colorize'
require 'httparty'
require 'socket'
require 'time'
require 'timeout'

# Colors don't work on Appveyor
String.disable_colorization = true if Gem.win_platform?

def sleep_for(secs)
  puts "Sleeping for #{secs}s".blue
  sleep(secs)
end

def section(name)
  timestamp = Time.now.utc.iso8601
  puts ''
  puts "[#{timestamp}] >>>>>>>>>>>>>> #{name} STAGE".black.on_white
  puts ''
end

def install_requirements(req_file, pip_options = nil, output = nil, use_venv = nil)
  pip_command = use_venv ? 'venv/bin/pip' : 'pip'
  redirect_output = output ? "2>&1 >> #{output}" : ''
  pip_options = '' if pip_options.nil?
  File.open(req_file, 'r') do |f|
    f.each_line do |line|
      line.strip!
      unless line.empty? || line.start_with?('#')
        sh %(#{pip_command} install #{line} #{pip_options} #{redirect_output}\
             || echo 'Unable to install #{line}' #{redirect_output})
      end
    end
  end
end

def travis_pr?
  !ENV['TRAVIS'].nil? && ENV['TRAVIS_EVENT_TYPE'] == 'pull_request'
end

BAD_CITIZENS = {
  'couch' => 'couchdb',
  'disk' => 'system',
  'network' => 'system',
  'tcp_check' => 'system',
  'http_check' => 'system',
  'sysstat' => 'system',
  'elastic' => 'elasticsearch',
  'gearmand' => 'gearman',
  'mongo' => 'mongodb',
  'mcache' => 'memcache',
  'php_fpm' => 'phpfpm',
  'redisdb' => 'redis',
  'ssh_check' => 'ssh',
  'zk' => 'zookeeper'
}.freeze

def translate_to_travis(checks)
  checks.map do |check_name|
    BAD_CITIZENS.key? check_name ? BAD_CITIZENS[check_name] : check_name
  end
end

# rubocop:disable Metrics/AbcSize
# [15.39/15]....
def can_skip?
  return false, [] unless travis_pr?

  modified_checks = []
  git_output = `git diff-tree --no-commit-id --name-only -r #{ENV['TRAVIS_COMMIT']} #{ENV['TRAVIS_BRANCH']}`
  git_output.each_line do |filename|
    filename.strip!
    if filename.start_with? 'checks.d'
      check_name = File.basename(filename, '.py')
    elsif filename.start_with?('tests/checks/integration', 'tests/checks/mock')
      check_name = File.basename(filename, '.py').slice 'test_'
    elsif filename.start_with?('tests/checks/fixtures', 'conf.d')
      next
    else
      return false, []
    end
    modified_checks << check_name unless modified_checks.include? check_name
  end
  [true, translate_to_travis(modified_checks)]
end
# rubocop:enable Metrics/AbcSize

# helper class to wait for TCP/HTTP services to boot
class Wait
  DEFAULT_TIMEOUT = 10

  def self.check_port(port)
    Timeout.timeout(0.5) do
      begin
        s = TCPSocket.new('localhost', port)
        s.close
        return true
      rescue Errno::ECONNREFUSED, Errno::EHOSTUNREACH
        return false
      end
    end
  rescue Timeout::Error
    return false
  end

  def self.check_url(url)
    Timeout.timeout(0.5) do
      begin
        r = HTTParty.get(url)
        return (200...300).cover? r.code
      rescue Errno::ECONNREFUSED, Errno::EHOSTUNREACH
        return false
      end
    end
  rescue Timeout::Error
    return false
  end

  def self.check_file(file_path)
    File.exist?(file_path)
  end

  def self.check(smth)
    if smth.is_a? Integer
      check_port smth
    elsif smth.include? 'http'
      check_url smth
    else
      check_file smth
    end
  end

  def self.for(smth, max_timeout = DEFAULT_TIMEOUT)
    start_time = Time.now
    status = false
    n = 1
    puts "Trying #{smth}"
    loop do
      puts n.to_s
      status = check(smth)
      break if status || Time.now > start_time + max_timeout
      n += 1
      sleep 0.25
    end
    raise "Still not up after #{max_timeout}s" unless status
    puts 'Found!'
    status
  end
end

namespace :ci do
  namespace :common do
    task :before_install do |t|
      section('BEFORE_INSTALL')
      # We use tempdir on Windows, no need to create it
      sh %(mkdir -p #{ENV['VOLATILE_DIR']}) unless Gem.win_platform?
      t.reenable
    end

    task :install do |t|
      section('INSTALL')
      sh %(#{'python -m ' if Gem.win_platform?}pip install --upgrade pip setuptools)
      sh %(pip install\
           -r requirements.txt\
           --cache-dir #{ENV['PIP_CACHE']}\
           2>&1 >> #{ENV['VOLATILE_DIR']}/ci.log)
      install_requirements('requirements-opt.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log")
      sh %(pip install\
           --upgrade\
           -r requirements-test.txt\
           --cache-dir #{ENV['PIP_CACHE']}\
            2>&1 >> #{ENV['VOLATILE_DIR']}/ci.log)
      t.reenable
    end

    task :before_script do |t|
      section('BEFORE_SCRIPT')
      sh %(cp #{ENV['TRAVIS_BUILD_DIR']}/ci/resources/datadog.conf.example\
           #{ENV['TRAVIS_BUILD_DIR']}/datadog.conf)
      t.reenable
    end

    task :script do |t|
      section('SCRIPT')
      t.reenable
    end

    task :before_cache do |t|
      section('BEFORE_CACHE')
      unless Gem.win_platform?
        sh %(find #{ENV['INTEGRATIONS_DIR']}/ -type f -name '*.log*' -delete)
      end
      t.reenable
    end

    task :cleanup do |t|
      section('CLEANUP')
      t.reenable
    end

    task :run_tests, :flavor do |t, attr|
      flavors = attr[:flavor]
      filter = ENV['NOSE_FILTER'] || '1'

      nose = if flavors.include?('default') || flavors.include?('checks_mock')
               "(not requires) and #{filter}"
             else
               "(requires in ['#{flavors.join("','")}']) and #{filter}"
             end

      tests_directory = if flavors.include?('default') || flavors.include?('core_integration')
                          'tests/core'
                        else
                          'tests/checks'
                        end
      # Rake on Windows doesn't support setting the var at the beginning of the
      # command
      path = ''
      unless Gem.win_platform?
        # FIXME: make the other filters than param configurable
        # For integrations that cannot be easily installed in a
        # separate dir we symlink stuff in the rootdir
        path = %(PATH="#{ENV['INTEGRATIONS_DIR']}/bin:#{ENV['PATH']}" )
      end
      sh %(#{path}nosetests -s -v -A "#{nose}" #{tests_directory})
      t.reenable
    end

    task :execute, :flavor do |_t, attr|
      flavor = attr[:flavor]
      # flavor.scope.path is ci:cassandra
      # flavor.scope.path[3..-1] is cassandra
      check_name = flavor.scope.path[3..-1]

      can_skip, checks = can_skip?
      can_skip &&= !%w(default core_integration checks_mock).include?(check_name)
      if can_skip && !checks.include?(check_name)
        puts "Skipping #{check_name} tests, not affected by the change".yellow
        next
      end
      exception = nil
      begin
        tasks = %w(before_install install before_script script)
        tasks << 'before_cache' unless ENV['CI'].nil?
        tasks.each do |t|
          Rake::Task["#{flavor.scope.path}:#{t}"].invoke
        end
      rescue => e
        exception = e
        puts "Failed task: #{e.class} #{e.message}".red
      end
      if ENV['SKIP_CLEANUP']
        puts 'Skipping cleanup, disposable environments are great'.yellow
      else
        puts 'Cleaning up'
        Rake::Task["#{flavor.scope.path}:cleanup"].invoke
      end
      raise exception if exception
    end
  end
end
