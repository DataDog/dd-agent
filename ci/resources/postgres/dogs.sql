CREATE TABLE breed (id SERIAL, name VARCHAR(255));
CREATE TABLE kennel (id SERIAL, address VARCHAR(255));
INSERT INTO kennel (address) VALUES ('Midtown, New York'), ('Boston');
SELECT * FROM kennel;
CREATE INDEX breed_names ON breed(name);
INSERT INTO breed (name) VALUES ('Labrador Retriver'), ('German Shepherd'), ('Yorkshire Terrier'), ('Golden Retriever'), ('Bulldog');
SELECT * FROM breed WHERE name = 'Labrador';
