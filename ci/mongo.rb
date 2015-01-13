require './ci/common'

namespace :ci do
  namespace :mongo do
    task :before_install => ['ci:common:before_install'] do
      sh %Q{sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10}
      sh %Q{echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list}
      apt_update
    end

    task :install => ['ci:common:install'] do
      # TODO: make this configurable through the matrix
      sh %Q{sudo apt-get install -qq mongodb-org=2.6.5}
    end

    task :before_script => ['ci:common:before_script'] do
      # Don't use the version of mongo shipped on the box
      sh %Q{sudo service mongod stop}

      sh %Q{sudo mkdir -p /data/mongod1}
      sh %Q{sudo mkdir -p /data/mongod2}
      hostname = `hostname`.strip
      sh %Q{sudo mongod --port 37017 --dbpath /data/mongod1 --replSet rs0/#{hostname}:37018 --logpath /data/mongod1/mongo.log --noprealloc --rest --fork}
      sh %Q{sudo mongod --port 37018 --dbpath /data/mongod2 --replSet rs0/#{hostname}:37017 --logpath /data/mongod2/mongo.log --noprealloc --rest --fork}

      # Set up the replica set + print some debug info
      sleep_for(15)
      # FIXME: cannot use this commands on travis because they seem to
      # make mongo enter in a sort of lock forever stalling the build
      # sh %Q{sudo mongo --eval "printjson(db.serverStatus())" 'localhost:37017' >> /tmp/mongo.log}
      # sh %Q{sudo mongo --eval "printjson(db.serverStatus())" 'localhost:37018' >> /tmp/mongo.log}
      sh %Q{sudo mongo --eval "printjson(rs.initiate()); printjson(rs.conf());" 'localhost:37017' >> /tmp/mongo.log}
      sleep_for(30)
      sh %Q{sudo mongo --verbose --eval "printjson(rs.config()); printjson(rs.status());" 'localhost:37017' >> /tmp/mongo.log}
      sh %Q{sudo mongo --verbose --eval "printjson(rs.config()); printjson(rs.status());" 'localhost:37018' >> /tmp/mongo.log}
    end

    task :script => ['ci:common:script'] do
      this_provides = [
        'mongo',
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :execute => [:before_install, :install, :before_script, :script]
  end
end
