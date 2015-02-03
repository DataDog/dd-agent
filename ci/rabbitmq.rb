require './ci/common'

# TODO: make this available in the matrix
def rabbitmq_version
  '3.4.3'
end

def rabbitmq_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/rabbitmq_#{rabbitmq_version}"
end

namespace :ci do
  namespace :rabbitmq do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(rabbitmq_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/rabbitmq-server-generic-unix-3.4.3.tar.gz\
             http://www.rabbitmq.com/releases/rabbitmq-server/v3.4.3/rabbitmq-server-generic-unix-3.4.3.tar.gz)
        sh %(mkdir -p #{rabbitmq_rootdir})
        sh %(tar zxf $VOLATILE_DIR/rabbitmq-server-generic-unix-3.4.3.tar.gz\
             -C #{rabbitmq_rootdir} --strip-components=1)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      sh %(#{rabbitmq_rootdir}/sbin/rabbitmq-server -detached)
      sleep_for 5
      sh %(#{rabbitmq_rootdir}/sbin/rabbitmq-plugins enable rabbitmq_management)
      sh %(#{rabbitmq_rootdir}/sbin/rabbitmq-plugins enable rabbitmq_management)
      sh %(python `find #{rabbitmq_rootdir} -name rabbitmqadmin` declare queue name=test1)
      sh %(python `find #{rabbitmq_rootdir} -name rabbitmqadmin` declare queue name=test5)
      sh %(python `find #{rabbitmq_rootdir} -name rabbitmqadmin` declare queue name=tralala)
      sh %(python `find #{rabbitmq_rootdir} -name rabbitmqadmin` list queues)
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'rabbitmq'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup'] do
      sh %(#{rabbitmq_rootdir}/sbin/rabbitmqctl stop)
    end

    task :execute do
      exception = nil
      begin
        %w(before_install install before_script script).each do |t|
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
      fail exception if exception
    end
  end
end
