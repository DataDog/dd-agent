require './ci/common'

namespace :ci do
  namespace :network do
    task :before_install => ['ci:common:before_install'] do
      apt_update
    end

    task :install => ['ci:common:install'] do
      # snmpd
      sh %Q{sudo apt-get install snmpd -qq}

      # ntpd
      sh %Q{sudo apt-get install ntp -qq}
    end

    task :before_script => ['ci:common:before_script'] do
      # snmpd
      sh %Q{sudo cp $TRAVIS_BUILD_DIR/tests/snmp/snmpd.conf /etc/snmp/snmpd.conf}
      sh %Q{sudo service snmpd restart}
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'ntpd',
        'snmpd'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
