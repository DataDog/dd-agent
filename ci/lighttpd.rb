# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def lighttpd_version
  ENV['FLAVOR_VERSION'] || '1.4.35'
end

def lighttpd_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/lighttpd_#{lighttpd_version}"
end

namespace :ci do
  namespace :lighttpd do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(lighttpd_rootdir)
        # Downloads
        # http://download.lighttpd.net/lighttpd/releases-#{lighttpd_version[0..2]}.x/lighttpd-#{lighttpd_version}.tar.gz
        sh %(curl -s -L\
             -o $VOLATILE_DIR/lighttpd-#{lighttpd_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/lighttpd-#{lighttpd_version}.tar.gz)
        sh %(mkdir -p #{lighttpd_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/lighttpd)
        sh %(tar zxf $VOLATILE_DIR/lighttpd-#{lighttpd_version}.tar.gz\
             -C $VOLATILE_DIR/lighttpd --strip-components=1)
        sh %(cd $VOLATILE_DIR/lighttpd\
             && ./configure --prefix=#{lighttpd_rootdir}\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/lighttpd/lighttpd.conf\
           #{lighttpd_rootdir}/lighttpd.conf)
      sh %(sed -i -e "s@%PATH%@$VOLATILE_DIR@" #{lighttpd_rootdir}/lighttpd.conf)
      sh %(#{lighttpd_rootdir}/sbin/lighttpd -f #{lighttpd_rootdir}/lighttpd.conf)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'lighttpd'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache'] do
      # Conf is regenerated at every run
      sh %(rm -f #{lighttpd_rootdir}/lighttpd.conf)
    end

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/lighttpd.pid`)
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
