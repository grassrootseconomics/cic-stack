#!/bin/bash

set -e
>&2 echo executing database migration
migrate.py -c /usr/local/etc/cic-eth --migrations-dir /usr/local/share/cic-eth/alembic -vv
set +e
