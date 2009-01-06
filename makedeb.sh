#!/bin/bash

for i in common gnome; do
	PKGNAME=`cat control.$i | grep "Package:" | cut -d" " -f2`
	PKGVER=`cat control.$i | grep "Version:" | cut -d" " -f2`
	PKGARCH=`cat control.$i | grep "Architecture:" | cut -d" " -f2`

	echo $PKGNAME $PKGVER $PKGARCH

	rm -rf deb
	mkdir -p deb/DEBIAN

	cp control.$i deb/DEBIAN/control
	sh install-$i.sh ./deb
	dpkg --build deb/ $PKGNAME-${PKGVER}_$PKGARCH.deb
done

rm -rf deb

