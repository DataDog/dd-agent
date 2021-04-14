# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
require './ci/common'

def solr_version
  ENV['FLAVOR_VERSION'] || '6.2'
end

def solr_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/solr_#{solr_version}"
end

rmi_port = 18_983
container_port = 8983

container_name = 'dd-test-solr'

jmx_opts = %(-Dcom.sun.management.jmxremote \
             -Dcom.sun.management.jmxremote.local.only=false \
             -Dcom.sun.management.jmxremote.ssl=false \
             -Dcom.sun.management.jmxremote.authenticate=false \
             -Dcom.sun.management.jmxremote.port=18983 \
             -Dcom.sun.management.jmxremote.rmi.port=18983 \
             -Djava.rmi.server.hostname=localhost)

namespace :ci do
  namespace :solr do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('solr')
      docker_image = "solr:#{solr_version}"
      sh %(docker run -d -e ENABLE_REMOTE_JMX_OPTS=true -e RMI_PORT=18983 \
           -p #{rmi_port}:#{rmi_port} -p #{container_port}:#{container_port} \
           --name #{container_name} #{docker_image} #{jmx_opts})
      wait_on_docker_logs(container_name, 40, 'Server Started')
      sleep 10
      sh %(docker exec -it --user=solr #{container_name} bin/solr create_core -c gettingstarted)
      sleep 10
    end

    task before_script: ['ci:common:before_script'] do
      # sh %(docker kill #{container_name} 2>/dev/null || true)
      # sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'solr'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup']
    # sample cleanup task
    # task cleanup: ['ci:common:cleanup'] do
    #   sh %(docker stop solr)
    #   sh %(docker rm solr)
    # end

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
