require './ci/common'

def es_version
  ENV['ES_VERSION'] || '1.4.2'
end

def es_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/es_#{es_version}"
end

namespace :ci do
  namespace :elasticsearch do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(es_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/elasticsearch-#{es_version}.tar.gz\
             https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-#{es_version}.tar.gz)
        sh %(mkdir -p #{es_rootdir})
        sh %(tar zxf $VOLATILE_DIR/elasticsearch-#{es_version}.tar.gz\
             -C #{es_rootdir} --strip-components=1)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      sh %(#{es_rootdir}/bin/elasticsearch -d)
      sleep_for 10
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'elasticsearch'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup']
    # FIXME: stop elasticsearch

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
