#!/bin/bash

VERSION=`cat VERSION`
echo VERSION: $VERSION

echo "Update 'control.common'"
sed -i -e "s/^Version: .*$/Version: $VERSION/" control.common

echo "Update 'control.gnome'"
sed -i -e "s/^Version: .*$/Version: $VERSION/" control.gnome
sed -i -e "s/backintime-common (= [^)]*)/backintime-common (= $VERSION)/" control.gnome

echo "Update 'control.kde4'"
sed -i -e "s/^Version: .*$/Version: $VERSION/" control.kde4
sed -i -e "s/backintime-common (= [^)]*)/backintime-common (= $VERSION)/" control.kde4

echo "Update 'config.py'"
sed -i -e "s/^\tVERSION = '.*'$/\tVERSION = '$VERSION'/" config.py

echo "Update man page"
FILE=man/C/backintime.1
gzip -d $FILE.gz
sed -i -e "s/\.TH\(.*\)\"version\([^\"]*\)\"\(.*\)$/.TH\1\"version $VERSION\"\3/" $FILE
gzip --best $FILE

echo "Update help .omf file"
sed -i -e "s/^\([ \]*\)<version\([^0-9]*\)\([^\"]*\)\(.*\)$/\1<version\2$VERSION\4/" docbook/C/backintime-C.omf

echo "Update help docbook file"
sed -i -e "s/^<!ENTITY appversion .*>$/<!ENTITY appversion \"$VERSION\">/" -e "s/^<!ENTITY manrevision .*>$/<!ENTITY manrevision \"$VERSION\">/" docbook/C/backintime.xml

