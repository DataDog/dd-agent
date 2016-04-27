# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def haproxy_version
  ENV['FLAVOR_VERSION'] || '1.5.11'
end

def haproxy_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/haproxy_#{haproxy_version}"
end

namespace :ci do
  namespace :haproxy do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(haproxy_rootdir)
        # Downloads
        # http://www.haproxy.org/download/#{haproxy_version[0..2]}/src/haproxy-#{haproxy_version}.tar.gz
        sh %(curl -s -L\
             -o $VOLATILE_DIR/haproxy-#{haproxy_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/haproxy-#{haproxy_version}.tar.gz)
        sh %(mkdir -p #{haproxy_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/haproxy)
        sh %(tar zxf $VOLATILE_DIR/haproxy-#{haproxy_version}.tar.gz\
             -C $VOLATILE_DIR/haproxy --strip-components=1)

        target = if `uname`.strip == 'Darwin'
                   'mac'
                 else
                   'linux2628'
                 end
        sh %(cd $VOLATILE_DIR/haproxy\
             && make -j $CONCURRENCY TARGET=#{target} USE_PCRE=1 USE_OPENSSL=1 USE_ZLIB=1)
        sh %(cp $VOLATILE_DIR/haproxy/haproxy #{haproxy_rootdir})
        # FIXME: use that we don't start haproxy in the tests
        sh %(mkdir -p #{ENV['INTEGRATIONS_DIR']}/bin)
        sh %(cp $VOLATILE_DIR/haproxy/haproxy #{ENV['INTEGRATIONS_DIR']}/bin/)
      end
    end

    task before_script: ['ci:common:before_script'] do
      %w(haproxy haproxy-open).each do |name|
        pid = spawn("#{haproxy_rootdir}/haproxy", '-d', '-f',
                    "#{ENV['TRAVIS_BUILD_DIR']}/ci/resources/haproxy/#{name}.cfg",
                    out: '/dev/null')
        Process.detach(pid)
        sh %(echo #{pid} > $VOLATILE_DIR/#{name}.pid)
      end
      # Waiting for haproxy to start
      Wait.for 3836
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'haproxy'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      %w(haproxy haproxy-open).each do |name|
        sh %(kill `cat $VOLATILE_DIR/#{name}.pid`)
      end
    end

    task :execute do
      exception = nil
      begin
        %w(before_install install before_script
           script before_cache cache).each do |t|
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
