CREATE TABLE tx (
	id SERIAL PRIMARY KEY,
	date_registered TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	block_number INTEGER NOT NULL,
	tx_index INTEGER NOT NULL,
	tx_hash VARCHAR(66) NOT NULL,
	sender VARCHAR(42) NOT NULL, 
	recipient VARCHAR(42) NOT NULL, 
	source_token VARCHAR(42) NOT NULL,
	destination_token VARCHAR(42) NOT NULL,
	from_value BIGINT NOT NULL,
	to_value BIGINT NOT NULL,
	success BOOLEAN NOT NULL, 
	date_block TIMESTAMP NOT NULL
);

CREATE TABLE tx_sync (
	id SERIAL PRIMARY KEY,
	tx VARCHAR(66) NOT NULL
);

INSERT INTO tx_sync (tx) VALUES('0x0000000000000000000000000000000000000000000000000000000000000000');
