#!/bin/bash

which pyreq-merge &> /dev/null
if [ $? -gt 0 ]; then
	>&2 echo pyreq-merge missing, please install requirements
	exit 1
fi

t=$(mktemp)
>&2 echo using tmp $t

repos=(../../cic-cache ../../cic-eth ../../cic-ussd ../../data-seeding ../../cic-notify ../../contract-migration)

for r in ${repos[@]}; do
	f="$r/requirements.txt"
	>&2 echo updating $f
	pyreq-update $f base_requirement.txt > $t
	cp $t $f

	f="$r/test_requirements.txt"
	if [ -f $f ]; then
		>&2 echo updating $f
		pyreq-update $f base_requirement.txt > $t
		cp $t $f
	fi
done
