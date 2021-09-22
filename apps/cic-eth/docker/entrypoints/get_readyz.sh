#! /bin/bash

set -e
set -u

echo "fetching migration variables from $CONTRACT_MIGRATION_URL"
for s in $(curl -s "$CONTRACT_MIGRATION_URL/readyz" | jq -r "to_entries|map(\"\(.key)=\(.value|tostring)\")|.[]" ); do
    echo "exporting $s"
    export $s
done
