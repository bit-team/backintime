#!/bin/bash

for i in common ; do
	PKGNAME=`cat $i/debian_specific/control | grep "^Package:" | cut -d" " -f2`
	PKGVER=`cat $i/debian_specific/control | grep "^Version:" | cut -d" " -f2`
	PKGARCH=`cat $i/debian_specific/control | grep "^Architecture:" | cut -d" " -f2`

	echo $PKGNAME $PKGVER $PKGARCH

	rm -rf tmp
	mkdir -p tmp/${PKGNAME}_$PKGVER

	cd $i
	./makedeb-src.sh ../tmp/${PKGNAME}_$PKGVER
	cd ..

	cd tmp/${PKGNAME}_$PKGVER
	debuild -i -us -uc -S

	cd ..
	rm -rf ${PKGNAME}_$PKGVER
	mv * ../
	cd ..

	exit 0

	rm -rf tmp
done

