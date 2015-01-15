require './ci/common'

# TODO: make this available in the matrix
def mongo_version
  '2.6.6'
end

def mongo_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/mongo_#{mongo_version}"
end

namespace :ci do
  namespace :mongo do |flavor|
    task :before_install => ['ci:common:before_install']

    task :install => ['ci:common:install'] do
      unless Dir.exist? File.expand_path(mongo_rootdir)
        sh %(curl -s -L\
             -o $VOLATILE_DIR/mongodb-linux-x86_64-2.6.6.tgz\
             https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-2.6.6.tgz)
        sh %(mkdir -p #{mongo_rootdir})
        sh %(tar zxf $VOLATILE_DIR/mongodb-linux-x86_64-2.6.6.tgz\
             -C #{mongo_rootdir} --strip-components=1)
      end
    end

    task :before_script => ['ci:common:before_script'] do
      sh %(mkdir -p $VOLATILE_DIR/mongod1)
      sh %(mkdir -p $VOLATILE_DIR/mongod2)
      hostname = `hostname`.strip
      sh %(#{mongo_rootdir}/bin/mongod --port 37017\
           --dbpath $VOLATILE_DIR/mongod1\
           --replSet rs0/#{hostname}:37018\
           --logpath $VOLATILE_DIR/mongod1/mongo.log\
           --noprealloc --rest --fork)
      sh %(#{mongo_rootdir}/bin/mongod --port 37018\
          --dbpath $VOLATILE_DIR/mongod2\
          --replSet rs0/#{hostname}:37017\
          --logpath $VOLATILE_DIR/mongod2/mongo.log\
          --noprealloc --rest --fork)

      # Set up the replica set + print some debug info
      sleep_for 15
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

    task :script => ['ci:common:script'] do
      this_provides = [
        'mongo'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task :cleanup => ['ci:common:cleanup']
    # FIXME: stop both mongos

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
