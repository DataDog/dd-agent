# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def es_version
  ENV['FLAVOR_VERSION'] || '1.6.0'
end

def es_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/es_#{es_version}"
end

def es_bin
  "#{es_rootdir}/bin/elasticsearch"
end

namespace :ci do
  namespace :elasticsearch do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless File.exist? es_bin
        # cleanup dirty states
        sh %(rm -rf #{es_rootdir})
        # Downloads
        # https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-#{es_version}.tar.gz
        sh %(curl -s -L\
             -o $VOLATILE_DIR/elasticsearch-#{es_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/elasticsearch-#{es_version}.tar.gz)
        sh %(mkdir -p #{es_rootdir})
        sh %(tar zxf $VOLATILE_DIR/elasticsearch-#{es_version}.tar.gz\
             -C #{es_rootdir} --strip-components=1)
      end
    end

    task before_script: ['ci:common:before_script'] do
      # Elasticsearch configuration
      sh %(mkdir -p #{es_rootdir}/config)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/elasticsearch/elasticsearch.yml\
           #{es_rootdir}/config/)
      # Elasticsearch data
      sh %(mkdir -p $VOLATILE_DIR/es_data)
      pid = spawn %(#{es_rootdir}/bin/elasticsearch --path.data=$VOLATILE_DIR/es_data)
      Process.detach(pid)
      sh %(echo #{pid} > $VOLATILE_DIR/elasticsearch.pid)
      # Waiting for elaticsearch to start
      Wait.for 'http://localhost:9200', 20
      # Create an index in ES
      http = Net::HTTP.new('localhost', 9200)
      resp = http.send_request('PUT', '/datadog/')
      puts "Creating index returned #{resp.code}"
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'elasticsearch'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      # FIXME: remove `|| true` when we drop support for ES 0.90.x
      # (the only version spawning a process in background)
      sh %(kill `cat $VOLATILE_DIR/elasticsearch.pid` || true)
      sleep_for 1
    end

    task :execute do
      Rake::Task['ci:common:execute'].invoke(flavor)
    end
  end
end
