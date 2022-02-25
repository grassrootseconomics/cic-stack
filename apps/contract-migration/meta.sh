#!/bin/bash

set -e

key=$1
file=$2

t=`mktemp -d`

# Since a python tool for posting automerge items is still missing, we need to make use of the cic-meta server's capability to generate the change graph and provide a digest to sign.
curl -s -X POST $META_URL/$ptr -H "Content-Type: application/json" -H "X-CIC-AUTOMERGE: server" --data-binary @$file > $t/req.json

# Extract the digest
`jq -j .digest < $t/req.json > $t/digest`

# Sign the digest
mkdir -p $t/.gnupg
chmod 700 $t/.gnupg -R
gpg -q --homedir $t/.gnupg --pinentry-mode loopback --passphrase merman --import pgp/merman.priv.asc
gpg -q --homedir $t/.gnupg --pinentry-mode loopback --passphrase merman -u F3FAF668E82EF5124D5187BAEF26F4682343F692 -a -b $t/digest

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

# Send the update request
curl -s -X PUT $META_URL/$ptr -H "Content-Type: application/json" -H "X-CIC-AUTOMERGE: server" --data @$t/req3.json

# Clean up
rm -rf $t

set +e
