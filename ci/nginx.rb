require './ci/common'

def nginx_version
  ENV['NGINX_VERSION'] || '1.7.9'
end

def nginx_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/nginx_#{nginx_version}"
end

namespace :ci do
  namespace :nginx do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(nginx_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/nginx-#{nginx_version}.tar.gz\
             http://nginx.org/download/nginx-#{nginx_version}.tar.gz)
        sh %(mkdir -p #{nginx_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/nginx)
        sh %(tar zxf $VOLATILE_DIR/nginx-#{nginx_version}.tar.gz\
             -C $VOLATILE_DIR/nginx --strip-components=1)
        sh %(cd $VOLATILE_DIR/nginx\
             && ./configure --prefix=#{nginx_rootdir} --with-http_stub_status_module\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/nginx/nginx.conf\
           #{nginx_rootdir}/conf/nginx.conf)
      sh %(#{nginx_rootdir}/sbin/nginx -g "pid #{ENV['VOLATILE_DIR']}/nginx.pid;")
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'nginx'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/nginx.pid`)
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
