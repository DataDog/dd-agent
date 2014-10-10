require './ci/common'

namespace :ci do
  namespace :cassandra do
    task :before_install => ['ci:common:before_install'] do
      sh %Q{curl http://apache.mesi.com.ar/cassandra/2.0.9/apache-cassandra-2.0.9-bin.tar.gz | tar -C /tmp -xz}
    end

    task :install => ['ci:common:install']

    task :before_script => ['ci:common:before_script'] do
      sh %Q{sudo /tmp/apache-cassandra-2.0.9/bin/cassandra}
      # Wait for cassandra to init
      sh %Q{sleep 10}
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'cassandra',
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
