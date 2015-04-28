require 'colorize'
require 'time'

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

# Initialize cache if in travis and in our repository
# (no cache for external contributors)
if ENV['TRAVIS'] && ENV['AWS_SECRET_ACCESS_KEY']
  cache = Cache.new({
    debug: ENV['DEBUG_CACHE'],
    s3: {
      bucket: 'dd-agent-travis-cache',
      access_key_id: ENV['AWS_ACCESS_KEY_ID'],
      secret_access_key: ENV['AWS_SECRET_ACCESS_KEY']
    }
  })
end

namespace :ci do
  namespace :common do
    task :before_install do |t|
      section('BEFORE_INSTALL')
      sh %(mkdir -p $VOLATILE_DIR)
      if ENV['TRAVIS'] && ENV['AWS_SECRET_ACCESS_KEY']
        cache.directories = ["#{ENV['HOME']}/embedded"]
        cache.setup
      end
      t.reenable
    end

    task :install do |t|
      section('INSTALL')
      sh %(pip install --upgrade pip setuptools)
      sh %(pip install\
           -r requirements.txt\
           --cache-dir $PIP_CACHE\
           2>&1 >> $VOLATILE_DIR/ci.log)
      sh %(pip install\
           -r test-requirements.txt\
           --cache-dir $PIP_CACHE\
            2>&1 >> $VOLATILE_DIR/ci.log)
      t.reenable
    end

    task :before_script do |t|
      section('BEFORE_SCRIPT')
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/datadog.conf.example\
           $TRAVIS_BUILD_DIR/datadog.conf)
      t.reenable
    end

    task :script do |t|
      section('SCRIPT')
      t.reenable
    end

    task :before_cache do |t|
      section('BEFORE_CACHE')
      sh %(find $INTEGRATIONS_DIR/ -type f -name '*.log*' -delete)
      t.reenable
    end

    task :cache do |t|
      section('CACHE')
      cache.push
    end

    task :cleanup do |t|
      section('CLEANUP')
      t.reenable
    end

    task :run_tests, :flavor do |t, attr|
      flavor = attr[:flavor]
      filter = ENV['NOSE_FILTER'] || '1'
      if flavor == 'default'
        nose = "(not requires) and #{filter}"
      else
        nose = "(requires in #{flavor}) and #{filter}"
      end
      # FIXME: make the other filters than param configurable
      # For integrations that cannot be easily installed in a
      # separate dir we symlink stuff in the rootdir
      sh %(PATH=$INTEGRATIONS_DIR/bin:$PATH nosetests -v -A '#{nose}' tests)
      t.reenable
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
