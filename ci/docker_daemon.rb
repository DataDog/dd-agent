# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

namespace :ci do
  namespace :docker_daemon do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install']

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'docker_daemon'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup']

    task :execute do
      Rake::Task['ci:common:execute'].invoke(flavor)
    end
  end
end
