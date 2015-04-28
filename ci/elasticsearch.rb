require './ci/common'

def es_version
  ENV['FLAVOR_VERSION'] || '1.4.2'
end

def es_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/es_#{es_version}"
end

namespace :ci do
  namespace :elasticsearch do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(es_rootdir)
        # Downloads
        # https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-#{es_version}.tar.gz
        sh %(curl -s -L\
             -o $VOLATILE_DIR/elasticsearch-#{es_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/elasticsearch-#{es_version}.tar.gz)
        sh %(mkdir -p #{es_rootdir})
        sh %(tar zxf $VOLATILE_DIR/elasticsearch-#{es_version}.tar.gz\
             -C #{es_rootdir} --strip-components=1)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      pid = spawn %(#{es_rootdir}/bin/elasticsearch)
      Process.detach(pid)
      sh %(echo #{pid} > $VOLATILE_DIR/elasticsearch.pid)
      sleep_for 10
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'elasticsearch'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :before_cache => ['ci:common:before_cache'] do
      Rake::Task['ci:elasticsearch:cleanup'].invoke
    end

    task :cache => ['ci:common:cache']

    task :cleanup => ['ci:common:cleanup'] do
      # FIXME: remove `|| true` when we drop support for ES 0.90.x
      # (the only version spawning a process in background)
      sh %(kill `cat $VOLATILE_DIR/elasticsearch.pid` || true)
      sleep_for 1
      sh %(rm -rf #{es_rootdir}/data || true)
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
      if ENV['TRAVIS'] && ENV['AWS_SECRET_ACCESS_KEY']
        %w(before_cache cache).each do |t|
          Rake::Task["#{flavor.scope.path}:#{t}"].invoke
        end
      end
      fail exception if exception
    end
  end
end
