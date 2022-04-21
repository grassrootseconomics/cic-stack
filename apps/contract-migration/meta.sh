#!/bin/bash

set -e

key=$1
file=$2

if [ "$DEV_DEBUG_LEVEL" -eq 1 ]; then
	curl_debug_flag="-v"
elif [ "$DEV_DEBUG_LEVEL" -gt 1 ]; then
	curl_debug_flag="-vv"
fi

t=`mktemp -d`

# Since a python tool for posting automerge items is still missing, we need to make use of the cic-meta server's capability to generate the change graph and provide a digest to sign.
f_size=`stat -c %s $file`
curl --show-error -f $curl_debug_flag -s -X POST $META_URL/$ptr -H "Content-Length: $f_size" -H "Content-Type: application/json" -H "X-CIC-AUTOMERGE: server" --data-binary @$file > $t/req.json

# Extract the digest
`jq -j .digest < $t/req.json > $t/digest`

# Sign the digest
mkdir -p $t/.gnupg
chmod 700 $t/.gnupg -R
gpg -q --homedir $t/.gnupg --pinentry-mode loopback --passphrase $PGP_PASSPHRASE --import $PGP_PRIVATEKEY_FILE
gpg -q --homedir $t/.gnupg --pinentry-mode loopback --passphrase $PGP_PASSPHRASE -u $PGP_FINGERPRINT -a -b $t/digest

# Assemble the signed update request for cic-meta
d_raw=`cat $t/req.json`
d_sig=`cat $t/digest.asc | tr '\n' '\t' | sed -e 's/\t/\\\\n/g'`
d_digest=`cat $t/digest`

cat <<EOF > $t/req2.json
{
	"s": {
		"engine": "pgp",
		"algo": 969,
		"data": "$d_sig",
		"digest": "$d_digest"
	}
}
EOF
< $t/req2.json jq --arg m "$d_raw" '. + { m: $m }' > $t/req3.json
f_size=`stat -c %s $t/req3.json`

# Send the update request
curl --show-error -f  $curl_debug_flag -s -X PUT $META_URL/$ptr -H "Content-Length: $f_size" -H "Content-Type: application/json" -H "X-CIC-AUTOMERGE: server" --data-binary @$t/req3.json

# Clean up
rm -rf $t

set +e
