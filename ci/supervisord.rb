# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def supervisor_version
  ENV['FLAVOR_VERSION'] || '3.3.0'
end

def supervisor_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/supervisor_#{supervisor_version}_#{ENV['TRAVIS_PYTHON_VERSION']}"
end

namespace :ci do
  namespace :supervisord do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(supervisor_rootdir)
        sh %(pip install supervisor==#{supervisor_version} --ignore-installed\
             --install-option="--prefix=#{supervisor_rootdir}")
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(mkdir -p $VOLATILE_DIR/supervisor)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/supervisord/supervisord.conf\
           $VOLATILE_DIR/supervisor/)
      sh %(sed -i -- 's/VOLATILE_DIR/#{ENV['VOLATILE_DIR'].gsub '/', '\/'}/g'\
         $VOLATILE_DIR/supervisor/supervisord.conf)

      3.times do |i|
        sh %(cp $TRAVIS_BUILD_DIR/ci/resources/supervisord/program_#{i}.sh\
             $VOLATILE_DIR/supervisor/)
      end
      sh %(chmod a+x $VOLATILE_DIR/supervisor/program_*.sh)

      sh %(#{supervisor_rootdir}/bin/supervisord\
           -c $VOLATILE_DIR/supervisor/supervisord.conf)
      3.times { |i| Wait.for "#{ENV['VOLATILE_DIR']}/supervisor/started_#{i}" }
      # And we still have to sleep a little, because sometimes supervisor
      # doesn't immediately realize that its processes are running
      sleep_for 1
    end

    task script: ['ci:common:script'] do
      Rake::Task['ci:common:run_tests'].invoke(['supervisord'])
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/supervisor/supervisord.pid`)
      sh %(rm -rf $VOLATILE_DIR/supervisor)
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
