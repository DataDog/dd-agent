# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def gearman_version
  '1.0.6'
end

def gearman_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/gearman_#{gearman_version}"
end

namespace :ci do
  namespace :gearman do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(gearman_rootdir)
        # Downloads
        # https://launchpad.net/gearmand/#{gearman_version[0..2]}/#{gearman_version}/+download/gearmand-#{gearman_version}.tar.gz
        sh %(curl -s -L\
             -o $VOLATILE_DIR/gearman-#{gearman_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/gearmand-#{gearman_version}.tar.gz)
        sh %(mkdir -p $VOLATILE_DIR/gearman)
        sh %(tar zxf $VOLATILE_DIR/gearman-#{gearman_version}.tar.gz\
             -C $VOLATILE_DIR/gearman --strip-components=1)
        sh %(mkdir -p #{gearman_rootdir})
        sh %(cd $VOLATILE_DIR/gearman\
             && ./configure --prefix=#{gearman_rootdir}\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(#{gearman_rootdir}/sbin/gearmand -d -l $VOLATILE_DIR/gearmand.log)
      # FIXME: wait for gearman start
      # Wait.for ??
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'gearman'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup']
    # FIXME: stop gearman

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
