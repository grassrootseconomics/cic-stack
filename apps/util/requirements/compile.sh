#!/bin/bash

which pyreq-merge &> /dev/null
if [ $? -gt 0 ]; then
	>&2 echo pyreq-merge missing, please install requirements
	exit 1
fi

in=$(mktemp)
out=$(mktemp)
>&2 echo using tmp $t
cat ../../requirements.txt > $out

repos=(../../cic-cache ../../cic-eth ../../cic-ussd ../../data-seeding ../../cic-notify)


for r in ${repos[@]}; do
	f="$r/requirements.txt"
	>&2 echo updating $f
	pyreq-merge $f $out -vv > $in
	cp $in $out

	f="$r/test_requirements.txt"
	if [ -f $f ]; then
		>&2 echo updating $f
		pyreq-merge $f $out -vv > $in
		cp $in $out
	fi
done
cp -v $out compiled_requirements.txt

outd=$(mktemp -d)
for r in ${repos[@]}; do
	f="$r/requirements.txt"
	b=$(basename $f)
	d=$(basename $r)
	echo output to $outd/$d/$b
	mkdir -vp $outd/$d
	pyreq-update -v $f compiled_requirements.txt > $outd/$d/$b
done
