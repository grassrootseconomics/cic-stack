#!/bin/bash
set -euo pipefail

# db migration
sh ./db.sh

# /usr/local/bin/node /usr/local/bin/cic-meta-server $@
# ./node_modules/ts-node/dist/bin.js", "./scripts/server/server.ts $@
npm run start "$@"
