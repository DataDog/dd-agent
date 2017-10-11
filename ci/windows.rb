# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

namespace :ci do
  namespace :windows do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install']

    task before_script: ['ci:common:before_script'] do
      # Set up an IIS website
      site_name = 'Test-Website-1'
      site_folder = File.join(ENV['INTEGRATIONS_DIR'], "iis_#{site_name}")
      sh %(powershell New-Item -ItemType Directory -Force #{site_folder})
      sh %(powershell Import-Module WebAdministration)
      # Create the new website
      sh %(powershell New-Website -Name #{site_name} -Port 8080 -PhysicalPath #{site_folder})
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'windows'
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
