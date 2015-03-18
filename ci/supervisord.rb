require './ci/common'

namespace :ci do
  namespace :supervisord do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
        sh %(pip install supervisor)
    end

    task :before_script => ['ci:common:before_script'] do
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/supervisord/supervisord.conf $VOLATILE_DIR/)
      sh %(sed -i -- 's/VOLATILE_DIR/#{ENV['VOLATILE_DIR'].gsub '/','\/'}/g' $VOLATILE_DIR/supervisord.conf)

      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/supervisord/supervisord.yaml $VOLATILE_DIR/)
      sh %(sed -i -- 's/VOLATILE_DIR/#{ENV['VOLATILE_DIR'].gsub '/','\/'}/g' $VOLATILE_DIR/supervisord.yaml)

      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/supervisord/program_1.sh $VOLATILE_DIR/)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/supervisord/program_2.sh $VOLATILE_DIR/)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/supervisord/program_3.sh $VOLATILE_DIR/)
      sh %(chmod a+x $VOLATILE_DIR/program_*.sh)

      sh %(supervisord -c $VOLATILE_DIR/supervisord.conf)
      sh %(sed -i -- 's/VOLATILE_DIR/#{ENV['VOLATILE_DIR'].gsub '/','\/'}/g' $VOLATILE_DIR/supervisord.conf)

      sleep_for 10
    end

    task :script => ['ci:common:script'] do
      Rake::Task['ci:common:run_tests'].invoke(['supervisord'])
    end

    task :cleanup => ['ci:common:cleanup'] do
      sh %(rm -f $VOLATILE_DIR/supervisord.conf)
      sh %(rm -f $VOLATILE_DIR/supervisord.yaml)
      sh %(rm -f $VOLATILE_DIR/program*.sh)
      sh %(rm -f $VOLATILE_DIR/supervisord.conf)
      sh %(rm -f $VOLATILE_DIR/supervisord.log)
      sh %(rm -f $VOLATILE_DIR/supervisord.pid)
      sh %(rm -f $VOLATILE_DIR/program*.log)
      sh %(rm -f $VOLATILE_DIR/ci.log)

      sh %(unlink $VOLATILE_DIR/supervisor.sock)
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
      fail exception if exception
    end
  end
end
