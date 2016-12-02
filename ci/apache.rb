# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def apache_version
  ENV['FLAVOR_VERSION'] || '2.4.12'
end

def apache_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/apache_#{apache_version}"
end

namespace :ci do
  namespace :apache do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(apache_rootdir)
        # Downloads:
        # http://httpd.apache.org/download.cgi#apache24
        # apr/apr-util on any apache mirror https://www.apache.org/mirrors/
        sh %(curl -s -L\
             -o $VOLATILE_DIR/httpd-#{apache_version}.tar.bz2\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/httpd-#{apache_version}.tar.bz2)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/apr.tar.bz2\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/apr-1.5.1.tar.bz2)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/apr-util.tar.bz2\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/apr-util-1.5.4.tar.bz2)
        sh %(mkdir -p #{apache_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/apache)
        sh %(tar jxf $VOLATILE_DIR/httpd-#{apache_version}.tar.bz2\
             -C $VOLATILE_DIR/apache --strip-components=1)
        sh %(mkdir -p $VOLATILE_DIR/apache/srclib/apr)
        sh %(mkdir -p $VOLATILE_DIR/apache/srclib/apr-util)
        sh %(tar jxf $VOLATILE_DIR/apr.tar.bz2\
             -C $VOLATILE_DIR/apache/srclib/apr --strip-components=1)
        sh %(tar jxf $VOLATILE_DIR/apr-util.tar.bz2\
             -C $VOLATILE_DIR/apache/srclib/apr-util --strip-components=1)
        sh %(cd $VOLATILE_DIR/apache\
             && ./configure --prefix=#{apache_rootdir}\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/apache/httpd.conf\
              #{apache_rootdir}/conf/httpd.conf)
      sh %(sed -i -e 's@%APACHE_ROOTDIR%@#{apache_rootdir}@'\
            #{apache_rootdir}/conf/httpd.conf)
      sh %(sed -i -e "s@%VOLATILE_DIR%@$VOLATILE_DIR@"\
            #{apache_rootdir}/conf/httpd.conf)
      sh %(#{apache_rootdir}/bin/apachectl start)
      # Wait for Apache to start
      Wait.for 'http://localhost:8080', 15
      # Simulate activity to populate metrics
      100.times do
        sh %(curl --silent http://localhost:8080 > /dev/null)
      end
      sleep_for 2
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'apache'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache'] do
      # Useless to cache the conf, as it is regenerated every time
      sh %(mkdir -p $VOLATILE_DIR/apache)
      sh %(mv #{apache_rootdir}/conf/httpd.conf $VOLATILE_DIR/apache/httpd.conf)
    end

    task cleanup: ['ci:common:cleanup'] do
      # We need to move the conf back to apache's dir before stopping
      sh %(mv $VOLATILE_DIR/apache/httpd.conf #{apache_rootdir}/conf/httpd.conf)
      sh %(#{apache_rootdir}/bin/apachectl stop)
    end

    task :execute do
      Rake::Task['ci:common:execute'].invoke(flavor)
    end
  end
end
