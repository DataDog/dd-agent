require './ci/common'

namespace :ci do
  namespace :fluentd do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      sh %(gem install fluentd --no-ri --no-rdoc)
    end

    task :before_script => ['ci:common:before_script'] do
      sh %(fluentd -c $TRAVIS_BUILD_DIR/ci/resources/fluentd/td-agent.conf &)
      sleep_for 10
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'fluentd'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup']
    # FIXME: stop fluentd

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
