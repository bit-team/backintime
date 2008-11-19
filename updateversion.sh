#!/bin/bash

VERSION=`cat VERSION`
echo VERSION: $VERSION

echo "Update 'control'"
mv control control.tmp
sed -e "s/^Version: .*$/Version: $VERSION/" control.tmp > control
rm control.tmp

echo "Update 'config.py'"
mv config.py config.py.tmp
sed -e "s/^\tVERSION = '.*'$/\tVERSION = '$VERSION'/" config.py.tmp  > config.py
rm config.py.tmp

echo "Update man page"
FILE=man/C/backintime.1
gzip -d $FILE.gz
mv $FILE $FILE.tmp
sed -e "s/\.TH\(.*\)\"version\([^\"]*\)\"\(.*\)$/.TH\1\"version $VERSION\"\3/" $FILE.tmp > $FILE
rm $FILE.tmp
gzip $FILE

echo "Update help .omf file"
FILE=docbook/C/backintime-C.omf
mv $FILE $FILE.tmp
sed -e "s/^\([ \]*\)<version\([^0-9]*\)\([^\"]*\)\(.*\)$/\1<version\2$VERSION\4/" $FILE.tmp > $FILE
rm $FILE.tmp

echo "Update help docbook file"
FILE=docbook/C/backintime.xml
mv $FILE $FILE.tmp
sed -e "s/^<!ENTITY appversion .*>$/<!ENTITY appversion \"$VERSION\">/" -e "s/^<!ENTITY manrevision .*>$/<!ENTITY manrevision \"$VERSION\">/" $FILE.tmp > $FILE
rm $FILE.tmp

