#!/bin/bash

PKGNAME=`cat control | grep "Package:" | cut -d" " -f2`
PKGVER=`cat control | grep "Version:" | cut -d" " -f2`
PKGARCH=`cat control | grep "Architecture:" | cut -d" " -f2`

echo $PKGNAME $PKGVER $PKGARCH

rm -rf deb
mkdir -p deb/DEBIAN

cp control deb/DEBIAN
sh install.sh ./deb
dpkg --build deb/ $PKGNAME-${PKGVER}_$PKGARCH.deb

rm -rf deb

#translations
./translate.sh

for lang in `ls locale | cut -d/ -f2`; do
	echo Make package for language: $lang

	mkdir -p deb/DEBIAN

	echo "Package: $PKGNAME-$lang" > deb/DEBIAN/control
	echo "Depends: backintime" >> deb/DEBIAN/control
	echo "Description: Back In Time locale for language '$lang'" >> deb/DEBIAN/control
	cat control | grep -v Package | grep -v Depends | grep -v Description >> deb/DEBIAN/control

	sh install_locale.sh $lang ./deb
	dpkg --build deb/ $PKGNAME-$lang-${PKGVER}_$PKGARCH.deb

	rm -rf deb
done

