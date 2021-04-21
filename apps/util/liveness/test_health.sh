#!/bin/bash

export CIC_RUNDIR=`realpath ./tests/testdata/run`
t=`mktemp -d -p $CIC_RUNDIR`
export CIC_UNIT=`basename $t`

>&2 echo test pid $$
echo $$ > $t/pid
echo 0 > $t/error

. health.sh

echo 1 > $t/error
#unlink $t/error
. health.sh

echo if error this is not printed
