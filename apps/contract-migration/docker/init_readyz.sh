#! /bin/bash

set -e 
set -a

mkdir -p $DEV_DATA_DIR/health

source $DEV_DATA_DIR/env_reset

jq --arg CIC_REGISTRY_ADDRESS "$CIC_REGISTRY_ADDRESS" \
   --arg CIC_TRUST_ADDRESS "$CIC_TRUST_ADDRESS" \
   --arg CIC_DEFAULT_TOKEN_SYMBOL "$CIC_DEFAULT_TOKEN_SYMBOL"\
   --arg TOKEN_NAME "$TOKEN_NAME"\
   -n '{"CIC_REGISTRY_ADDRESS": $CIC_REGISTRY_ADDRESS, 
        "CIC_TRUST_ADDRESS": $CIC_TRUST_ADDRESS,
        "CIC_DEFAULT_TOKEN_SYMBOL": $CIC_DEFAULT_TOKEN_SYMBOL,
        "TOKEN_NAME": $TOKEN_NAME}' > $DEV_DATA_DIR/health/readyz

cd $DEV_DATA_DIR/health

echo "starting health endpoint on :8000/readyz"
python -m http.server 8000 &> /dev/null 

