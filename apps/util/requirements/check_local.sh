#!/bin/bash

MODULE_ROOT='../..'
repos=($MODULE_ROOT/cic-cache $MODULE_ROOT/cic-eth $MODULE_ROOT/cic-ussd $MODULE_ROOT/cic-notify)

sumd=$(realpath ./local_package_sums)
mkdir -vp $sumd

for r in ${repos[@]}; do
	b=$(basename $r)
	pushd $r
	rm -v dist/*
	python setup.py sdist
	f=`ls dist/`
	cp -v dist/$f $sumd/$b.tar.gz
	pushd $sumd
	if [ -f $b.sha256sum ]; then
		echo "sha256sum -c $b.sha256sum"
		sha256sum $b.tar.gz
		cat $b.sha256sum
		sha256sum -c $b.sha256sum
		if [ $? -gt 0 ]; then
			>&2 echo "sum mismatch for $f"
			sha256sum $b.whl > $b.sha256sum
		else
			>&2 echo "sum match (no change) for $f"
		fi
	else
		sha256sum $b.tar.gz > $b.sha256sum
	fi
	popd
	popd
done
