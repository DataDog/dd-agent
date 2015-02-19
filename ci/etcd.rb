require './ci/common'

def etcd_version
  ENV['ETCD_VERSION'] || '2.0.3'
end

def etcd_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/etcd_#{etcd_version}"
end

namespace :ci do
  namespace :etcd do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(etcd_rootdir)
        sh %(curl -s -L -o $VOLATILE_DIR/etcd.tar.gz\
              https://github.com/coreos/etcd/releases/download/v#{etcd_version}/etcd-v#{etcd_version}-linux-amd64.tar.gz)
        sh %(mkdir -p #{etcd_rootdir})
        sh %(tar xzvf $VOLATILE_DIR/etcd.tar.gz\
                      -C #{etcd_rootdir}\
                      --strip-components=1 >/dev/null)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      sh %(cd $VOLATILE_DIR && #{etcd_rootdir}/etcd >/dev/null &)
      sleep_for 10
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'etcd'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup'] do
      # This will delete the temp directory of etcd,
      # so the etcd process will kill himself quickly after that (<10s)
      sh %(rm -rf $VOLATILE_DIR/*etcd*)
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
