require './ci/common'

namespace :ci do
  namespace :default do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install']

    task :before_script => ['ci:common:before_script']

    task :lint do
      sh %(find . -name '*.py' -not \\( -path '*.cache*' -or -path '*embedded*' -or -path '*venv*' \\) | xargs -n 1 pylint --rcfile=./.pylintrc)
    end

    task :script => ['ci:common:script', :lint] do
      Rake::Task['ci:common:run_tests'].invoke('default')
    end

    task :before_cache => ['ci:common:before_cache']

    task :cache => ['ci:common:cache']

    task :cleanup => ['ci:common:cleanup']

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
      if ENV['TRAVIS'] && ENV['AWS_SECRET_ACCESS_KEY']
        %w(before_cache cache).each do |t|
          Rake::Task["#{flavor.scope.path}:#{t}"].invoke
        end
      end
      fail exception if exception
    end
  end
end
