#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname cic_meta <<-EOSQL
    create table if not exists cic_meta.store (
        id serial primary key not null,
        owner_fingerprint text not null,
        hash char(64) not null unique,
        content text not null
    );

    create index if not exists idx_fp on store ((lower(owner_fingerprint)));
EOSQL


