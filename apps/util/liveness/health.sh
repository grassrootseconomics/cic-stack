#!/bin/bash

rundir=${CIC_RUNDIR:-/run}

read p < $rundir/$CIC_UNIT/pid

if [ -z $p ]; then
	>&2 echo unit $CIC_UNIT has no pid
	exit 1
fi

if [ ! -d /proc/$p ]; then
	>&2 echo unit $CIC_UNIT reports non-existent pid $p
	exit 1
fi	

>&2 echo unit $CIC_UNIT has pid $p

if [ ! -f $rundir/$CIC_UNIT/error ]; then
	>&2 echo unit $CIC_UNIT has unspecified state
	exit 1
fi

read e 2> /dev/null < $rundir/$CIC_UNIT/error 
if [ -z $e ]; then
	>&2 echo unit $CIC_UNIT has unspecified state
	exit 1
fi

>&2 echo unit $CIC_UNIT has error $e

if [ $e -gt 0 ]; then
	exit 1;
fi
