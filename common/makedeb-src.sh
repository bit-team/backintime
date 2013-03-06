#!/bin/bash

if [ -z $1 ]; then
	echo "ERROR: You need to specify the install dir"
	exit 1
fi

VERSION=`cat ../VERSION`

DEST=$1

mkdir -p $DEST/debian
mkdir -p $DEST/man/C
mkdir -p $DEST/mo
mkdir -p $DEST/doc
mkdir -p $DEST/plugins

#app
cp backintime $DEST/
cp backintime-askpass $DEST/

#autostart
cp backintime.desktop $DEST/

#python files
cp *.py $DEST/

#plugins
cp plugins/*.py $DEST/plugins

#man pages
gzip --best -c man/C/backintime.1 >$DEST/man/C/backintime.1.gz

#doc files
cp ../AUTHORS $DEST/doc
cp ../LICENSE $DEST/doc
cp ../README $DEST/doc
cp ../TRANSLATIONS $DEST/doc
cp ../VERSION $DEST/doc
cp ../CHANGES $DEST/doc

#debian: copyright
cp debian_specific/copyright $DEST/debian

#debian: postrm
cp debian_specific/postrm $DEST/debian

#debian: rules
cp debian_specific/rules $DEST/debian

#debian: conffiles
cp debian_specific/conffiles $DEST/debian

#add languages to rules
for langfile in `ls po/*.po`; do
	lang=`echo $langfile | cut -d/ -f2 | cut -d. -f1`
	mkdir -p $DEST/mo/$lang
	msgfmt -o $DEST/mo/$lang/backintime.mo po/$lang.po
	#sed -i -e "s/\t\[INSTALL_LANGS\]/\tdh_installdirs \/usr\/share\/locale\/$lang\/LC_MESSAGES\n\tdh_install mo\/$lang.mo \/usr\/share\/locale\/$lang\/LC_MESSAGES\/backintime.mo\n\t[INSTALL_LANGS]/g" $DEST/debian/rules
	sed -i -e "s/\t\[INSTALL_LANGS\]/\tdh_install mo\/$lang\/backintime.mo \/usr\/share\/locale\/$lang\/LC_MESSAGES\n\t[INSTALL_LANGS]/g" $DEST/debian/rules
done

sed -i -e "s/\t\[INSTALL_LANGS\]/\t/" $DEST/debian/rules

