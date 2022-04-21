create table if not exists store (
	id serial primary key not null,
	owner_fingerprint text default null,
	hash char(64) not null unique,
	content text not null,
	mime_type text
);

create index if not exists idx_fp on store ((lower(owner_fingerprint)));
