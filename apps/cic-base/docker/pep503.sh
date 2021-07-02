#!/usr/bin/env 

dest=`pwd`
d=$1
for df in `find $d -name "*.whl" -type f`; do
	f=`basename $df`
	pd=`echo $f | sed -e "s/^\(.*\)-[[:digit:]]*\.[[:digit:]].*$/\1/g" | tr "[:upper:]" "[:lower:]" | tr "_" "-"`
	mkdir -v $dest/$pd
	mv -v $df $dest/$pd/
done
for df in `find $d -name "*.tar.gz" -type f`; do
	f=`basename $df`
	pd=`echo $f | sed -e "s/^\(.*\)-[[:digit:]]*\.[[:digit:]].*$/\1/g" | tr "[:upper:]" "[:lower:]" | tr "_" "-"`
	mkdir -v $dest/$pd
	mv -v $df $dest/$pd/
done
for df in `find $d -name "*.zip" -type f`; do
	f=`basename $df`
	pd=`echo $f | sed -e "s/^\(.*\)-[[:digit:]]*\.[[:digit:]].*$/\1/g" | tr "[:upper:]" "[:lower:]" | tr "_" "-"`
	mkdir -v $dest/$pd
	mv -v $df $dest/$pd/
done
