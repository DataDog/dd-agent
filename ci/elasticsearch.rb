require './ci/common'

namespace :ci do
  namespace :elasticsearch do
    task :before_install => ['ci:common:before_install'] do
      # already installed on Travis
      sh %Q{sudo service elasticsearch restart}
    end

    task :install => ['ci:common:install']

    task :before_script => ['ci:common:before_script']

    task :script => ['ci:common:script'] do
      this_provides = [
        'elasticsearch',
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
