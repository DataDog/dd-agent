require './ci/common'

def raw_pg_version
  ENV['PG_VERSION'] || '9.4.0'
end

def pg_version
  "REL#{raw_pg_version.gsub('.', '_')}"
end

def pg_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/pg_#{pg_version}"
end

namespace :ci do
  namespace :postgres do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(pg_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/postgres-#{pg_version}.tar.gz\
             https://github.com/postgres/postgres/archive/#{pg_version}.tar.gz)
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

    task :before_script => ['ci:common:before_script'] do
      sh %(mkdir -p $VOLATILE_DIR/postgres_data)
      sh %(#{pg_rootdir}/bin/initdb -D $VOLATILE_DIR/postgres_data)
      # docker travis seems to have pg already running :X
      # use another port
      sh %(#{pg_rootdir}/bin/pg_ctl -D $VOLATILE_DIR/postgres_data\
           -l $VOLATILE_DIR/postgres.log\
           -o "-p 15432"\
           start)
      sleep_for 5
      sh %(#{pg_rootdir}/bin/psql\
           -p 15432 -U $USER\
           -c "CREATE USER datadog WITH PASSWORD 'datadog'"\
           postgres)
      sh %(#{pg_rootdir}/bin/psql\
           -p 15432 -U $USER\
           -c "GRANT SELECT ON pg_stat_database TO datadog"\
           postgres)
      sh %(#{pg_rootdir}/bin/psql\
           -p 15432 -U $USER\
           -c "CREATE DATABASE datadog_test"\
           postgres)
      sh %(#{pg_rootdir}/bin/psql\
           -p 15432 -U $USER\
           -c "GRANT ALL PRIVILEGES ON DATABASE datadog_test TO datadog"\
           postgres)
      sh %(#{pg_rootdir}/bin/psql\
           -p 15432 -U datadog\
           -c "CREATE TABLE persons (personid INT, lastname VARCHAR(255), firstname VARCHAR(255), address VARCHAR(255), city VARCHAR(255))"\
           datadog_test)
      # For pg_stat_user_table to return stuff
      sleep_for 5
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'postgres'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup'] do
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
