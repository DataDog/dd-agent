require './ci/common'

namespace :ci do
  namespace :tomcat do
    task :before_install => ['ci:common:before_install'] do
      apt_update
    end

    task :install => ['ci:common:install'] do
      sh %Q{sudo apt-get install tomcat6 -qq}
      sh %Q{sudo apt-get install solr-tomcat -qq}
    end

    task :before_script => ['ci:common:before_script'] do
      sh %Q{sudo cp $TRAVIS_BUILD_DIR/tests/tomcat_cfg.xml /etc/tomcat6/server.xml}
      sh %Q{sudo cp $TRAVIS_BUILD_DIR/tests/tomcat6 /etc/default/tomcat6}
      sh %Q{sudo service tomcat6 restart}
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'solr',
        'tomcat'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
