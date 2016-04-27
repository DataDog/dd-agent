# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def varnish_version
  ENV['FLAVOR_VERSION'] || '4.0.3'
end

def varnish_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/varnish_#{varnish_version}"
end

namespace :ci do
  namespace :varnish do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(varnish_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/varnish-#{varnish_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/varnish-#{varnish_version}.tar.gz)
        sh %(mkdir -p #{varnish_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/varnish)
        sh %(tar zxf $VOLATILE_DIR/varnish-#{varnish_version}.tar.gz\
             -C $VOLATILE_DIR/varnish --strip-components=1)
        # Hack to not install the docs that require python-docs
        ENV['RST2MAN'] = 'echo'
        sh %(cd $VOLATILE_DIR/varnish\
             && ./configure --prefix=#{varnish_rootdir}\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(#{varnish_rootdir}/sbin/varnishd -b 127.0.0.1:4242 -a 127.0.0.1:4000 -P $VOLATILE_DIR/varnish.pid)
      # We need this for our varnishadm/varnishstat bins
      ENV['PATH'] = "#{varnish_rootdir}/bin:#{ENV['PATH']}"
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'varnish'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/varnish.pid`)
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
