# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def activemq_version
  ENV['FLAVOR_VERSION'] || '5.11.1'
end

def activemq_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/activemq_#{activemq_version}"
end

def activemq_bin
  "#{activemq_rootdir}/bin/activemq"
end

namespace :ci do
  namespace :activemq do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless File.exist? activemq_bin
        # Download from Apache
        # http://archive.apache.org/dist/activemq/#{activemq_version}/apache-activemq-#{activemq_version}-bin.tar.gz
        sh %(curl -s -L\
             -o $VOLATILE_DIR/activemq-#{activemq_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/apache-activemq-#{activemq_version}-bin.tar.gz)
        sh %(mkdir -p #{activemq_rootdir})
        sh %(tar zxf $VOLATILE_DIR/activemq-#{activemq_version}.tar.gz\
             -C #{activemq_rootdir} --strip-components=1)
      end
    end

    task before_script: ['ci:common:before_script'] do
      # Pre-set configuration (binary file based persistence database)
      # with queues, subscribers and topics
      sh %(curl -s -L\
           -o $VOLATILE_DIR/kahadb.tar.gz\
           https://s3.amazonaws.com/dd-agent-tarball-mirror/apache-activemq-kahadb.tar.gz)
      sh %(tar zxf $VOLATILE_DIR/kahadb.tar.gz\
           -C #{activemq_rootdir}/data)
      sh %(#{activemq_bin} start)
      Wait.for 'http://localhost:8161'
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'activemq'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache'] do
      sh %(rm -rf #{activemq_rootdir}/data/*)
    end

    task cleanup: ['ci:common:cleanup'] do
      sh %(#{activemq_rootdir}/bin/activemq stop)
    end

    task :execute do
      Rake::Task['ci:common:execute'].invoke(flavor)
    end
  end
end
