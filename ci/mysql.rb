require './ci/common'

def mysql_version
  ENV['FLAVOR_VERSION'] || '5.7.10'
end

def mysql_parent_version
  "#{mysql_version}".split('.').slice(0, 2).join('.')
end

def mysql_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/mysql_#{mysql_version}"
end

namespace :ci do
  namespace :mysql do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(mysql_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/mysql-#{mysql_version}.tar.gz\
             http://cdn.mysql.com//Downloads/MySQL-#{mysql_parent_version}/mysql-#{mysql_version}.tar.gz)
        sh %(mkdir -p #{mysql_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/mysql)
        sh %(tar zxf $VOLATILE_DIR/mysql-#{mysql_version}.tar.gz\
             -C $VOLATILE_DIR/mysql --strip-components=1)
        sh %(cd $VOLATILE_DIR/mysql &&\
             cmake -DCMAKE_INSTALL_PREFIX=#{mysql_rootdir} -DMYSQL_DATADIR=#{mysql_rootdir}/data \
               -DMYSQL_UNIX_ADDR=#{mysql_rootdir}/mysql.sock -DDOWNLOAD_BOOST=1 &&\
             make -j $CONCURRENCY &&\
             make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      if Gem::Version.new("#{mysql_version}") >= Gem::Version.new('5.7.6')
        sh %(#{mysql_rootdir}/bin/mysqld --initialize-insecure --basedir=#{mysql_rootdir} --datadir=#{mysql_rootdir}/data)
      else
        case Gem::Version.new("#{mysql_version}")
        when Gem::Version.new('5.7.5')
          insecure_option = '--insecure'
          execute_file = "#{mysql_rootdir}/bin/mysql_install_db"
        when Gem::Version.new('5.7.4')
          insecure_option = '--skip-random-passwords'
          execute_file = "#{mysql_rootdir}/scripts/mysql_install_db"
        else
          insecure_option = ''
          execute_file = "#{mysql_rootdir}/scripts/mysql_install_db"
        end
        sh %(#{execute_file} #{insecure_option} --basedir=#{mysql_rootdir} --datadir=#{mysql_rootdir}/data)
      end
      sh %(#{mysql_rootdir}/bin/mysqld_safe --no-defaults --user=$USER --port=6033 --pid-file=#{mysql_rootdir}/mysql.pid &)
      Wait.for 6_033
      sleep_for 2
      sh %(#{mysql_rootdir}/bin/mysql -P 6033 -e "create user 'dog'@'localhost' identified by 'dog'" -uroot)
      sh %(#{mysql_rootdir}/bin/mysql -P 6033 -e "CREATE DATABASE testdb;" -uroot)
      sh %(#{mysql_rootdir}/bin/mysql -P 6033 -e "CREATE TABLE testdb.users (name VARCHAR(20), age INT);" -uroot)
      sh %(#{mysql_rootdir}/bin/mysql -P 6033 -e "GRANT SELECT ON testdb.users TO 'dog'@'localhost';" -uroot)
      sh %(#{mysql_rootdir}/bin/mysql -P 6033 -e "INSERT INTO testdb.users (name,age) VALUES('Alice',25);" -uroot)
      sh %(#{mysql_rootdir}/bin/mysql -P 6033 -e "INSERT INTO testdb.users (name,age) VALUES('Bob',20);" -uroot)
      sh %(#{mysql_rootdir}/bin/mysql -P 6033 -e "GRANT SUPER, REPLICATION CLIENT ON *.* TO 'dog'@'localhost';" -uroot)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'mysql'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat #{mysql_rootdir}/mysql.pid`)
      sleep_for 2
      sh %(rm -rf #{mysql_rootdir}/data)
      sh %(rm -rf $VOLATILE_DIR/mysql*)
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
