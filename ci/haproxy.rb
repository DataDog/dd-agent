require './ci/common'

def haproxy_version
  ENV['HAPROXY_VERSION'] || '1.5.10'
end

def haproxy_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/haproxy_#{haproxy_version}"
end

namespace :ci do
  namespace :haproxy do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(haproxy_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/haproxy-#{haproxy_version}.tar.gz\
             http://www.haproxy.org/download/#{haproxy_version[0..2]}/src/haproxy-#{haproxy_version}.tar.gz)
        sh %(mkdir -p #{haproxy_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/haproxy)
        sh %(tar zxf $VOLATILE_DIR/haproxy-#{haproxy_version}.tar.gz\
             -C $VOLATILE_DIR/haproxy --strip-components=1)
        sh %(cd $VOLATILE_DIR/haproxy\
             && make -j $CONCURRENCY TARGET=linux2628 USE_PCRE=1 USE_OPENSSL=1 USE_ZLIB=1)
        sh %(cp $VOLATILE_DIR/haproxy/haproxy #{haproxy_rootdir})
        # FIXME: use that we don't start haproxy in the tests
        sh %(mkdir -p #{ENV['INTEGRATIONS_DIR']}/bin)
        sh %(cp $VOLATILE_DIR/haproxy/haproxy #{ENV['INTEGRATIONS_DIR']}/bin/)
      end
    end

    task :before_script => ['ci:common:before_script']

    task :script => ['ci:common:script'] do
      this_provides = [
        'haproxy'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup']

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
