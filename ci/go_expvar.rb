# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

namespace :ci do
  namespace :go_expvar do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install']

    task before_script: ['ci:common:before_script'] do
      pid = spawn %(go run $TRAVIS_BUILD_DIR/ci/resources/go_expvar/test_expvar.go)
      Process.detach(pid)
      sh %(echo #{pid} > $VOLATILE_DIR/go_expvar.pid)
      Wait.for 8079
      2.times do
        sh %(curl -s http://localhost:8079?user=123456)
      end
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'go_expvar'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill -INT `cat $VOLATILE_DIR/go_expvar.pid` || true)
      sh %(rm -f $VOLATILE_DIR/go_expvar.pid)
      # There is two processes running when launching `go run` on Mac
      sh %(pkill 'test_expvar' || true)
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
