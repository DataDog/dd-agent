require './ci/common'

def kong_version
  ENV['FLAVOR_VERSION'] || '0.6.0'
end

def kong_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/kong"
end

def cassandra_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/cassandra"
end

namespace :ci do
  namespace :kong do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(kong_rootdir)
        # Download Kong, Cassandra. curl, openjdk 1.8, wget, make, gcc must be already installed
        sh %(mkdir -p #{kong_rootdir})
        sh %(cp $TRAVIS_BUILD_DIR/ci/resources/kong/kong_install.sh #{kong_rootdir}/kong_install.sh)
        sh %(bash #{kong_rootdir}/kong_install.sh)
        sh %(mkdir -p #{cassandra_rootdir})
        sh %(tar zxf $VOLATILE_DIR/kong-#{kong_version}.tar.gz\
             -C #{kong_rootdir} --strip-components=1)
        sh %(tar zxf $VOLATILE_DIR/apache-cassandra-2.1.3-bin.tar.gz\
             -C #{cassandra_rootdir} --strip-components=1)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/kong/cassandra_2.1.yaml #{cassandra_rootdir}/conf/cassandra.yaml)
      sh %(#{cassandra_rootdir}/bin/cassandra -p $VOLATILE_DIR/cass.pid > /dev/null)
       # Create temp cassandra workdir
      sh %(mkdir -p $VOLATILE_DIR/cassandra)
      Wait.for 9042, 10
      sh %(kong start)
      Wait.for 8001, 10
      sleep_for 5
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'kong'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: :cleanup

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(ccm stop)
      sleep_for 3
      sh %(kill `cat /usr/local/kong/nginx.pid`)
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
      fail exception if exception
    end
  end
end
