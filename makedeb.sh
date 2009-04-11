#!/bin/bash

for i in common gnome kde4; do
	PKGNAME=`cat control.$i | grep "Package:" | cut -d" " -f2`
	PKGVER=`cat control.$i | grep "Version:" | cut -d" " -f2`
	PKGARCH=`cat control.$i | grep "Architecture:" | cut -d" " -f2`

	echo $PKGNAME $PKGVER $PKGARCH

	rm -rf tmp
	mkdir -p tmp/DEBIAN

	cp control.$i tmp/DEBIAN/control
	./configure --no-common --no-gnome --no-kde4 --$i
	make DESTDIR=tmp install
	dpkg --build tmp/ $PKGNAME-${PKGVER}_$PKGARCH.deb
	rm -rf tmp
done

