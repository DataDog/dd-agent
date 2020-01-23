# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
require './ci/common'

def cassandra_version
  ENV['FLAVOR_VERSION'] || '2.2.10' # '2.1.14' # '2.0.17'
end

def cassandra_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/cassandra_#{cassandra_version}"
end

def test_dir
  "#{ENV['TRAVIS_BUILD_DIR']}/tests/cassandra"
end

container_name = 'dd-test-cassandra'
container_port = 7199
cassandra_jmx_options = "-Dcom.sun.management.jmxremote.port=#{container_port}
  -Dcom.sun.management.jmxremote.rmi.port=#{container_port}
  -Dcom.sun.management.jmxremote.ssl=false
  -Dcom.sun.management.jmxremote.authenticate=true
  -Dcom.sun.management.jmxremote.password.file=/etc/cassandra/jmxremote.password
  -Djava.rmi.server.hostname=localhost"

namespace :ci do
  namespace :cassandra do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      sh %(rm -f #{test_dir}/jmxremote.password.tmp)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('cassandra')
      sh %(docker pull cassandra:#{cassandra_version})
      sh %(docker create --expose #{container_port} \
           -p #{container_port}:#{container_port} -e JMX_PORT=#{container_port} \
           -e LOCAL_JMX='no' -e JVM_EXTRA_OPTS="#{cassandra_jmx_options}" --name #{container_name} cassandra:#{cassandra_version})

      sh %(cp #{test_dir}/jmxremote.password #{test_dir}/jmxremote.password.tmp)
      sh %(chmod 400 #{test_dir}/jmxremote.password.tmp)
      sh %(docker cp #{test_dir}/jmxremote.password.tmp #{container_name}:/etc/cassandra/jmxremote.password)
      sh %(rm -f #{test_dir}/jmxremote.password.tmp)
      sh %(docker start #{container_name})
    end

    task before_script: ['ci:common:before_script'] do
      # Wait.for container_port
      count = 0
      logs = `docker logs #{container_name} 2>&1`
      puts 'Waiting for Cassandra to come up'
      until count == 20 || logs.include?('Listening for thrift clients') || logs.include?("Created default superuser role 'cassandra'")
        sleep_for 2
        logs = `docker logs #{container_name} 2>&1`
        count += 1
      end
      if logs.include?('Listening for thrift clients') || logs.include?("Created default superuser role 'cassandra'")
        puts 'Cassandra is up!'
      else
        sh %(docker logs #{container_name} 2>&1)
        raise
      end
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'cassandra'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
      sh %(rm -f #{test_dir}/jmxremote.password.tmp)
    end

    task :execute do
      exception = nil
      begin
        %w[before_install install before_script].each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        if !ENV['SKIP_TEST']
          Rake::Task["#{flavor.scope.path}:script"].invoke
        else
          puts 'Skipping tests'.yellow
        end
        Rake::Task["#{flavor.scope.path}:before_cache"].invoke
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
