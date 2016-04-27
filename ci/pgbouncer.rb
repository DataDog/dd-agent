# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'
require './ci/postgres'

def pgb_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/pgbouncer"
end

namespace :ci do
  namespace :pgbouncer do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:postgres:install'].invoke
      unless Dir.exist? File.expand_path(pgb_rootdir)
        # upstream link: https://github.com/markokr/pgbouncer-dev/archive/pgbouncer_1_5_4.tar.gz
        sh %(mkdir -p #{pgb_rootdir})
        sh %(git clone https://github.com/markokr/pgbouncer-dev $VOLATILE_DIR/pgbouncer)
        sh %(cd $VOLATILE_DIR/pgbouncer\
             && git checkout pgbouncer_1_5_4\
             && git submodule init\
             && git submodule update\
             && ./autogen.sh\
             && ./configure --prefix=#{pgb_rootdir}\
             && make\
             && cp pgbouncer #{pgb_rootdir})
      end
    end

    task :before_script do
      Rake::Task['ci:postgres:before_script'].invoke
      sh %(sed 's#USERS_TXT##{pgb_rootdir}/users.txt#'\
           $TRAVIS_BUILD_DIR/ci/resources/pgbouncer/pgbouncer.ini\
           > #{pgb_rootdir}/pgbouncer.ini)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/pgbouncer/users.txt\
           #{pgb_rootdir}/users.txt)
      sh %(#{pgb_rootdir}/pgbouncer -d #{pgb_rootdir}/pgbouncer.ini)
      # Wait for pgbouncer to start
      Wait.for 15_433
      sh %(PGPASSWORD=datadog #{pg_rootdir}/bin/psql\
           -h localhost -p 15433 -U datadog -w\
           -c "SELECT * FROM persons"\
           datadog_test)
      sleep_for 5
    end

    task :script do
      this_provides = [
        'pgbouncer'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task :cleanup do
      sh %(killall pgbouncer)
      sh %(rm -rf $VOLATILE_DIR/pgbouncer*)
      Rake::Task['ci:postgres:cleanup'].invoke
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
