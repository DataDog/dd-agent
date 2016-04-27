# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def nginx_version
  ENV['NGINX_VERSION'] || '1.7.11'
end

def php_version
  ENV['PHP_VERSION'] || '5.6.7'
end

def phpfpm_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/phpfpm_#{php_version}"
end

namespace :ci do
  namespace :phpfpm do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      # Downloads
      # http://nginx.org/download/nginx-#{nginx_version}.tar.gz
      # http://us1.php.net/get/php-#{php_version}.tar.bz2/from/this/mirror
      unless Dir.exist? File.expand_path(phpfpm_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/nginx-#{nginx_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/nginx-#{nginx_version}.tar.gz)
        sh %(mkdir -p #{phpfpm_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/nginx)
        sh %(tar zxf $VOLATILE_DIR/nginx-#{nginx_version}.tar.gz\
             -C $VOLATILE_DIR/nginx --strip-components=1)
        sh %(cd $VOLATILE_DIR/nginx\
             && ./configure --prefix=#{phpfpm_rootdir} --with-http_stub_status_module\
             && make -j $CONCURRENCY\
             && make install)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/php-#{php_version}.tar.bz2\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/php-#{php_version}.tar.bz2)
        sh %(mkdir -p $VOLATILE_DIR/php)
        sh %(tar jxf $VOLATILE_DIR/php-#{php_version}.tar.bz2\
             -C $VOLATILE_DIR/php --strip-components=1)
        sh %(cd $VOLATILE_DIR/php\
             && ./configure --prefix=#{phpfpm_rootdir} --enable-fpm\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/phpfpm/nginx.conf\
           #{phpfpm_rootdir}/conf/nginx.conf)
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/phpfpm/php-fpm.conf\
           #{phpfpm_rootdir}/etc/php-fpm.conf)
      sh %(#{phpfpm_rootdir}/sbin/nginx -g "pid #{ENV['VOLATILE_DIR']}/nginx.pid;")
      sh %(#{phpfpm_rootdir}/sbin/php-fpm -g #{ENV['VOLATILE_DIR']}/php-fpm.pid)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'phpfpm'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/nginx.pid`)
      sh %(kill `cat $VOLATILE_DIR/php-fpm.pid`)
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
