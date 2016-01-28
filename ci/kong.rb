require './ci/common'

def kong_version
  ENV['FLAVOR_VERSION'] || '0.6.0'
end

def kong_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/kong"
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
        ENV['LUA_VERSION']="luajit-2.1"
        ENV['CASSANDRA_VERSION']="2.2.4"
        ENV['LUAROCKS_VERSION']="2.2.2"
        ENV['OPENSSL_VERSION']="1.0.2f"
        ENV['OPENRESTY_VERSION']="1.9.3.1"
        ENV['SERF_VERSION']="0.7.0"
        ENV['DNSMASQ_VERSION']="2.75"
        ENV['LUAJIT_DIR']="#{ENV['INTEGRATIONS_DIR']}/luajit"
        ENV['LUAROCKS_DIR']="#{ENV['INTEGRATIONS_DIR']}/luarocks"
        ENV['OPENRESTY_DIR']="#{ENV['INTEGRATIONS_DIR']}/openresty"
        ENV['SERF_DIR']="#{ENV['INTEGRATIONS_DIR']}/serf"
        ENV['DNSMASQ_DIR']="#{ENV['INTEGRATIONS_DIR']}/dnsmasq"
        ENV['CASSANDRA_HOSTS']="127.0.0.1"

        
        sh %(mkdir -p #{kong_rootdir})
        sh %(cp $TRAVIS_BUILD_DIR/ci/resources/kong/*.sh #{kong_rootdir})

        sh %(bash #{kong_rootdir}/setup_lua.sh)
        sh %(bash #{kong_rootdir}/setup_openresty.sh)
        sh %(bash #{kong_rootdir}/setup_serf.sh)
        sh %(bash #{kong_rootdir}/setup_dnsmasq.sh)

        ENV['LUA_CPATH']="./?.so;$LUAROCKS_DIR/lib/lua/5.1/?.so;"
        ENV['LUA_PATH']="./?.lua;$LUAROCKS_DIR/share/lua/5.1/?.lua;$LUAROCKS_DIR/share/lua/5.1/?/init.lua;$LUAROCKS_DIR/lib/lua/5.1/?.lua;"
        ENV['PATH']="$LUAJIT_DIR/bin:$LUAROCKS_DIR/bin:$OPENRESTY_DIR/nginx/sbin:$SERF_DIR:$DNSMASQ_DIR/usr/local/sbin:#{ENV['PATH']}"
		
		sh %(echo $PATH)
		sh %(echo $LUAROCKS_DIR)
		sh %(echo $LUA_CPATH)
		sh %(echo $LUA_PATH)
        sh %(bash #{kong_rootdir}/kong_install.sh)

        sh %(curl -s -L -o $VOLATILE_DIR/apache-cassandra-2.1.3-bin.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/apache-cassandra-2.1.3-bin.tar.gz)
        sh %(mkdir -p #{cassandra_rootdir})
        sh %(tar zxf $VOLATILE_DIR/apache-cassandra-2.1.3-bin.tar.gz\
             -C #{cassandra_rootdir} --strip-components=1)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/kong/cassandra_2.1.yaml #{cassandra_rootdir}/conf/cassandra.yaml)
      sh %(#{cassandra_rootdir}/bin/cassandra -p $VOLATILE_DIR/cass.pid > /dev/null)
       # Create temp cassandra workdir
      sh %(mkdir -p $VOLATILE_DIR/cassandra)
      Wait.for 9042, 10
      sh %(kong start)
      Wait.for 8001, 10
      sleep_for 5
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
      sh %(kill `cat /usr/local/kong/nginx.pid`)
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
