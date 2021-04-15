#!/bin/bash

set -e
>&2 echo executing database migration
python scripts/migrate.py -c /usr/local/etc/cic-cache --migrations-dir /usr/local/share/cic-cache/alembic -vv
set +e
