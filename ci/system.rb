# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

# This is "less" important to change the version
# because it is shipped with the self-contained agent
def sysstat_version
  '11.0.1'
end

def system_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/system_#{sysstat_version}"
end

namespace :ci do
  namespace :system do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(system_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/system-#{sysstat_version}.tar.xz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/sysstat-11.0.1.tar.xz)
        sh %(mkdir -p $VOLATILE_DIR/system)
        sh %(mkdir -p #{system_rootdir})
        sh %(mkdir -p #{system_rootdir}/var/log/sa)
        sh %(tar Jxf $VOLATILE_DIR/system-#{sysstat_version}.tar.xz\
             -C $VOLATILE_DIR/system --strip-components=1)
        sh %(cd $VOLATILE_DIR/system\
             && conf_dir=#{system_rootdir}/etc/sysconfig sa_dir=#{system_rootdir}/var/log/sa\
                ./configure --prefix=#{system_rootdir} --disable-man-group\
             && make\
             && make install)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(mkdir -p $INTEGRATIONS_DIR/bin)
      sh %(rm -f $INTEGRATIONS_DIR/bin/mpstat)
      sh %(ln -s #{system_rootdir}/bin/mpstat $INTEGRATIONS_DIR/bin/mpstat)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'system'
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
