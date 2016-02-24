# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def etcd_version
  ENV['FLAVOR_VERSION'] || '2.0.5'
end

def etcd_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/etcd_#{etcd_version}"
end

namespace :ci do
  namespace :etcd do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(etcd_rootdir)
        # Downloads:
        # https://github.com/coreos/etcd/releases/download/v#{etcd_version}/etcd-v#{etcd_version}-darwin-amd64.zip
        # https://github.com/coreos/etcd/releases/download/v#{etcd_version}/etcd-v#{etcd_version}-linux-amd64.tar.gz
        if `uname -s`.strip.casecmp('darwin').zero?
          sh %(curl -s -L -o $VOLATILE_DIR/etcd.zip\
                https://s3.amazonaws.com/dd-agent-tarball-mirror/etcd-v#{etcd_version}-darwin-amd64.zip)
          sh %(mkdir -p #{etcd_rootdir})
          sh %(unzip -d $VOLATILE_DIR/ -x $VOLATILE_DIR/etcd.zip)
          sh %(mv -f $VOLATILE_DIR/etcd-*/* #{etcd_rootdir})
        else
          sh %(curl -s -L -o $VOLATILE_DIR/etcd.tar.gz\
                https://s3.amazonaws.com/dd-agent-tarball-mirror/etcd-v#{etcd_version}-linux-amd64.tar.gz)
          sh %(mkdir -p #{etcd_rootdir})
          sh %(tar xzvf $VOLATILE_DIR/etcd.tar.gz\
                        -C #{etcd_rootdir}\
                        --strip-components=1 >/dev/null)
        end
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(cd $VOLATILE_DIR && #{etcd_rootdir}/etcd >/dev/null &)
      # Waiting for etcd to start
      Wait.for 'http://localhost:4001/v2/stats/self'
      Wait.for 'http://localhost:4001/v2/stats/store'
      10.times do
        sh %(curl -s http://127.0.0.1:2379/v2/keys/message\
             -XPUT -d value="Hello world" >/dev/null)
        sh %(curl -s http://127.0.0.1:2379/v2/keys/message > /dev/null)
      end
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'etcd'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      # This will delete the temp directory of etcd,
      # so the etcd process will kill himself quickly after that (<10s)
      sh %(rm -rf $VOLATILE_DIR/*etcd*)
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
