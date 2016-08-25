# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

namespace :ci do
  namespace :my_new_flavor do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install']

    task before_script: ['ci:common:before_script']
    # If you need to wait on a start of a progran, please use Wait.for,
    # see https://github.com/DataDog/dd-agent/pull/1547

    task script: ['ci:common:script'] do
      this_provides = [
        'my_new_flavor'
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
