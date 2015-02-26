require './ci/common'

def snmpd_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/snmpd"
end

namespace :ci do
  namespace :snmpd do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(snmpd_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/snmpd.tar.gz\
             http://sourceforge.net/projects/net-snmp/files/net-snmp/5.7.3/net-snmp-5.7.3.tar.gz/download)
        sh %(mkdir -p $VOLATILE_DIR/snmpd)
        sh %(mkdir -p #{snmpd_rootdir})
        sh %(tar zxf $VOLATILE_DIR/snmpd.tar.gz\
             -C $VOLATILE_DIR/snmpd --strip-components=1)
        sh %(cd $VOLATILE_DIR/snmpd\
             && yes '' | ./configure --disable-embedded-perl --without-perl-modules --prefix=#{snmpd_rootdir}\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      sh %(#{snmpd_rootdir}/sbin/snmpd -Ln\
          -c $TRAVIS_BUILD_DIR/ci/resources/snmpd/snmpd.conf\
          -x TCP:11111 UDP:11111\
          -p $VOLATILE_DIR/snmpd.pid)
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'snmpd'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/snmpd.pid`)
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
