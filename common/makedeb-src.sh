#!/bin/bash

if [ -z $1 ]; then
	echo "ERROOR: You need to specify the install dir"
	exit 1
fi

DEST=$1

mkdir -p $DEST/src/debian
mkdir -p $DEST/src/po
mkdir -p $DEST/src/man

#languages
for langfile in `ls po/*.po`; do
	msgfmt -o po/$lang.mo $DEST/po/$lang.po
done

#python files
cp *.py $DEST/src

#man pages
cp -R man/* $DEST/src/man

#copyright
cp debian_specific/copyright $DEST/src/debian

#changelog
cat debian_specific/changelog | sed -e "s/$BACKINTIME/backintime-common" > $DEST/src/debian/changelog

#rules files
cp debian_specific/rules $DEST/src/debian

