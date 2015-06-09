require './ci/common'

namespace :ci do
  namespace :docker do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      sh %(docker pull redis:latest)
      sh %(docker pull mongo:latest)
      sh %(docker run -d --name redis -p 6380:6380 redis)
      sh %(docker run -d --name mongo -p 27018:27018 mongo)
    end

    task before_script: ['ci:common:before_script'] do
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'docker'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill redis)
      sh %(docker rm redis)
      sh %(docker kill mongo)
      sh %(docker rm mongo)
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
