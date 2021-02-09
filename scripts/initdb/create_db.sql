CREATE USER grassroots WITH PASSWORD 'tralala' CREATEDB;
CREATE DATABASE "cic_cache";
CREATE DATABASE "cic_eth";
CREATE DATABASE "cic_notify";
CREATE DATABASE "cic_meta";
CREATE DATABASE "cic_signer";
CREATE DATABASE "cic_ussd";
GRANT ALL PRIVILEGES 
ON DATABASE "cic_cache", "cic_eth", "cic_notify", "cic_meta", "cic_signer", "cic_ussd"
TO grassroots;
