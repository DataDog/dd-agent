require './ci/common'

# FIXME: use our own brew of MySQL like other flavors

namespace :ci do
  namespace :mysql do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install']

    task before_script: ['ci:common:before_script'] do
      sh %(mysql --protocol=tcp -P 3312 -e "create user 'dog'@'localhost' identified by 'dog'" -uroot -pdatadog)
      sh %(mysql --protocol=tcp -P 3312 -e "GRANT PROCESS, REPLICATION CLIENT ON *.* TO 'dog'@'localhost' \
           WITH MAX_USER_CONNECTIONS 5;" -uroot -pdatadog)
      sh %(mysql --protocol=tcp -P 3312 -e "CREATE DATABASE testdb;" -uroot -pdatadog)
      sh %(mysql --protocol=tcp -P 3312 -e "CREATE TABLE testdb.users (name VARCHAR(20), age INT);" -uroot -pdatadog)
      sh %(mysql --protocol=tcp -P 3312 -e "GRANT SELECT ON testdb.users TO 'dog'@'localhost';" -uroot -pdatadog)
      sh %(mysql --protocol=tcp -P 3312 -e "INSERT INTO testdb.users (name,age) VALUES('Alice',25);" -uroot -pdatadog)
      sh %(mysql --protocol=tcp -P 3312 -e "INSERT INTO testdb.users (name,age) VALUES('Bob',20);" -uroot -pdatadog)
      sh %(mysql --protocol=tcp -P 3312 -e "GRANT SELECT ON performance_schema.* TO 'dog'@'localhost';" -uroot -pdatadog)
      sh %(mysql --protocol=tcp -P 3312 -e "USE testdb; SELECT * FROM users ORDER BY name;" -uroot -pdatadog)
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
      sh %(mysql --protocol=tcp -P 3312 -e "DROP USER 'dog'@'localhost';" -uroot -pdatadog)
      sh %(mysql --protocol=tcp -P 3312 -e "DROP DATABASE testdb;" -uroot -pdatadog)
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
