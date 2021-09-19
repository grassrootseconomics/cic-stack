#!/bin/bash

while read l; do
	e=${!l}
	if [ ! -z $e ]; then
		>&2 echo "saving env var $l = $e"
		echo "$l=$e"
	fi
done
