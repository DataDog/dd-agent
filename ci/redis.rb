require './ci/common'

def redis_version
  ENV['REDIS_VERSION'] || '2.8'
end

def redis_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/redis_#{redis_version}"
end

namespace :ci do
  namespace :redis do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(redis_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/redis.zip\
             https://github.com/antirez/redis/archive/#{redis_version}.zip)
        sh %(mkdir -p #{redis_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/redis)
        sh %(unzip -x $VOLATILE_DIR/redis.zip -d $VOLATILE_DIR/)
        sh %(mv -f $VOLATILE_DIR/redis-*/* #{redis_rootdir})
        sh %(cd #{redis_rootdir} && make -j $CONCURRENCY)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      # Run redis !
      sh %(#{redis_rootdir}/src/redis-server\
           $TRAVIS_BUILD_DIR/ci/resources/redis/auth.conf)
      sh %(#{redis_rootdir}/src/redis-server\
           $TRAVIS_BUILD_DIR/ci/resources/redis/noauth.conf)
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'redis'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup']
    # FIXME: stop redis

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
