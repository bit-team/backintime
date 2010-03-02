#!/bin/bash

RELEASES="hardy intrepid jaunty karmic"

for i in common gnome kde4; do
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

	for release in $RELEASES; do
		#debuild -i -us -uc -S
		sed -e "1s/.*/$PKGNAME ($PKGVER~$release) $release; urgency=low/" -i debian/changelog
		debuild -i -S
	done

	cd ..
	rm -rf ${PKGNAME}_$PKGVER
	mv * ../
	cd ..

	rm -rf tmp
done

