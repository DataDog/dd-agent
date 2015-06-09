circle_flavors = ['docker']

namespace :ci do
  namespace :circleci do
    task :install do |t|
      circle_flavors do |flavor|
        puts
        Rake::Task["ci:#{flavor}:before_install"].reenable
        Rake::Task["ci:#{flavor}:before_install"].invoke
        Rake::Task["ci:#{flavor}:install"].reenable
        Rake::Task["ci:#{flavor}:install"].invoke
      end
      t.reenable
    end

    task :run do |t|
      circle_flavors.each() do |flavor|
        Rake::Task["ci:#{flavor}:execute"].invoke
      end
      t.reenable
    end
  end
end
