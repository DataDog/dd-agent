# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

# FIXME: test against different versions of tomcat
# and JDKs

def tomcat_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/tomcat-6.0.43"
end

namespace :ci do
  namespace :tomcat do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      # Downloads
      # http://mirror.sdunix.com/apache/tomcat/tomcat-6/v6.0.43/bin/apache-tomcat-6.0.43.tar.gz
      unless Dir.exist? File.expand_path(tomcat_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/apache-tomcat-6.0.43.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/apache-tomcat-6.0.43.tar.gz)
        sh %(mkdir -p #{tomcat_rootdir})
        sh %(tar zxf $VOLATILE_DIR/apache-tomcat-6.0.43.tar.gz\
             -C #{tomcat_rootdir} --strip-components=1)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/tomcat/setenv.sh #{tomcat_rootdir}/bin/)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/tomcat/server.xml #{tomcat_rootdir}/conf/server.xml)
      sh %(mkdir -p $VOLATILE_DIR/jmx_yaml)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/tomcat/tomcat.yaml $VOLATILE_DIR/jmx_yaml/)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/tomcat/jmx.yaml $VOLATILE_DIR/jmx_yaml/)
      sh %(#{tomcat_rootdir}/bin/startup.sh)
      Wait.for 'http://localhost:8080'
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'tomcat'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache'] do
      # Regenerated at every run
      sh %(rm -f #{tomcat_rootdir}/bin/setenv.sh)
      sh %(rm -f #{tomcat_rootdir}/conf/server.xml)
    end

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(#{tomcat_rootdir}/bin/shutdown.sh)
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
