# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def snmp_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/snmp"
end

namespace :ci do
  namespace :snmp do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      # Downloads
      # http://sourceforge.net/projects/net-snmp/files/net-snmp/5.7.3/net-snmp-5.7.3.tar.gz/download
      unless Dir.exist? File.expand_path(snmp_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/snmp.tar.gz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/net-snmp-5.7.3.tar.gz)
        sh %(mkdir -p $VOLATILE_DIR/snmp)
        sh %(mkdir -p #{snmp_rootdir})
        sh %(tar zxf $VOLATILE_DIR/snmp.tar.gz\
             -C $VOLATILE_DIR/snmp --strip-components=1)
        sh %(cd $VOLATILE_DIR/snmp\
             && yes '' | ./configure --disable-embedded-perl --without-perl-modules --prefix=#{snmp_rootdir}\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(#{snmp_rootdir}/sbin/snmpd -Ln\
          -c $TRAVIS_BUILD_DIR/ci/resources/snmp/snmpd.conf\
          -x TCP:11111 UDP:11111\
          -p $VOLATILE_DIR/snmpd.pid)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'snmp'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/snmpd.pid`)
    end

    task :execute do
      Rake::Task['ci:common:execute'].invoke(flavor)
    end
  end
end
