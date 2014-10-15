require 'colorize'
require 'time'

def apt_update
  sh "sudo apt-get update -qq"
end

def sleep_for(secs)
  puts "Sleeping for #{secs}s".blue
  sleep(secs)
end

def section(name)
  timestamp = Time.now.utc.iso8601
  puts ""
  puts "[#{timestamp}] >>>>>>>>>>>>>> #{name} STAGE".black.on_white
  puts ""
end

namespace :ci do
  namespace :common do
    task :before_install do |t|
      section('BEFORE_INSTALL')
      t.reenable
    end

    task :install do |t|
      section('INSTALL')
      marker_file = '/tmp/COMMON_INSTALL_DONE'
      unless File.exists?(marker_file)
        sh "pip install -r requirements.txt --use-mirrors 2>&1 >> /tmp/ci.log"
        sh "pip install -r test-requirements.txt --use-mirrors 2>&1 >> /tmp/ci.log"
        sh "pip install . --use-mirrors 2>&1 >> /tmp/ci.log"
        sh "touch #{marker_file}"
      else
        puts "Skipping common installs, already done by another task".yellow
      end
      t.reenable
    end

    task :before_script do |t|
      section('BEFORE_SCRIPT')
      marker_file = '/tmp/COMMON_BEFORE_SCRIPT_DONE'
      unless File.exists?(marker_file)
        sh "sudo mkdir -p /etc/dd-agent/"
        sh %Q{sudo install -d -o "$(id -u)" /var/log/datadog}
        sh "sudo cp $TRAVIS_BUILD_DIR/datadog.conf.example /etc/dd-agent/datadog.conf"
        sh "touch #{marker_file}"
      else
        puts "Skipping common env setup, already done by another task".yellow
      end
      t.reenable
    end

    task :script do |t|
      section('SCRIPT')
      t.reenable
    end

    task :run_tests, :flavor do |t, attr|
      flavor = attr[:flavor]
      filter = ENV['NOSE_FILTER'] || 'True'
      if flavor == 'default'
        nose = "(not requires) and #{filter}"
      else
        nose = "(requires in #{flavor}) and #{filter}"
      end
      # FIXME make the other filters than param configurable
      sh %Q{nosetests -v -A '#{nose}' tests}
      t.reenable
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
