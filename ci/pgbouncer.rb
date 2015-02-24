require './ci/common'
require './ci/postgres'

def pgb_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/pgbouncer"
end


namespace :ci do
  namespace :pgbouncer do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install do
      Rake::Task['ci:postgres:install'].invoke
      unless Dir.exist? File.expand_path(pgb_rootdir)
        sh %(wget -O $VOLATILE_DIR/pgbouncer-1.5.4.tar.gz https://s3.amazonaws.com/travis-archive/pgbouncer-1.5.4.tar.gz)
        sh %(mkdir -p $VOLATILE_DIR/pgbouncer)
        sh %(tar xzf $VOLATILE_DIR/pgbouncer-1.5.4.tar.gz\
             -C $VOLATILE_DIR/pgbouncer --strip-components=1)
        sh %(mkdir -p #{pgb_rootdir})
        sh %(cd $VOLATILE_DIR/pgbouncer\
             && ./configure --prefix=#{pgb_rootdir}\
             && make\
             && cp pgbouncer #{pgb_rootdir})
      end
    end

    task :before_script do
      Rake::Task['ci:postgres:before_script'].invoke
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/pgbouncer/pgbouncer.ini\
           #{pgb_rootdir}/pgbouncer.ini)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/pgbouncer/users.txt\
           #{pgb_rootdir}/users.txt)
      sh %(#{pgb_rootdir}/pgbouncer -d #{pgb_rootdir}/pgbouncer.ini)
      sleep_for 3
      sh %(PGPASSWORD=datadog #{pg_rootdir}/bin/psql\
           -h localhost -p 15433 -U datadog -w\
           -c "SELECT * FROM persons"\
           datadog_test)
      sleep_for 3
    end

    task :script do
      this_provides = [
        'pgbouncer'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup do
      sh %(rm -rf $VOLATILE_DIR/pgbouncer*)
      sh %(killall pgbouncer)
      Rake::Task['ci:postgres:cleanup'].invoke
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
