require './ci/common'

namespace :ci do
  namespace :fluentd do
    task :before_install => ['ci:common:before_install'] do
      sh %Q{curl -L http://toolbelt.treasuredata.com/sh/install-ubuntu-precise-td-agent2.sh | sudo sh}
    end

    task :install => ['ci:common:install']

    task :before_script => ['ci:common:before_script'] do
      sh %Q{sudo /etc/init.d/td-agent stop}
      sh %Q{sudo cp $TRAVIS_BUILD_DIR/tests/fluentd/td-agent.conf /etc/td-agent/td-agent.conf}
      sh %Q{sudo /etc/init.d/td-agent start}
      sleep_for(10)
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'fluentd',
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
