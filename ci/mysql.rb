require './ci/common'

def mysql_version
  ENV['FLAVOR_VERSION'] || '5.7.9'
end

def mysql_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/mysql_#{mysql_version}"
end

namespace :ci do
  namespace :mysql do |flavor|
    @ld_path = "#{mysql_rootdir}/ld_deps/"
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      # Downloads
      # https://github.com/postgres/postgres/archive/#{pg_version}.tar.gz
      unless Dir.exist? File.expand_path(mysql_rootdir)
        if `uname`.strip == 'Darwin'
          target = 'osx10.10'
        else
          target = 'linux-glibc2.5'
        end
        sh %(curl -s -L\
             -o $VOLATILE_DIR/mysql-#{mysql_version}.tar.gz \
             https://dev.mysql.com/get/Downloads/MySQL-5.7/mysql-#{mysql_version}-#{target}-x86_64.tar.gz)

        # https://s3.amazonaws.com/dd-agent-tarball-mirror/#{pg_version}.tar.gz)
        sh %(mkdir -p #{mysql_rootdir}/ld_deps)
        sh %(tar zxf $VOLATILE_DIR/mysql-#{mysql_version}.tar.gz\
               -C #{mysql_rootdir} --strip-components=1)
        if target.include? 'linux'
          libaio_url = `apt-cache show libaio1 | grep "Filename:" | cut -f 2 -d " "`
          sh %(curl -s -L\
               -o $VOLATILE_DIR/libaio.deb \
               http://archive.ubuntu.com/ubuntu/#{libaio_url})
          sh %(dpkg-deb -x $VOLATILE_DIR/libaio.deb #{mysql_rootdir}/ld_deps)
        end
      end
    end

    task before_script: ['ci:common:before_script'] do
      # does travis have any mysql instance already running? :X
      # use another port?
      if `uname`.strip != 'Darwin'
        @ld_path += "lib/x86_64-linux-gnu/"
      end
      sh %(mkdir -p #{mysql_rootdir}/data)
      sh %(mkdir -p #{mysql_rootdir}/data_replica)
      puts 'Initializing MySQL instances.'.yellow
      system({ 'LD_LIBRARY_PATH' => @ld_path },
             "#{mysql_rootdir}/bin/mysqld --no-defaults --initialize-insecure --basedir=#{mysql_rootdir} --datadir=#{mysql_rootdir}/data" \
             "--log-error=#{mysql_rootdir}/data/mysql.err --socket=#{mysql_rootdir}/data/mysql.sock --pid-file=#{mysql_rootdir}/data/mysqld_safe.pid" \
             "--performance-schema")
      system({ 'LD_LIBRARY_PATH' => @ld_path },
             "#{mysql_rootdir}/bin/mysqld --no-defaults --initialize-insecure --basedir=#{mysql_rootdir} --datadir=#{mysql_rootdir}/data_replica" \
             "--log-error=#{mysql_rootdir}/data_replica/mysql.err --socket=#{mysql_rootdir}/data_replica/mysql.sock --pid-file=#{mysql_rootdir}/data_replica/mysqld_safe.pid" \
             "--performance-schema")
      # let the init process complete
      sleep_for 2
      system({ 'LD_LIBRARY_PATH' => @ld_path },
             "#{mysql_rootdir}/bin/mysqld --no-defaults --basedir=#{mysql_rootdir} --datadir=#{mysql_rootdir}/data --plugin-dir=#{mysql_rootdir}/lib/plugin" \
             "--log-error=#{mysql_rootdir}/data/mysql.err --socket=#{mysql_rootdir}/data/mysql.sock --pid-file=#{mysql_rootdir}/data/mysqld_safe.pid --port=3308" \
             "--log-bin=mysql-bin --server-id=1 --performance-schema --daemonize >/dev/null 2>&1")
      system({ 'LD_LIBRARY_PATH' => @ld_path },
             "#{mysql_rootdir}/bin/mysqld --no-defaults --basedir=#{mysql_rootdir} --datadir=#{mysql_rootdir}/data_replica --plugin-dir=#{mysql_rootdir}/lib/plugin" \
             "--log-error=#{mysql_rootdir}/data_replica/mysql.err --socket=#{mysql_rootdir}/data_replica/mysql.sock --pid-file=#{mysql_rootdir}/data_replica/mysqld_safe.pid" \
             "--port=3310 --server-id=2 --performance-schema --daemonize >/dev/null 2>&1")
      Wait.for 33_08, 10
      Wait.for 33_10, 10
      # set-up replication
      sh %(#{mysql_rootdir}/bin/mysql -e "CREATE USER 'repl'@'%' IDENTIFIED BY 'slavedog';" -u root --socket=#{mysql_rootdir}/data/mysql.sock)
      sh %(#{mysql_rootdir}/bin/mysql -e "GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';" \
           -u root --socket=#{mysql_rootdir}/data/mysql.sock)
      sh %(#{mysql_rootdir}/bin/mysql -e "create user 'dog'@'localhost' identified by 'dog'" -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
      sh %(#{mysql_rootdir}/bin/mysql -e "GRANT PROCESS, REPLICATION CLIENT ON *.* TO 'dog'@'localhost' WITH MAX_USER_CONNECTIONS 5;" \
           -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
      sh %(#{mysql_rootdir}/bin/mysql -e "CHANGE MASTER TO MASTER_HOST='localhost', MASTER_PORT=3309, MASTER_USER='repl', MASTER_PASSWORD='slavedog', MASTER_LOG_FILE='', MASTER_LOG_POS=4;" \
           -uroot --socket=#{mysql_rootdir}/data_replica/mysql.sock)
      sh %(#{mysql_rootdir}/bin/mysql -e "START SLAVE;" -uroot --socket=#{mysql_rootdir}/data_replica/mysql.sock)
      # lets add some data to our master.
      sh %(#{mysql_rootdir}/bin/mysql -e "CREATE DATABASE testdb;" -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
      sh %(#{mysql_rootdir}/bin/mysql -e "CREATE TABLE testdb.users (name VARCHAR(20), age INT);" -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
      sh %(#{mysql_rootdir}/bin/mysql -e "GRANT SELECT ON testdb.users TO 'dog'@'localhost';" -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
      sh %(#{mysql_rootdir}/bin/mysql -e "INSERT INTO testdb.users (name,age) VALUES('Alice',25);" -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
      sh %(#{mysql_rootdir}/bin/mysql -e "INSERT INTO testdb.users (name,age) VALUES('Bob',20);" -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
      sh %(#{mysql_rootdir}/bin/mysql -e "GRANT SELECT ON performance_schema.* TO 'dog'@'localhost';" -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
      # generate some performance metrics....
      sh %(#{mysql_rootdir}/bin/mysql -e "USE testdb; SELECT * FROM users ORDER BY name;" -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
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
      sh %(mysql -e "DROP USER 'dog'@'localhost';" -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
      sh %(mysql -e "DROP DATABASE testdb;" -uroot --socket=#{mysql_rootdir}/data/mysql.sock)
      `pgrep -f "#{mysql_rootdir}/bin/mysqld" `.split("\n").each do |spid|
        begin
          p = spid.to_i
          puts "Stopping #{p}"
          Process.kill 'TERM', p
        rescue Errno::ESRCH
          next
        end
      end
      puts 'Waiting for MySQL instances to shutdown.'.yellow
      sleep_for 2
      sh %(rm -rf #{mysql_rootdir}/data)
      sh %(rm -rf #{mysql_rootdir}/data_replica)
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
