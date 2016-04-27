# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

# TODO: make this available in the matrix
def memcache_version
  '1.4.22'
end

def memcache_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/memcache_#{memcache_version}"
end

namespace :ci do
  namespace :memcache do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(memcache_rootdir)
        # Downloads
        # http://memcached.org/files/memcached-#{memcache_version}.tar.gz
        sh %(curl -s -L\
             -o $VOLATILE_DIR/memcached-#{memcache_version}.tar.gz\
              https://s3.amazonaws.com/dd-agent-tarball-mirror/memcached-#{memcache_version}.tar.gz)
        sh %(mkdir -p #{memcache_rootdir})
        sh %(tar zxf $VOLATILE_DIR/memcached-#{memcache_version}.tar.gz\
             -C #{memcache_rootdir} --strip-components=1)
        sh %(cd #{memcache_rootdir} && ./configure && make -j $CONCURRENCY)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(#{memcache_rootdir}/memcached -d)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'memcache'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task cleanup: ['ci:common:cleanup']
    # FIXME: stop memcache

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

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
