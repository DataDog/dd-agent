# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def tokumx_version
  ENV['FLAVOR_VERSION'] || '2.0.1'
end

def tokumx_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/tokumx_#{tokumx_version}"
end

namespace :ci do
  namespace :tokumx do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(tokumx_rootdir)
        # Downloads
        # http://www.tokutek.com/tokumx-for-mongodb/download-community/
        sh %(curl -s -L\
             -o $VOLATILE_DIR/tokumx-#{tokumx_version}.tgz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/tokumx-#{tokumx_version}-linux-x86_64-main.tar.gz)
        sh %(mkdir -p #{tokumx_rootdir})
        sh %(tar zxf $VOLATILE_DIR/tokumx-#{tokumx_version}.tgz\
             -C #{tokumx_rootdir} --strip-components=1)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(mkdir -p $VOLATILE_DIR/tokumxd1)
      sh %(#{tokumx_rootdir}/bin/mongod --port 37017\
           --pidfilepath $VOLATILE_DIR/tokumxd1/tokumx.pid\
           --dbpath $VOLATILE_DIR/tokumxd1\
           --logpath $VOLATILE_DIR/tokumxd1/tokumx.log\
           --noprealloc --rest --fork)

      sh %(#{tokumx_rootdir}/bin/mongo\
           --eval "printjson(db.serverStatus())" 'localhost:37017')
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'tokumx'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/tokumxd1/tokumx.pid`)
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
