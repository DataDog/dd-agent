require './ci/common'

def kong_version
  ENV['FLAVOR_VERSION'] || '0.5.2'
end

def kong_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/kong_#{kong_version}"
end

def cassandra_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/cassandra"
end

namespace :ci do
  namespace :kong do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(kong_rootdir)
        # Download Kong, Cassandra. curl, openjdk 1.8, wget, make, gcc must be already installed
        sh %(curl -L -o $VOLATILE_DIR/kong-#{kong_version}.tar.gz\
            https://s3.amazonaws.com/kong-dd-agent-trusty/kong-trusty-0.5.2.tar.gz)
        sh %(curl -s -L -o $VOLATILE_DIR/apache-cassandra-2.1.3-bin.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/apache-cassandra-2.1.3-bin.tar.gz)
        sh %(mkdir -p #{kong_rootdir})
        sh %(mkdir -p #{cassandra_rootdir})
        sh %(tar zxf $VOLATILE_DIR/kong-#{kong_version}.tar.gz\
             -C #{kong_rootdir} --strip-components=1)
        sh %(tar zxf $VOLATILE_DIR/apache-cassandra-2.1.3-bin.tar.gz\
             -C #{cassandra_rootdir} --strip-components=1)
        sh %(bash #{kong_rootdir}/configure.sh)
        sh %(touch #{kong_rootdir}/rocks_config.lua)
        sh %(echo 'rocks_trees = {{ name = [[system]], root = [[#{kong_rootdir}/usr/local]] }}' >>\
             #{kong_rootdir}/rocks_config.lua)
        ENV['LUAROCKS_CONFIG'] = "#{kong_rootdir}/rocks_config.lua"
        ENV['LUA_PATH'] = "#{kong_rootdir}/usr/local/share/lua/5.1/?.lua;\
#{kong_rootdir}/usr/local/share/lua/5.1/?/init.lua;\
#{kong_rootdir}/usr/local/openresty/lualib/?.lua"
        ENV['LUA_CPATH'] = "#{kong_rootdir}/usr/local/lib/lua/5.1/?.so"
        ENV['LD_LIBRARY_PATH'] = "#{kong_rootdir}/usr/local/lib"
        ENV['PATH'] = "#{kong_rootdir}/usr/local/openresty/nginx/sbin:#{kong_rootdir}/dnsmasq/usr/local/sbin:#{ENV['PATH']}"
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(cat #{kong_rootdir}/rocks_config.lua)
      sh %(ls #{kong_rootdir}/usr/local/share/lua/5.1/yaml/ )
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/kong/cassandra_2.1.yaml #{cassandra_rootdir}/conf/cassandra.yaml)
      sh %(#{cassandra_rootdir}/bin/cassandra -p $VOLATILE_DIR/cass.pid > /dev/null)
      # Create temp cassandra workdir
      sh %(mkdir -p $VOLATILE_DIR/cassandra)
      Wait.for 9042, 10
      sh %(#{kong_rootdir}/usr/local/bin/kong start -c #{kong_rootdir}/kong.yml)
      Wait.for 8001, 10
      sleep_for 10
      sh %(curl http://localhost:8001/status)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'kong'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: :cleanup

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/cass.pid`)
      sleep_for 3
      sh %(rm -rf #{cassandra_rootdir}/data)
      sh %(kill `cat #{kong_rootdir}/usr/local/kong/kong.pid`)
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
      fail exception if exception
    end
  end
end
