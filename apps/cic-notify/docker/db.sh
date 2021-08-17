#!/bin/bash
set -e
python scripts/migrate.py -c /usr/local/etc/cic-notify --migrations-dir /usr/local/share/cic-notify/alembic -vv
