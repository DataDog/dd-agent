# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

# TODO: make this available in the matrix
def rabbitmq_version
  '3.5.0'
end

def rabbitmq_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/rabbitmq_#{rabbitmq_version}"
end

namespace :ci do
  namespace :rabbitmq do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      # Downloads
      # http://www.rabbitmq.com/releases/rabbitmq-server/v#{mongo_version}/rabbitmq-server-generic-unix-#{mongo_version}.tar.gz
      unless Dir.exist? File.expand_path(rabbitmq_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/rabbitmq-server-generic-unix-#{rabbitmq_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/rabbitmq-server-generic-unix-#{rabbitmq_version}.tar.gz)
        sh %(mkdir -p #{rabbitmq_rootdir})
        sh %(tar zxf $VOLATILE_DIR/rabbitmq-server-generic-unix-#{rabbitmq_version}.tar.gz\
             -C #{rabbitmq_rootdir} --strip-components=1)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(#{rabbitmq_rootdir}/sbin/rabbitmq-server -detached)
      Wait.for 5672, 10
      sh %(#{rabbitmq_rootdir}/sbin/rabbitmq-plugins enable rabbitmq_management)
      sh %(#{rabbitmq_rootdir}/sbin/rabbitmq-plugins enable rabbitmq_management)
      %w(test1 test5 tralala).each do |q|
        sh %(python `find #{rabbitmq_rootdir} -name rabbitmqadmin` declare queue name=#{q})
        sh %(python `find #{rabbitmq_rootdir} -name rabbitmqadmin` publish exchange=amq.default routing_key=#{q} payload="hello, world")
      end
      sh %(python `find #{rabbitmq_rootdir} -name rabbitmqadmin` list queues)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'rabbitmq'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache'] do
      # Delete the RabbitMQ RABBITMQ_MNESIA_DIR which contains the data
      sh %(rm -rf #{rabbitmq_rootdir}/var/lib/rabbitmq/mnesia)
    end

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(#{rabbitmq_rootdir}/sbin/rabbitmqctl stop)
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
