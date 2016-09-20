# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

namespace :ci do
  namespace :default do |flavor|
    task before_install: ['ci:common:before_install']

    task :coverage do
      ci_dir = File.dirname(__FILE__)
      checks_dir = File.join(ci_dir, '..', 'checks.d')
      tests_checks_dir = File.join(ci_dir, '..', 'tests', 'checks')
      mock_dir = File.join(tests_checks_dir, 'mock')
      integration_dir = File.join(tests_checks_dir, 'integration')
      untested = []
      mocked = []
      perfects = []
      Dir.glob(File.join(checks_dir, '*.py')).each do |check|
        check_name = /((\w|_)+).py$/.match(check)[1]
        if File.exist?(File.join(integration_dir, "test_#{check_name}.py"))
          perfects.push(check_name)
        elsif File.exist?(File.join(mock_dir, "test_#{check_name}.py"))
          mocked.push(check_name)
        else
          untested.push(check_name)
        end
      end
      total_checks = (untested + mocked + perfects).length
      unless untested.empty?
        puts "Untested checks (#{untested.length}/#{total_checks})".red
        puts '-----------------------'.red
        untested.each { |check_name| puts check_name.red }
        puts ''
      end
      unless mocked.empty?
        puts "Mocked tests (#{mocked.length}/#{total_checks})".yellow
        puts '--------------------'.yellow
        mocked.each { |check_name| puts check_name.yellow }
      end
    end

    task install: ['ci:common:install']

    task before_script: ['ci:common:before_script']

    task lint: ['rubocop'] do
      if ENV['SKIP_LINT']
        puts 'Skipping lint'.yellow
      else
        sh %(echo "PWD IS")
        sh %(pwd)
        sh %(flake8)
        sh %(find . -name '*.py' -not\
               \\( -path '*.cache*' -or -path '*embedded*' -or -path '*venv*' -or -path '*.git*' -or -path \
               '*.ropeproject*' \\) | xargs -n 100 -P 8 pylint --rcfile=./.pylintrc)
      end
    end

    task script: ['ci:common:script', :coverage, :lint] do
      Rake::Task['ci:common:run_tests'].invoke(['default'])
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup']

    task :execute do
      Rake::Task['ci:common:execute'].invoke(flavor)
    end
  end
end
