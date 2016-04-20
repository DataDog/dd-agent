# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def couchdb_version
  ENV['FLAVOR_VERSION'] || '1.6.1'
end

def couchdb_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/couchdb_#{couchdb_version}"
end

namespace :ci do
  namespace :couchdb do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      if !Dir.exist? File.expand_path(couchdb_rootdir)
        # Downloads
        # http://www.erlang.org/download/otp_src_17.4.tar.gz
        # http://mirrors.gigenet.com/apache/couchdb/source/#{couchdb_version}/apache-couchdb-#{couchdb_version}.tar.gz
        # http://ftp.mozilla.org/pub/mozilla.org/js/js185-1.0.0.tar.gz
        # http://download.icu-project.org/files/icu4c/54.1/icu4c-54_1-src.tgz
        sh %(curl -s -L\
             -o $VOLATILE_DIR/erlang.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/otp_src_17.4.tar.gz)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/couchdb-#{couchdb_version}.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/apache-couchdb-#{couchdb_version}.tar.gz)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/js185.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/js185-1.0.0.tar.gz)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/icu.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/icu4c-54_1-src.tgz)
        sh %(mkdir -p $VOLATILE_DIR/couchdb)
        sh %(mkdir -p $VOLATILE_DIR/js185)
        sh %(mkdir -p $VOLATILE_DIR/icu)
        sh %(mkdir -p $VOLATILE_DIR/erlang)
        sh %(tar zxf $VOLATILE_DIR/erlang.tar.gz\
             -C $VOLATILE_DIR/erlang --strip-components=1)
        sh %(tar zxf $VOLATILE_DIR/couchdb-#{couchdb_version}.tar.gz\
             -C $VOLATILE_DIR/couchdb --strip-components=1)
        sh %(tar zxf $VOLATILE_DIR/js185.tar.gz\
             -C $VOLATILE_DIR/js185 --strip-components=1)
        sh %(tar zxf $VOLATILE_DIR/icu.tar.gz\
             -C $VOLATILE_DIR/icu --strip-components=1)
        sh %(cd $VOLATILE_DIR/erlang\
             && ./configure --prefix=#{couchdb_rootdir}/ 2>&1 >> $VOLATILE_DIR/ci.log\
             && make -j $CONCURRENCY 2>&1 >> $VOLATILE_DIR/ci.log\
             && make install 2>&1 >> $VOLATILE_DIR/ci.log)
        sh %(cd $VOLATILE_DIR/js185/js/src\
             && ./configure --prefix=#{couchdb_rootdir}/ 2>&1 >> $VOLATILE_DIR/ci.log\
             && make -j $CONCURRENCY 2>&1 >> $VOLATILE_DIR/ci.log\
             && make install 2>&1 >> $VOLATILE_DIR/ci.log)
        sh %(cd $VOLATILE_DIR/icu/source\
             && ./configure --prefix=#{couchdb_rootdir}/ 2>&1 >> $VOLATILE_DIR/ci.log\
             && make -j $CONCURRENCY 2>&1 >> $VOLATILE_DIR/ci.log\
             && make install 2>&1 >> $VOLATILE_DIR/ci.log)
        ENV['PATH'] = "#{couchdb_rootdir}/bin:#{ENV['PATH']}"
        ENV['LD_LIBRARY_PATH'] = "#{couchdb_rootdir}/lib:#{ENV['LD_LIBRARY_PATH']}"
        # For macs
        ENV['DYLD_LIBRARY_PATH'] = "#{couchdb_rootdir}/lib:#{ENV['DYLD_LIBRARY_PATH']}"
        sh %(cd $VOLATILE_DIR/couchdb\
             && ./configure --prefix=#{couchdb_rootdir} --with-js-lib=#{couchdb_rootdir}/lib --with-js-include=#{couchdb_rootdir}/include/js\
             && make -j $CONCURRENCY\
             && make install)
      else
        # Still needed to start
        ENV['PATH'] = "#{couchdb_rootdir}/bin:#{ENV['PATH']}"
        ENV['LD_LIBRARY_PATH'] = "#{couchdb_rootdir}/lib:#{ENV['LD_LIBRARY_PATH']}"
        ENV['DYLD_LIBRARY_PATH'] = "#{couchdb_rootdir}/lib:#{ENV['DYLD_LIBRARY_PATH']}"
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(#{couchdb_rootdir}/bin/couchdb -b)
      # Couch takes some time to start
      Wait.for 5984

      # Create a test database
      sh %(curl -X PUT http://localhost:5984/kennel)

      # Create a user
      sh %(curl -X PUT http://localhost:5984/_config/admins/dduser -d '"pawprint"')

      # Restrict test databse to authenticated user
      sh %(curl -X PUT http://dduser:pawprint@127.0.0.1:5984/kennel/_security \
           -d '{"admins":{"names":[],"roles":[]},"members":{"names":["dduser"],"roles":[]}}')
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'couchdb'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache'] do
      # It's the pid file which changes eveytime,
      # so let's actually cleanup before cache
      Rake::Task['ci:couchdb:cleanup'].invoke
    end

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(#{couchdb_rootdir}/bin/couchdb -k)
      sh %(rm -f #{couchdb_rootdir}/var/run/couchdb/couchdb.pid)
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
