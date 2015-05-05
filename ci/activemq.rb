require './ci/common'

def activemq_version
  ENV['FLAVOR_VERSION'] || '5.11.1'
end

def activemq_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/activemq_#{activemq_version}"
end

namespace :ci do
  namespace :activemq do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(activemq_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/activemq-#{activemq_version}.tar.gz\
             http://archive.apache.org/dist/activemq/#{activemq_version}/apache-activemq-#{activemq_version}-bin.tar.gz)
        sh %(mkdir -p #{activemq_rootdir})
        sh %(tar zxf $VOLATILE_DIR/activemq-#{activemq_version}.tar.gz\
             -C #{activemq_rootdir} --strip-components=1)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      sh %(tar zxf $TRAVIS_BUILD_DIR/ci/resources/activemq/kahadb.tar.gz\
           -C #{activemq_rootdir}/data)
      sh %(#{activemq_rootdir}/bin/activemq start)
      Wait.for 'http://localhost:8161'
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'activemq'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :before_cache => ['ci:common:before_cache'] do
      sh %(rm -rf #{activemq_rootdir}/data/*)
    end

    task :cache => ['ci:common:cache']

    task :cleanup => ['ci:common:cleanup'] do
      sh %(#{activemq_rootdir}/bin/activemq stop)
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
      if ENV['TRAVIS']
        %w(before_cache cache).each do |t|
          Rake::Task["#{flavor.scope.path}:#{t}"].invoke
        end
      end
      fail exception if exception
    end
  end
end
