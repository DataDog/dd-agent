# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def mongo_version
  ENV['FLAVOR_VERSION'] || '3.0.1'
end

def mongo_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/mongo_#{mongo_version}"
end

namespace :ci do
  namespace :mongo do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless Dir.exist? File.expand_path(mongo_rootdir)
        # Downloads
        # https://fastdl.mongodb.org/linux/mongodb-#{target}-x86_64-#{mongo_version}.tgz
        target = if `uname`.strip == 'Darwin'
                   'osx'
                 else
                   'linux'
                 end
        sh %(curl -s -L\
             -o $VOLATILE_DIR/mongodb-#{target}-x86_64-#{mongo_version}.tgz\
             https://s3.amazonaws.com/dd-agent-tarball-mirror/mongodb-#{target}-x86_64-#{mongo_version}.tgz)
        sh %(mkdir -p #{mongo_rootdir})
        sh %(tar zxf $VOLATILE_DIR/mongodb-#{target}-x86_64-#{mongo_version}.tgz\
             -C #{mongo_rootdir} --strip-components=1)
      end
    end

    task before_script: ['ci:common:before_script'] do
      sh %(mkdir -p $VOLATILE_DIR/mongod1)
      sh %(mkdir -p $VOLATILE_DIR/mongod2)
      hostname = `hostname`.strip
      sh %(#{mongo_rootdir}/bin/mongod --port 37017\
           --pidfilepath $VOLATILE_DIR/mongod1/mongo.pid\
           --dbpath $VOLATILE_DIR/mongod1\
           --replSet rs0/#{hostname}:37018\
           --logpath $VOLATILE_DIR/mongod1/mongo.log\
           --noprealloc --rest --fork)
      sh %(#{mongo_rootdir}/bin/mongod --port 37018\
          --pidfilepath $VOLATILE_DIR/mongod2/mongo.pid\
          --dbpath $VOLATILE_DIR/mongod2\
          --replSet rs0/#{hostname}:37017\
          --logpath $VOLATILE_DIR/mongod2/mongo.log\
          --noprealloc --rest --fork)

      # Set up the replica set + print some debug info
      Wait.for 37_017, 10
      Wait.for 37_018
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(db.serverStatus())" 'localhost:37017'\
           >> $VOLATILE_DIR/mongo.log)
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(db.serverStatus())" 'localhost:37018'\
           >> $VOLATILE_DIR/mongo.log)
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(rs.initiate()); printjson(rs.conf());" 'localhost:37017'\
           \>> $VOLATILE_DIR/mongo.log)
      sleep_for 30
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(rs.config()); printjson(rs.status());" 'localhost:37017'\
           >> $VOLATILE_DIR/mongo.log)
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(rs.config()); printjson(rs.status());" 'localhost:37018'\
            >> $VOLATILE_DIR/mongo.log)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'mongo'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cache: ['ci:common:cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/mongod1/mongo.pid` `cat $VOLATILE_DIR/mongod2/mongo.pid`)
    end

    task :execute do
      exception = nil
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
