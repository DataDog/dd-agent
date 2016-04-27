# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def riak_version
  ENV['COUCHDB_VERSION'] || '2.0.5'
end

def riak_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/riak_#{riak_version}"
end

namespace :ci do
  namespace :riak do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(riak_rootdir)
        sh %(curl -o $VOLATILE_DIR/kerl https://raw.githubusercontent.com/spawngrid/kerl/master/kerl)
        sh %(chmod a+x $VOLATILE_DIR/kerl)
        sh %($VOLATILE_DIR/kerl build git git://github.com/basho/otp.git OTP_R16B02 R16B02)
        sh %($VOLATILE_DIR/kerl install R16B02 $VOLATILE_DIR/erlang/R16B02)
        sh %(curl -o $VOLATILE_DIR/riak.tar.gz\
             http://s3.amazonaws.com/downloads.basho.com/riak/#{riak_version[0..2]}/#{riak_version}/riak-#{riak_version}.tar.gz)
        sh %(mkdir -p $VOLATILE_DIR/riak)
        sh %(tar zxvf $VOLATILE_DIR/riak.tar.gz  -C $VOLATILE_DIR/riak --strip-components=1)
        sh %(cd $VOLATILE_DIR/riak\
             && PATH=$PATH:$VOLATILE_DIR/erlang/R16B02/bin make all\
             && PATH=$PATH:$VOLATILE_DIR/erlang/R16B02/bin make devrel DEVNODES=2)
        sh %(mv $VOLATILE_DIR/riak/dev #{riak_rootdir})
      end
    end

    task before_script: ['ci:common:before_script'] do
      %w(dev1 dev2).each do |dev|
        sh %(#{riak_rootdir}/#{dev}/bin/riak start)
      end
      # When cached, dev2 is already a member of the cluster
      sh %(#{riak_rootdir}/dev2/bin/riak-admin cluster join dev1@127.0.0.1 || true)
      sh %(#{riak_rootdir}/dev2/bin/riak-admin cluster plan)
      sh %(#{riak_rootdir}/dev2/bin/riak-admin cluster commit)
      10.times do
        sh %(curl -s -XPUT http://localhost:10018/buckets/welcome/keys/german\
             -H 'Content-Type: text/plain'\
             -d 'herzlich willkommen')
        sh %(curl -s http://localhost:10018/buckets/welcome/keys/german)
      end
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'riak'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache'] do
      Rake::Task['ci:riak:cleanup'].invoke
    end

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      %w(dev1 dev2).each do |dev|
        sh %(#{riak_rootdir}/#{dev}/bin/riak stop)
        sh %(rm -rf #{riak_rootdir}/#{dev}/data)
      end
    end

    task :execute do
      exception = nil
      # Compilation takes too long on Travis
      if ENV['TRAVIS']
        puts "Riak tests won't run, compilation takes too long on Travis"
      else
        begin
          %w(before_install install before_script
             script before_cache cache).each do |t|
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
        raise exception if exception
      end
    end
  end
end
