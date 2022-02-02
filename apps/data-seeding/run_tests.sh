#!/bin/bash

set -a
set -e
set -x
default_pythonpath=$PYTHONPATH:.
export PYTHONPATH=${default_pythonpath:-.}
>&2 echo using pythonpath $PYTHONPATH
for f in `ls tests/*.py`; do
	python $f
done
set +x
set +e
set +a
