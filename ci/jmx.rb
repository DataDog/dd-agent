require './ci/common'

# WARNING, it's a bit sneaky, it actually depends on other java jobs to run
# the order matters for this one, probably a FIXME
namespace :ci do
  namespace :jmx do
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install']

    task :before_script => ['ci:common:before_script']

    task :script => ['ci:common:script'] do
      this_provides = [
        'jmx',
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
