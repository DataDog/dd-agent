require './ci/common'

def kong_version
  ENV['FLAVOR_VERSION'] || '0.8.1'
end

def kong_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/kong"
end

def kong_bin
  "#{kong_rootdir}/bin/kong"
end

def cassandra_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/cassandra"
end

def cassandra_bin
  "#{cassandra_rootdir}/bin/cassandra"
end

# rubocop:disable AbcSize
def set_kong_env
  ENV['LUA_VERSION'] = 'luajit-2.1'
  ENV['CASSANDRA_VERSION'] = '2.2.4'
  ENV['LUAROCKS_VERSION'] = '2.3.0'
  ENV['OPENSSL_VERSION'] = '1.0.2f'
  ENV['OPENRESTY_VERSION'] = '1.9.7.3'
  ENV['SERF_VERSION'] = '0.7.0'
  ENV['DNSMASQ_VERSION'] = '2.75'
  ENV['LUAJIT_VERSION'] = '2.1'
  ENV['LUAJIT_DIR'] = "#{ENV['INTEGRATIONS_DIR']}/lua"
  ENV['LUAROCKS_DIR'] = "#{ENV['INTEGRATIONS_DIR']}/luarocks"
  ENV['OPENRESTY_DIR'] = "#{ENV['INTEGRATIONS_DIR']}/openresty"
  ENV['SERF_DIR'] = "#{ENV['INTEGRATIONS_DIR']}/serf"
  ENV['DNSMASQ_DIR'] = "#{ENV['INTEGRATIONS_DIR']}/dnsmasq"
  ENV['UUID_DIR'] = "#{ENV['INTEGRATIONS_DIR']}/libuuid"
end

def set_kong_path
  ENV['CASSANDRA_DIR'] = "#{ENV['INTEGRATIONS_DIR']}/cassandra"
  ENV['CASSANDRA_HOSTS'] = '127.0.0.1'
  ENV['LUA_CPATH'] = "./?.so;#{ENV['LUAROCKS_DIR']}/lib/lua/5.1/?.so;"
  ENV['LUA_PATH'] = "./?.lua;#{ENV['LUAROCKS_DIR']}/share/lua/5.1/?.lua;#{ENV['LUAROCKS_DIR']}/share/lua/5.1/?/init.lua;\
      #{ENV['LUAROCKS_DIR']}/lib/lua/5.1/?.lua;"
  ENV['PATH'] = "#{ENV['LUAJIT_DIR']}/bin:#{ENV['LUAJIT_DIR']}/include/#{ENV['LUA_VERSION']}:#{ENV['LUAROCKS_DIR']}/bin:#{ENV['PATH']}"
  ENV['PATH'] = "#{ENV['OPENRESTY_DIR']}/nginx/sbin:#{ENV['SERF_DIR']}:#{ENV['DNSMASQ_DIR']}/usr/local/sbin:#{ENV['PATH']}"
end
# rubocop:enable AbcSize

namespace :ci do
  namespace :kong do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless File.exist? cassandra_bin
        sh %(curl -s -S -L -o $VOLATILE_DIR/apache-cassandra-2.2.8-bin.tar.gz\
          http://apache.trisect.eu/cassandra/2.2.8/apache-cassandra-2.2.8-bin.tar.gz)
        sh %(mkdir -p #{cassandra_rootdir})
        sh %(tar zxf $VOLATILE_DIR/apache-cassandra-2.2.8-bin.tar.gz\
          -C #{cassandra_rootdir} --strip-components=1)
      end

      unless File.exist? kong_bin
        # Download Kong. curl, openjdk 1.8, wget, make, gcc must be already installed
        sh %(mkdir -p #{kong_rootdir})
        sh %(cp $TRAVIS_BUILD_DIR/ci/resources/kong/*.sh #{kong_rootdir})
        set_kong_env
        sh %(bash #{kong_rootdir}/setup_uuid.sh)
        sh %(bash #{kong_rootdir}/setup_lua.sh)
        sh %(bash #{kong_rootdir}/setup_openresty.sh)
        sh %(bash #{kong_rootdir}/setup_serf.sh)
        sh %(bash #{kong_rootdir}/setup_dnsmasq.sh)
        set_kong_path
        sh %(bash #{kong_rootdir}/kong_install.sh)
        sh %(cd #{kong_rootdir} && make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      set_kong_env
      set_kong_path
      sh %(mkdir -p $VOLATILE_DIR/cassandra)
      sh %(#{cassandra_rootdir}/bin/cassandra -p $VOLATILE_DIR/cass.pid > /dev/null)
      Wait.for 9042, 60
      kong_yml = "#{ENV['TRAVIS_BUILD_DIR']}/ci/resources/kong/kong_DEVELOPMENT.yml"
      sh %(kong migrations -c #{kong_yml} up)
      sh %(kong start -c #{kong_yml})
      Wait.for 8001, 10
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'kong'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: :cleanup

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/cass.pid || true`)
      sleep_for 3
      sh %(rm -rf #{ENV['INTEGRATIONS_DIR']}/cassandra/data)
      sh %(rm -rf #{ENV['INTEGRATIONS_DIR']}/cassandra/logs)
      sh %(kill `cat $INTEGRATIONS_DIR/kong/nginx.pid` || true)
      sh %(kill `cat $INTEGRATIONS_DIR/kong/dnsmasq.pid` || true)
      sh %(kill `cat $INTEGRATIONS_DIR/kong/serf.pid` || true)
    end

    task :execute do
      Rake::Task['ci:common:execute'].invoke(flavor)
    end
  end
end
