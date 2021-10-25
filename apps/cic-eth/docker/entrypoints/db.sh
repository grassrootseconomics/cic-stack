#!/bin/bash

set -e
>&2 echo executing database migration
#python scripts/migrate.py -c /usr/local/etc/cic-eth --migrations-dir /usr/local/share/cic-eth/alembic -vv
python scripts/migrate.py --migrations-dir /usr/local/share/cic-eth/alembic -vv
set +e
