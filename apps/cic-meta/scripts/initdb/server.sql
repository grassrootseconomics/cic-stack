create table if not exists store (
	/*id serial primary key not null,*/
	id integer primary key autoincrement,
	owner_fingerprint text not null,
	hash char(64) not null unique,
	content text not null
);

create index if not exists idx_fp on store ((lower(owner_fingerprint)));
