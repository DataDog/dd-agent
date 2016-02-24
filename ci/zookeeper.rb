# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def zk_version
  ENV['FLAVOR_VERSION'] || '3.4.7'
end

def zk_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/zk_#{zk_version}"
end

namespace :ci do
  namespace :zookeeper do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(zk_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/zookeeper-#{zk_version}.tar.gz\
            http://archive.apache.org/dist/zookeeper/zookeeper-#{zk_version}/zookeeper-#{zk_version}.tar.gz)
        sh %(mkdir -p #{zk_rootdir})
        sh %(tar zxf $VOLATILE_DIR/zookeeper-#{zk_version}.tar.gz\
             -C #{zk_rootdir} --strip-components=1)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(mkdir -p $VOLATILE_DIR/zookeeper)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/zookeeper/zoo.cfg\
           #{zk_rootdir}/conf/)
      sh %(#{zk_rootdir}/bin/zkServer.sh start)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'zookeeper'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(#{zk_rootdir}/bin/zkServer.sh stop)
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
