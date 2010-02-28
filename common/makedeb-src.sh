#!/bin/bash

if [ -z $1 ]; then
	echo "ERROOR: You need to specify the install dir"
	exit 1
fi

DEST=$1

mkdir -p $DEST/debian
mkdir -p $DEST/man
mkdir -p $DEST/mo

#python files
cp *.py $DEST/

#man pages
cp -R man/* $DEST/man

#copyright
cp debian_specific/copyright $DEST/debian

#changelog
cat debian_specific/changelog | sed -e "s/\$BACKINTIME/backintime-common/" > $DEST/debian/changelog

#rules files
cp debian_specific/rules $DEST/debian

#languages
for langfile in `ls po/*.po`; do
	lang=`echo $langfile | cut -d/ -f2 | cut -d. -f1`
	msgfmt -o $DEST/mo/$lang.mo po/$lang.po
	sed -i -e "s/\t\[INSTALL_LANGS\]/\tdh_installdirs \/usr\/share\/locale\/$lang\/LC_MESSAGES\n\tdh_install ..\/mo\/$lang.mo \/usr\/share\/locale\/$lang\/LC_MESSAGES\/backintime.mo\n\t[INSTALL_LANGS]/g" $DEST/debian/rules
done

sed -i -e "s/\t\[INSTALL_LANGS\]//" $DEST/debian/rules

