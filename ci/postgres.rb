require './ci/common'

def raw_pg_version
  ENV['FLAVOR_VERSION'] || '9.4.1'
end

def pg_version
  "REL#{raw_pg_version.tr('.', '_')}"
end

def pg_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/pg_#{pg_version}"
end

namespace :ci do
  namespace :postgres do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      # Downloads
      # https://github.com/postgres/postgres/archive/#{pg_version}.tar.gz
      unless Dir.exist? File.expand_path(pg_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/postgres-#{pg_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/#{pg_version}.tar.gz)
        sh %(mkdir -p $VOLATILE_DIR/postgres)
        sh %(tar zxf $VOLATILE_DIR/postgres-#{pg_version}.tar.gz\
             -C $VOLATILE_DIR/postgres --strip-components=1)
        sh %(mkdir -p #{pg_rootdir})
        sh %(cd $VOLATILE_DIR/postgres\
             && ./configure --prefix=#{pg_rootdir}\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(mkdir -p $VOLATILE_DIR/postgres_data)
      sh %(#{pg_rootdir}/bin/initdb -D $VOLATILE_DIR/postgres_data)
      # docker travis seems to have pg already running :X
      # use another port
      sh %(#{pg_rootdir}/bin/pg_ctl -D $VOLATILE_DIR/postgres_data\
           -l $VOLATILE_DIR/postgres.log\
           -o "-p 15432"\
           start)
      Wait.for 15_432
      # Wait a tiny bit more, for PG to accept connections
      sleep_for 2
      sh %(#{pg_rootdir}/bin/psql\
           -p 15432 -U $USER\
           postgres < $TRAVIS_BUILD_DIR/ci/resources/postgres/postgres.sql)
      sh %(#{pg_rootdir}/bin/psql\
           -p 15432 -U datadog\
           datadog_test < $TRAVIS_BUILD_DIR/ci/resources/postgres/datadog_test.sql)
      sh %(#{pg_rootdir}/bin/psql\
           -p 15432 -U datadog\
           dogs < $TRAVIS_BUILD_DIR/ci/resources/postgres/dogs.sql)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'postgres'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(#{pg_rootdir}/bin/pg_ctl\
           -D $VOLATILE_DIR/postgres_data\
           -l $VOLATILE_DIR/postgres.log\
           -o "-p 15432"\
           stop)
      sh %(rm -r $VOLATILE_DIR/postgres*)
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
