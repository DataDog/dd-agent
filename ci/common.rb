require 'colorize'
require 'httparty'
require 'socket'
require 'time'
require 'timeout'

# Colors don't work on Appveyor
String.disable_colorization = true if Gem.win_platform?

require './ci/resources/cache'

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

# Initialize cache if in travis and in our repository
# (no cache for external contributors)
if ENV['TRAVIS'] && ENV['AWS_SECRET_ACCESS_KEY']
  cache = Cache.new(debug: ENV['DEBUG_CACHE'],
                    s3: {
                      bucket: 'dd-agent-travis-cache',
                      access_key_id: ENV['AWS_ACCESS_KEY_ID'],
                      secret_access_key: ENV['AWS_SECRET_ACCESS_KEY']
                    })
end

namespace :ci do
  namespace :common do
    task :before_install do |t|
      section('BEFORE_INSTALL')
      # We use tempdir on Windows, no need to create it
      sh %(mkdir -p #{ENV['VOLATILE_DIR']}) unless Gem.win_platform?
      if ENV['TRAVIS'] && ENV['AWS_SECRET_ACCESS_KEY']
        cache.directories = ["#{ENV['HOME']}/embedded"]
        cache.setup
      end
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
      if ENV['TRAVIS'] && ENV['AWS_SECRET_ACCESS_KEY']
        section('BEFORE_CACHE')
        sh %(find #{ENV['INTEGRATIONS_DIR']}/ -type f -name '*.log*' -delete)
      end
      t.reenable
    end

    task :cache do |t|
      if ENV['TRAVIS'] && ENV['AWS_SECRET_ACCESS_KEY']
        section('CACHE')
        cache.push
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
    task execute: [:before_install, :install, :before_script, :script]
  end
end
