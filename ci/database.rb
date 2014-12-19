require './ci/common'

namespace :ci do
  namespace :database do
    task :before_install => ['ci:common:before_install'] do
      # postgres
      # TODO: rely on Travis preinstalled postgres instances, fetch it from PG repo?
      sh "sudo service postgresql stop"
      # FIXME: include this as a version number in the matrix
      sh "sudo service postgresql start 9.3"

      # mysql - should already be installed to - ensure it is started
      sh %Q{sudo service mysql restart}
      # couchdb - should already be installed to - ensure it is started
      sh %Q{sudo service couchdb restart}

      # don't really like it but wait a few seconds for all these services to init
      # especially couchdb
      sleep(5)
    end

    task :install => ['ci:common:install']

    task :before_script => ['ci:common:before_script'] do
      # postgres
      sh %Q{psql -U postgres -c "create user datadog with password 'datadog'"}
      sh %Q{psql -U postgres -c "grant SELECT ON pg_stat_database to datadog"}
      sh %Q{psql -U postgres -c "CREATE DATABASE datadog_test" postgres}
      sh %Q{psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE datadog_test to datadog"}
      sh %Q{psql -U datadog -c "CREATE TABLE Persons (PersonID int, LastName varchar(255), FirstName varchar(255), Address varchar(255), City varchar(255))" datadog_test}

      # mysql
      sh %Q{mysql -e "create user 'dog'@'localhost' identified by 'dog'"}
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'couchdb',
        'mysql',
        'postgres'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
