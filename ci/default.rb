require './ci/common'

namespace :ci do
  namespace :default do
    task :before_install => ['ci:common:before_install'] do
      apt_update
    end

    task :install => ['ci:common:install'] do
      sh %Q{sudo apt-get install sysstat -qq}
    end

    task :before_script => ['ci:common:before_script']

    task :script => ['ci:common:script'] do
      sh "find . -name '*.py' | xargs --max-procs=0 -n 1 pylint --rcfile=./.pylintrc"
      Rake::Task['ci:common:run_tests'].invoke('default')
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
