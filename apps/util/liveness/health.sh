#!/bin/bash

rundir=${CIC_RUNDIR:-/run}
unit=${CIC_UNIT:-$HOSTNAME}

read p < $rundir/$unit/pid

if [ -z $p ]; then
	>&2 echo unit $unit has no pid
	exit 1
fi

if [ ! -d /proc/$p ]; then
	>&2 echo unit $unit reports non-existent pid $p
	exit 1
fi	

>&2 echo unit $unit has pid $p

if [ ! -f $rundir/$unit/error ]; then
	>&2 echo unit $unit has unspecified state
	exit 1
fi

read e 2> /dev/null < $rundir/$unit/error 
if [ -z $e ]; then
	>&2 echo unit $unit has unspecified state
	exit 1
fi

>&2 echo unit $unit has error $e

if [ $e -gt 0 ]; then
	exit 1;
fi
