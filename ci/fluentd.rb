# (C) Datadog, Inc. 2014-2016
# (C) Takumi Sakamoto <takumi.saka@gmail.com> 2014
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

namespace :ci do
  namespace :fluentd do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      sh %(gem install fluentd -v 0.12.22 --no-ri --no-rdoc)
    end

    task before_script: ['ci:common:before_script'] do
      pid = spawn %(fluentd -c $TRAVIS_BUILD_DIR/ci/resources/fluentd/td-agent.conf)
      Process.detach(pid)
      sh %(echo #{pid} > $VOLATILE_DIR/fluentd.pid)
      # Waiting for fluentd to start
      Wait.for 24_220
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'fluentd'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/fluentd.pid`)
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
      raise exception if exception
    end
  end
end
