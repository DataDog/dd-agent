# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
require './ci/common'

def kafka_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

namespace :ci do
  namespace :kafka do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('kafka')
      sh %(EXTERNAL_PORT=9092 EXTERNAL_JMX_PORT=9999 docker-compose -f \
           #{ENV['TRAVIS_BUILD_DIR']}/tests/kafka/resources/docker-compose-single-broker.yml up -d)
      Wait.for 2181
      Wait.for 9092
      wait_on_docker_logs('resources_kafka_1', 5, '[Kafka Server 1001], started')
      wait_on_docker_logs('resources_zookeeper_1', 5, 'NodeExists for /brokers/ids')
      sh %(EXTERNAL_PORT=9091 EXTERNAL_JMX_PORT=9998 docker-compose -f \
           #{ENV['TRAVIS_BUILD_DIR']}/tests/kafka/resources/docker-compose-single-broker.yml scale kafka=2)
      wait_on_docker_logs('resources_kafka_2', 5, '[Kafka Server 1002], started')
      sh %(docker run -d --name kafka_consumer -v /var/run/docker.sock:/var/run/docker.sock -e HOST_IP=172.17.0.1 \
           -e ZK=172.17.0.1:2181 -e JMX_PORT=9999 -p 7777:9999 -i -t wurstmeister/kafka:#{kafka_version} /bin/bash -c \
           '$KAFKA_HOME/bin/kafka-console-consumer.sh --topic=test --zookeeper=$ZK --consumer-property group.id=my_consumer ')
      wait_on_docker_logs('resources_kafka_1', 30, 'Created topic "test"')
      sh %(docker run -d --name kafka_producer -v /var/run/docker.sock:/var/run/docker.sock -e HOST_IP=172.17.0.1 \
           -e ZK=172.17.0.1:2181 -e JMX_PORT=9999 -p 7778:9999 -i -t wurstmeister/kafka:#{kafka_version} /bin/bash -c \
           '$KAFKA_HOME/bin/kafka-topics.sh --create --topic test --partitions 4 --zookeeper $ZK --replication-factor 2 ; \
           while true; do $KAFKA_HOME/bin/kafka-console-producer.sh --topic=test --broker-list=`broker-list.sh` <<< "boomshakalaka" ; \
           sleep 1 ; done')
    end

    task before_script: ['ci:common:before_script'] do
      wait_on_docker_logs('kafka_consumer', 25, 'boomshakalaka')
      wait_on_docker_logs('resources_zookeeper_1', 90, 'Error Path:/consumers/my_consumer/offsets')
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'kafka'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker rm -f kafka_consumer)
      sh %(docker rm -f kafka_producer)
      sh %(EXTERNAL_PORT=9092 EXTERNAL_JMX_PORT=9999 docker-compose -f \
           #{ENV['TRAVIS_BUILD_DIR']}/tests/kafka/resources/docker-compose-single-broker.yml stop)
      sh %(EXTERNAL_PORT=9092 EXTERNAL_JMX_PORT=9999 docker-compose -f \
           #{ENV['TRAVIS_BUILD_DIR']}/tests/kafka/resources/docker-compose-single-broker.yml rm -f)
    end

    task :execute do
      exception = nil
      begin
        %w[before_install install before_script].each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        if !ENV['SKIP_TEST']
          Rake::Task["#{flavor.scope.path}:script"].invoke
        else
          puts 'Skipping tests'.yellow
        end
        Rake::Task["#{flavor.scope.path}:before_cache"].invoke
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
