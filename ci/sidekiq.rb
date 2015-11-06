require './ci/common'
require './ci/redis'

namespace :ci do
  namespace :sidekiq do |flavor|
    task before_install: ['ci:redis:before_install']
    task install: ['ci:redis:install']
    task before_script: ['ci:redis:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'sidekiq'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:redis:before_cache']
    task cache: ['ci:redis:cache']
    task cleanup: ['ci:redis:cleanup']

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
