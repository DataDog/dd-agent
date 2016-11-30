# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

require './ci/common'

def mongo_version
  # We test on '2.6.9' and 3.0.1
  ENV['FLAVOR_VERSION'] || '3.0.1'
end

def mongo_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/mongo_#{mongo_version}"
end

def mongo_bin
  "#{mongo_rootdir}/bin/mongod"
end

namespace :ci do
  namespace :mongo do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      unless File.exist? mongo_bin
        # cleanup dirty states
        sh %(rm -rf #{mongo_rootdir})
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
           --replSet 'rs0' --bind_ip 0.0.0.0 \
           --logpath $VOLATILE_DIR/mongod1/mongo.log\
           --noprealloc --rest --fork)
      sh %(#{mongo_rootdir}/bin/mongod --port 37018\
          --pidfilepath $VOLATILE_DIR/mongod2/mongo.pid\
          --dbpath $VOLATILE_DIR/mongod2\
          --replSet 'rs0' --bind_ip 0.0.0.0 \
          --logpath $VOLATILE_DIR/mongod2/mongo.log\
          --noprealloc --rest --fork)

      # Set up the replica set + print some debug info
      Wait.for 37_017, 10
      Wait.for 37_018
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(db.serverStatus())" 'localhost:37017' \
           >> $VOLATILE_DIR/mongo1.log)
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(db.serverStatus())" 'localhost:37018' \
           >> $VOLATILE_DIR/mongo2.log)
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(rs.initiate()); printjson(rs.conf());" '#{hostname}:37017' \
           >> $VOLATILE_DIR/mongo1.log)

      # mongo 2 takes longer to spin up than mongo 3. Without this wait,
      # it will all break because it takes too long to come up.
      sleep_for 30
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "cfg = rs.conf(); cfg.members[0].host = '#{hostname}:37017';\
           printjson(cfg); \
           rs.reconfig(cfg); printjson(rs.conf());" 'localhost:37017' \
           >> $VOLATILE_DIR/mongo1.log)
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(rs.add('#{hostname}:37018'));\
           printjson(rs.status());" 'localhost:37017' >> $VOLATILE_DIR/mongo1.log)

      sleep_for 30
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(rs.config()); printjson(rs.status());" 'localhost:37017' \
           >> $VOLATILE_DIR/mongo1.log)
      sh %(#{mongo_rootdir}/bin/mongo\
           --eval "printjson(rs.config()); printjson(rs.status());" 'localhost:37018' \
           >> $VOLATILE_DIR/mongo2.log)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'mongo'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/mongod1/mongo.pid`)
      sh %(kill `cat $VOLATILE_DIR/mongod2/mongo.pid`)
    end

    task :execute do
      Rake::Task['ci:common:execute'].invoke(flavor)
    end
  end
end
