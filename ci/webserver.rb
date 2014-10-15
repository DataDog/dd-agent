require './ci/common'

namespace :ci do
  namespace :webserver do
    task :before_install => ['ci:common:before_install'] do
      apt_update
    end

    task :install => ['ci:common:install'] do
      # apache
      sh %Q{sudo apt-get install apache2}
      # haproxy
      sh %Q{sudo apt-get install haproxy}
      # lighttpd
      sh %Q{sudo apt-get install lighttpd}
      # nginx
      sh %Q{sudo apt-get install nginx}
    end

    task :before_script => ['ci:common:before_script'] do
      # apache
      sh %Q{sudo service apache2 stop}
      sh %Q{sudo cp $TRAVIS_BUILD_DIR/tests/apache/ports.conf /etc/apache2/ports.conf}
      sh %Q{sudo cp $TRAVIS_BUILD_DIR/tests/apache/apache.conf /etc/apache2/apache.conf}
      sh %Q{sudo service apache2 start}
      # haproxy - we launch it manually
      sh %Q{sudo service haproxy stop}
      # lighttpd
      sh %Q{sudo service lighttpd stop}
      sh %Q{sudo cp $TRAVIS_BUILD_DIR/tests/lighttpd/lighttpd.conf /etc/lighttpd/lighttpd.conf}
      sh %Q{sudo service lighttpd start}
      # nginx
      sh %Q{sudo service nginx stop}
      sh %Q{sudo cp $TRAVIS_BUILD_DIR/tests/nginx.conf /etc/nginx/conf.d/default.conf}
      sh %Q{sudo service nginx start}
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'apache',
        'haproxy',
        'lighttpd',
        'nginx',
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
