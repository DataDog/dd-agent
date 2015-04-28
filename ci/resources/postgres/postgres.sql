CREATE USER datadog WITH PASSWORD 'datadog';
GRANT SELECT ON pg_stat_database TO datadog;
CREATE DATABASE datadog_test;
GRANT ALL PRIVILEGES ON DATABASE datadog_test TO datadog;
CREATE DATABASE dogs;
