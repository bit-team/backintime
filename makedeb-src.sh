#!/bin/bash

RELEASES="karmic lucid maverick natty precise quantal raring saucy"

for i in common notify gnome kde4; do
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
		#debian: control
		cp ../../$i/debian_specific/control.source debian/control
		cat ../../$i/debian_specific/control >> debian/control
		sed -e "s/backintime-common (>= [^)]*)/backintime-common (>= $PKGVER~$release)/g" -i debian/control
		sed -e "s/backintime-notify (>= [^)]*)/backintime-notify (>= $PKGVER~$release)/g" -i debian/control

		#debian: changelog
		cp ../../common/debian_specific/changelog debian
		sed -e "s/\$BACKINTIME/backintime-$i/g" -e "s/\$VERSION/$PKGVER/g"  -e "s/\$RELEASE/$release/g" -i debian/changelog

		debuild -i -S
		#debuild -i -us -uc -S
	done

	cd ..
	rm -rf ${PKGNAME}_$PKGVER
	mv * ../
	cd ..

	rm -rf tmp
done

