#! /bin/bash

set -e 
set -a

mkdir -p $DEV_DATA_DIR/health

source $DEV_DATA_DIR/env_reset

jq --arg CIC_REGISTRY_ADDRESS "$CIC_REGISTRY_ADDRESS" \
   --arg CIC_TRUST_ADDRESS "$CIC_TRUST_ADDRESS" \
   --arg RUN_MASK "$RUN_MASK" \
   -n '{"CIC_REGISTRY_ADDRESS": $CIC_REGISTRY_ADDRESS, "CIC_TRUST_ADDRESS": $CIC_TRUST_ADDRESS, "RUN_MASK": $RUN_MASK}' > $DEV_DATA_DIR/health/readyz

cd $DEV_DATA_DIR/health

echo "starting health endpoint on :8000/readyz"
python -m http.server 8000 &> /dev/null 

