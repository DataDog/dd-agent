require './ci/common'

# This is "less" important to change the version
# because it is shipped with the self-contained agent
def sysstat_version
  '11.0.1'
end

def sysstat_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/sysstat_#{sysstat_version}"
end

namespace :ci do
  namespace :sysstat do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(sysstat_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/sysstat-#{sysstat_version}.tar.xz\
             http://perso.orange.fr/sebastien.godard/sysstat-11.0.1.tar.xz)
        sh %(mkdir -p $VOLATILE_DIR/sysstat)
        sh %(mkdir -p #{sysstat_rootdir})
        sh %(mkdir -p #{sysstat_rootdir}/var/log/sa)
        sh %(tar Jxf $VOLATILE_DIR/sysstat-#{sysstat_version}.tar.xz\
             -C $VOLATILE_DIR/sysstat --strip-components=1)
        sh %(cd $VOLATILE_DIR/sysstat\
             && conf_dir=#{sysstat_rootdir}/etc/sysconfig sa_dir=#{sysstat_rootdir}/var/log/sa ./configure --prefix=#{sysstat_rootdir} --disable-man-group\
             && make\
             && make install)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      # FIXME: probably not the cleanest way to go
      sh %(mkdir -p $INTEGRATIONS_DIR/bin)
      sh %(cp #{sysstat_rootdir}/bin/mpstat $INTEGRATIONS_DIR/bin)
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'sysstat'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup']

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
