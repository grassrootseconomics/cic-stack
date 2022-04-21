#!/bin/bash

set -e
>&2 echo executing database migration
python scripts/migrate_cic_cache.py --migrations-dir /usr/local/share/cic-cache/alembic -vv
set +e
