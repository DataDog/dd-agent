# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def nginx_version
  ENV['FLAVOR_VERSION'] || '1.7.11'
end

def nginx_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/nginx_#{nginx_version}"
end

namespace :ci do
  namespace :nginx do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      # Downloads
      # http://nginx.org/download/nginx-#{nginx_version}.tar.gz
      unless Dir.exist? File.expand_path(nginx_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/nginx-#{nginx_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/nginx-#{nginx_version}.tar.gz)
        sh %(mkdir -p #{nginx_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/nginx)
        sh %(tar zxf $VOLATILE_DIR/nginx-#{nginx_version}.tar.gz\
             -C $VOLATILE_DIR/nginx --strip-components=1)
        sh %(cd $VOLATILE_DIR/nginx\
             && ./configure --prefix=#{nginx_rootdir} --with-http_stub_status_module --with-http_ssl_module\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/nginx/nginx.conf\
           #{nginx_rootdir}/conf/nginx.conf)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/nginx/testing.crt\
           #{nginx_rootdir}/conf/testing.crt)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/nginx/testing.key\
           #{nginx_rootdir}/conf/testing.key)
      sh %(#{nginx_rootdir}/sbin/nginx -g "pid #{ENV['VOLATILE_DIR']}/nginx.pid;")
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'nginx'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache'] do
      # Conf is regenerated at every run
      sh %(rm -f #{nginx_rootdir}/conf/nginx.conf)
      sh %(rm -f #{nginx_rootdir}/conf/testing.cert)
      sh %(rm -f #{nginx_rootdir}/conf/testing.key)
    end

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/nginx.pid`)
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
