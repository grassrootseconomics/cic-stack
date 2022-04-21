#!/bin/bash
set -e
python scripts/migrate.py -c /usr/src/cic_notify/data/config --migrations-dir /usr/local/share/cic-notify/alembic -vv
