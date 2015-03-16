require './ci/common'

def apache_version
  ENV['APACHE_VERSION'] || '2.4.10'
end

def apache_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/apache_#{apache_version}"
end

namespace :ci do
  namespace :apache do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(apache_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/httpd-#{apache_version}.tar.bz2\
             http://mirror.cc.columbia.edu/pub/software/apache/httpd/httpd-#{apache_version}.tar.bz2)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/apr.tar.bz2\
             http://mirror.cc.columbia.edu/pub/software/apache/apr/apr-1.5.1.tar.bz2)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/apr-util.tar.bz2\
             http://mirror.cc.columbia.edu/pub/software/apache/apr/apr-util-1.5.4.tar.bz2)
        sh %(mkdir -p #{apache_rootdir})
        sh %(mkdir -p $VOLATILE_DIR/apache)
        sh %(tar jxf $VOLATILE_DIR/httpd-#{apache_version}.tar.bz2\
             -C $VOLATILE_DIR/apache --strip-components=1)
        sh %(mkdir -p $VOLATILE_DIR/apache/srclib/apr)
        sh %(mkdir -p $VOLATILE_DIR/apache/srclib/apr-util)
        sh %(tar jxf $VOLATILE_DIR/apr.tar.bz2\
             -C $VOLATILE_DIR/apache/srclib/apr --strip-components=1)
        sh %(tar jxf $VOLATILE_DIR/apr-util.tar.bz2\
             -C $VOLATILE_DIR/apache/srclib/apr-util --strip-components=1)
        sh %(cd $VOLATILE_DIR/apache\
             && ./configure --prefix=#{apache_rootdir}\
             && make -j $CONCURRENCY\
             && make install)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      sh %(cp $TRAVIS_BUILD_DIR/ci/resources/apache/httpd.conf\
              #{apache_rootdir}/conf/httpd.conf)
      sh %(sed -i -e 's@%APACHE_ROOTDIR%@#{apache_rootdir}@'\
            #{apache_rootdir}/conf/httpd.conf)
      sh %(sed -i -e "s@%VOLATILE_DIR%@$VOLATILE_DIR@"\
            #{apache_rootdir}/conf/httpd.conf)
      sh %(#{apache_rootdir}/bin/apachectl start)
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'apache'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup'] do
      sh %(#{apache_rootdir}/bin/apachectl stop)
    end

    task :execute do
      exception = nil
      begin
        %w(before_install install before_script script).each do |t|
          Rake::Task["#{flavor.scope.path}:#{t}"].invoke
        end
      rescue => e
        exception = e
        puts "Failed task: #{e.class} #{e.message}".red
      end
      if ENV['SKIP_CLEANUP']
        puts 'Skipping cleanup, disposable environments are great'.yellow
      else
        puts 'Cleaning up'
        Rake::Task["#{flavor.scope.path}:cleanup"].invoke
      end
      fail exception if exception
    end
  end
end
